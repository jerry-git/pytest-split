import json
from types import SimpleNamespace
from typing import cast

import pytest
from _pytest.main import ExitCode  # type: ignore[attr-defined]
from pytest_split.algorithms import Algorithms, ModuleGrouping

pytest_plugins = ["pytester"]


def item(nodeid: str) -> pytest.Item:
    return cast("pytest.Item", SimpleNamespace(nodeid=nodeid))


class TestModuleGrouping:
    @pytest.mark.parametrize(
        ("splitting_algorithm", "expected"),
        [
            (
                "duration_based_chunks",
                {"test_a.py": 0, "test_b.py": 0, "test_c.py": 1, "test_d.py": 1},
            ),
            (
                "least_duration",
                {"test_a.py": 0, "test_b.py": 1, "test_c.py": 1, "test_d.py": 0},
            ),
        ],
    )
    def test_module_plan_uses_selected_algorithm(self, splitting_algorithm, expected):
        modules = {f"test_{name}.py" for name in "abcd"}
        durations = {
            f"test_{name}.py::test_one": duration
            for name, duration in zip("abcd", [8.0, 7.0, 6.0, 5.0], strict=True)
        }
        grouping = ModuleGrouping(Algorithms[splitting_algorithm].value)
        assert grouping.module_groups(2, modules, durations) == expected

    @pytest.mark.parametrize("splitting_algorithm", Algorithms.names())
    @pytest.mark.parametrize("splits", [1, 2, 6])
    @pytest.mark.parametrize("zero_durations", [False, True])
    def test_module_plan_handles_missing_and_zero_durations(
        self, splitting_algorithm, splits, zero_durations
    ):
        modules = {f"test_{name}.py" for name in "abcd"}
        durations = (
            {f"{path}::test_one": 0.0 for path in modules} if zero_durations else {}
        )
        grouping = ModuleGrouping(Algorithms[splitting_algorithm].value)
        plan = grouping.module_groups(splits, modules, durations)
        assert set(plan) == modules
        assert all(0 <= group < splits for group in plan.values())
        expected = {1: [0, 0, 0, 0], 2: [0, 0, 1, 1], 6: [0, 1, 2, 3]}
        assert sorted(plan.values()) == expected[splits]

    @pytest.mark.parametrize("splitting_algorithm", Algorithms.names())
    def test_module_plan_handles_no_modules(self, splitting_algorithm):
        grouping = ModuleGrouping(Algorithms[splitting_algorithm].value)
        assert grouping.module_groups(2, set(), {}) == {}

    def test_reuses_full_plan_when_only_one_group_has_been_collected(self):
        algorithm = ModuleGrouping(Algorithms["least_duration"].value)
        durations: dict[str, float] = {
            "test_a.py::test_one": 8,
            "test_b.py::test_one": 2,
        }
        plan = algorithm.module_groups(2, {"test_a.py", "test_b.py"}, durations)
        selected = item("test_b.py::test_one")
        first, second = algorithm(2, [selected], durations, module_groups=plan)
        assert first.selected == []
        assert second.selected == [selected]

    def test_unplanned_modules_are_split_without_changing_the_original_plan(self):
        algorithm = ModuleGrouping(Algorithms["least_duration"].value)
        plan = {"test_a.py": 1}
        items = [item(f"test_{name}.py::test_one") for name in "abc"]
        first, second = algorithm(2, items, {}, module_groups=plan)
        assert first.selected == [items[1]]
        assert second.selected == [items[0], items[2]]
        assert plan == {"test_a.py": 1}

    def test_balances_summed_module_durations(self):
        durations: dict[str, float] = {
            "test_a.py::test_one": 4,
            "test_a.py::test_two": 4,
            "test_b.py::test_one": 7,
            "test_c.py::test_one": 6,
            "test_d.py::test_one": 5,
        }
        items = [item(nodeid) for nodeid in durations]
        first, second = ModuleGrouping(Algorithms["least_duration"].value)(
            2, items, durations
        )
        assert first.selected == [items[0], items[1], items[4]]
        assert second.selected == [items[2], items[3]]
        assert (first.duration, second.duration) == (13, 13)

    def test_new_modules_use_average_module_duration_and_stale_entries_are_ignored(
        self,
    ):
        modules = {f"test_{name}.py" for name in "abcd"}
        durations: dict[str, float] = {
            "test_a.py::test_one": 4,
            "test_a.py::test_two": 4,
            "test_b.py::test_one": 2,
            "test_deleted.py::test_one": 1000,
        }
        groups = ModuleGrouping(Algorithms["least_duration"].value).module_groups(
            2, modules, durations
        )
        assert groups == {
            "test_a.py": 0,
            "test_b.py": 0,
            "test_c.py": 1,
            "test_d.py": 1,
        }

    @pytest.mark.parametrize("duration", [0, 1])
    def test_ties_are_deterministic_and_spread_modules_evenly(self, duration):
        modules = {f"test_{name}.py" for name in "abcd"}
        durations: dict[str, float] = {
            f"{path}::test_one": duration for path in modules
        }
        groups = ModuleGrouping(Algorithms["least_duration"].value).module_groups(
            2, modules, durations
        )
        assert groups == {
            "test_a.py": 0,
            "test_b.py": 1,
            "test_c.py": 0,
            "test_d.py": 1,
        }

    def test_groups_whole_modules_and_estimates_durations(self):
        items = [
            item("test_a.py::test_first[1]"),
            item("test_b.py::TestExample::test_first"),
            item("test_a.py::test_first[2]"),
            item("test_c.py::test_first"),
        ]
        durations: dict[str, float] = {
            items[0].nodeid: 2,
            items[1].nodeid: 4,
            items[2].nodeid: 3,
        }

        first, second = ModuleGrouping(Algorithms["least_duration"].value)(
            2, items, durations
        )

        assert first.selected == [items[0], items[2]]
        assert first.deselected == [items[1], items[3]]
        assert (first.duration, second.duration) == (5, 7)
        assert second.selected == first.deselected
        assert second.deselected == first.selected

    @pytest.mark.parametrize("splits", [1, 2, 3, 10])
    def test_assigns_every_test_once_independent_of_collection_order(self, splits):
        items = [item(f"test_{name}.py::test_example") for name in "abcd"]
        algorithm = ModuleGrouping(Algorithms["least_duration"].value)
        durations: dict[str, float] = {items[0].nodeid: 8, items[1].nodeid: 2}
        original = algorithm(splits, items, durations)
        reordered = algorithm(
            splits, items[::-1], dict(reversed(list(durations.items())))
        )

        assert sorted(test.nodeid for group in original for test in group.selected) == [
            test.nodeid for test in items
        ]
        for first, second in zip(original, reordered, strict=True):
            assert first.selected == second.selected[::-1]

    def test_keeps_notebook_cells_together(self):
        items = [
            item(f"test_{name}.ipynb::Cell {i}") for name in "ab" for i in range(3)
        ]
        first, second = ModuleGrouping(Algorithms["least_duration"].value)(2, items, {})
        assert first.selected == items[:3]
        assert second.selected == items[3:]


@pytest.mark.parametrize("splitting_algorithm", Algorithms.names())
class TestEarlyModuleFiltering:
    def test_pyargs_module_paths_are_not_imported_during_planning(
        self, testdir, splitting_algorithm
    ):
        testdir.makepyfile(
            test_a="def test_one(): pass", test_b="raise AssertionError('Other group')"
        )
        result = testdir.inline_run(
            "--splits",
            "2",
            "--group",
            "1",
            "--no-module-splits",
            "--splitting-algorithm",
            splitting_algorithm,
            "--pyargs",
            "test_a.py",
            "test_b.py",
        )
        result.assertoutcome(passed=1)

    @pytest.mark.parametrize(
        "arguments", [["examplepkg"], ["examplepkg.test_a", "examplepkg.test_b"]]
    )
    def test_pyargs_does_not_import_other_groups(
        self, testdir, arguments, splitting_algorithm
    ):
        package = testdir.mkpydir("examplepkg")
        package.join("test_a.py").write("def test_one(): pass")
        package.join("test_b.py").write("raise AssertionError('Other group')")
        testdir.syspathinsert()
        result = testdir.inline_run(
            "--splits",
            "2",
            "--group",
            "1",
            "--no-module-splits",
            "--splitting-algorithm",
            splitting_algorithm,
            "--pyargs",
            *arguments,
        )
        result.assertoutcome(passed=1)

    def test_norecursedirs_does_not_affect_group_loads(
        self, testdir, splitting_algorithm
    ):
        testdir.makeini("[pytest]\nnorecursedirs = excluded")
        testdir.makepyfile(
            test_a="def test_one(): pass", test_b="raise AssertionError('Other group')"
        )
        excluded = testdir.mkdir("excluded")
        excluded.join("test_slow.py").write("raise AssertionError('Ignored directory')")
        testdir.tmpdir.join("durations.json").write(
            json.dumps(
                {
                    "test_a.py::test_one": 8,
                    "test_b.py::test_one": 7,
                    "excluded/test_slow.py::test_one": 1000,
                }
            )
        )
        result = testdir.inline_run(
            "--splits",
            "2",
            "--group",
            "1",
            "--no-module-splits",
            "--splitting-algorithm",
            splitting_algorithm,
            "--durations-path",
            "durations.json",
        )
        result.assertoutcome(passed=1)

    @pytest.mark.parametrize(("group", "selected"), [(1, "ad"), (2, "bc")])
    @pytest.mark.parametrize("legacy_cache", [False, True])
    def test_balances_modules_without_importing_other_groups(  # noqa: PLR0913
        self, testdir, group, selected, legacy_cache, splitting_algorithm
    ):
        if splitting_algorithm == "duration_based_chunks":
            selected = "ab" if group == 1 else "cd"
        durations = {
            "test_a.py::test_one": 4,
            "test_a.py::test_two": 4,
            "test_b.py::test_one": 7,
            "test_c.py::test_one": 6,
            "test_d.py::test_one": 5,
        }
        for name in "abcd":
            source = "def test_one(): pass"
            if name == "a":
                source += "\ndef test_two(): pass"
            if name not in selected:
                source = "raise AssertionError('Must not import another group')"
            testdir.makepyfile(**{f"test_{name}": source})
        cache = list(durations.items()) if legacy_cache else durations
        testdir.tmpdir.join("durations.json").write(json.dumps(cache))
        result = testdir.inline_run(
            "--splits",
            "2",
            "--group",
            str(group),
            "--no-module-splits",
            "--splitting-algorithm",
            splitting_algorithm,
            "--durations-path",
            "durations.json",
        )
        result.assertoutcome(passed=3 if group == 1 else 2)
        passed = result.listoutcomes()[0]
        assert {report.nodeid.split(".py", 1)[0] for report in passed} == {
            f"test_{name}" for name in selected
        }

    @pytest.mark.parametrize("ignore_option", ["--ignore", "--ignore-glob"])
    def test_ignores_excluded_and_deleted_modules_when_balancing(
        self, testdir, ignore_option, splitting_algorithm
    ):
        testdir.makepyfile(
            test_a="def test_one(): pass",
            test_b="raise AssertionError('Ignored module')",
            test_c="raise AssertionError('Other group')",
        )
        testdir.tmpdir.join("durations.json").write(
            json.dumps(
                {
                    "test_a.py::test_one": 8,
                    "test_b.py::test_one": 100,
                    "test_c.py::test_one": 7,
                    "test_deleted.py::test_one": 1000,
                }
            )
        )
        result = testdir.inline_run(
            "--splits",
            "2",
            "--group",
            "1",
            "--no-module-splits",
            "--splitting-algorithm",
            splitting_algorithm,
            "--durations-path",
            "durations.json",
            ignore_option,
            "test_b.py",
        )
        result.assertoutcome(passed=1)

    @pytest.mark.parametrize(
        ("group", "selected", "excluded"), [(1, "a", "b"), (2, "b", "a")]
    )
    @pytest.mark.parametrize(
        "arguments",
        [
            [],
            ["."],
            ["test_a.py", "test_b.py"],
            ["test_a.py::test_a", "test_b.py::test_b"],
        ],
    )
    def test_does_not_import_or_collect_other_groups(  # noqa: PLR0913
        self, testdir, group, selected, excluded, arguments, splitting_algorithm
    ):
        testdir.makepyfile(
            **{
                f"test_{selected}": f"def test_{selected}(): pass",
                f"test_{excluded}": "raise AssertionError('This module must not be imported')",
            }
        )
        result = testdir.inline_run(
            "--splits",
            "2",
            "--group",
            str(group),
            "--no-module-splits",
            "--splitting-algorithm",
            splitting_algorithm,
            *arguments,
        )

        result.assertoutcome(passed=1)
        collected = [
            call.report.nodeid for call in result.getcalls("pytest_collectreport")
        ]
        assert f"test_{excluded}.py" not in collected

    @pytest.mark.parametrize("argument", ["test_b.py", "test_b.py::test_b"])
    def test_all_explicit_modules_belong_to_another_group(
        self, testdir, argument, splitting_algorithm
    ):
        testdir.makepyfile(
            test_b="raise AssertionError('This module must not be imported')"
        )
        result = testdir.inline_run(
            "--splits",
            "2",
            "--group",
            "2",
            "--no-module-splits",
            "--splitting-algorithm",
            splitting_algorithm,
            argument,
        )
        assert result.ret == ExitCode.NO_TESTS_COLLECTED
        result.assertoutcome(passed=0)

    def test_recurses_into_directories_and_respects_custom_python_modules(
        self, testdir, splitting_algorithm
    ):
        testdir.makeini("[pytest]\npython_files = check_*.py")
        checks = testdir.mkdir("checks")
        checks.join("check_a.py").write("def test_selected(): pass")
        checks.join("check_b.py").write("raise AssertionError('Must not be imported')")

        result = testdir.inline_run(
            "--splits",
            "2",
            "--group",
            "1",
            "--no-module-splits",
            "--splitting-algorithm",
            splitting_algorithm,
        )
        result.assertoutcome(passed=1)

    def test_applies_keyword_filtering_to_assigned_modules(
        self, testdir, splitting_algorithm
    ):
        testdir.makepyfile(test_a="def test_keep(): pass\ndef test_drop(): pass")
        result = testdir.inline_run(
            "--splits",
            "2",
            "--group",
            "1",
            "--no-module-splits",
            "--splitting-algorithm",
            splitting_algorithm,
            "-k",
            "keep",
        )
        result.assertoutcome(passed=1)
        deselected = result.getcalls("pytest_deselected")
        assert [test.nodeid for call in deselected for test in call.items] == [
            "test_a.py::test_drop"
        ]

    def test_no_filtering_without_splits(self, testdir, splitting_algorithm):
        testdir.makepyfile(test_a="def test_a(): pass", test_b="def test_b(): pass")
        result = testdir.inline_run(
            "--no-module-splits", "--splitting-algorithm", splitting_algorithm
        )
        result.assertoutcome(passed=2)

    def test_collect_only_skips_importing_other_groups(
        self, testdir, splitting_algorithm
    ):
        testdir.makepyfile(
            test_a="def test_a(): pass",
            test_b="raise AssertionError('Must not be imported')",
        )
        result = testdir.inline_run(
            "--splits",
            "2",
            "--group",
            "1",
            "--no-module-splits",
            "--splitting-algorithm",
            splitting_algorithm,
            "--collect-only",
        )
        assert result.ret == ExitCode.OK
        collected = result.getcalls("pytest_itemcollected")
        assert [call.item.nodeid for call in collected] == ["test_a.py::test_a"]

    def test_storing_durations_preserves_other_groups(
        self, testdir, splitting_algorithm
    ):
        testdir.makepyfile(test_a="def test_a(): pass", test_b="def test_b(): pass")
        durations_path = testdir.tmpdir.join("durations.json")
        other_group_duration = 100
        durations_path.write(
            json.dumps(
                {"test_a.py::test_a": 200, "test_b.py::test_b": other_group_duration}
            )
        )
        result = testdir.inline_run(
            "--splits",
            "2",
            "--group",
            "1",
            "--no-module-splits",
            "--splitting-algorithm",
            splitting_algorithm,
            "--store-durations",
            "--durations-path",
            str(durations_path),
        )

        result.assertoutcome(passed=1)
        durations = json.loads(durations_path.read())
        assert durations["test_b.py::test_b"] == other_group_duration
        assert "test_a.py::test_a" in durations
