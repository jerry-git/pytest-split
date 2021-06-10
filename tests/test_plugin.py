import itertools
import json
import os
from collections import namedtuple

import pytest
from _pytest.main import ExitCode
from pytest_split.plugin import split_tests

pytest_plugins = ["pytester"]


@pytest.fixture
def example_suite(testdir):
    testdir.makepyfile("".join(f"def test_{num}(): pass\n" for num in range(1, 11)))
    yield testdir


@pytest.fixture
def durations_path(tmpdir):
    return str(tmpdir.join(".durations"))


class TestStoreDurations:
    def test_it_stores(self, example_suite, durations_path):
        example_suite.runpytest("--store-durations", "--durations-path", durations_path)

        with open(durations_path) as f:
            durations = json.load(f)

        assert list(durations.keys()) == [
            "test_it_stores.py::test_1",
            "test_it_stores.py::test_2",
            "test_it_stores.py::test_3",
            "test_it_stores.py::test_4",
            "test_it_stores.py::test_5",
            "test_it_stores.py::test_6",
            "test_it_stores.py::test_7",
            "test_it_stores.py::test_8",
            "test_it_stores.py::test_9",
            "test_it_stores.py::test_10",
        ]

        for duration in durations.values():
            assert isinstance(duration, float)

    def test_it_does_not_store_without_flag(self, example_suite, durations_path):
        example_suite.runpytest("--durations-path", durations_path)
        assert not os.path.exists(durations_path)


class TestSplitToSuites:
    @pytest.mark.parametrize(
        "param_idx, splits, expected_tests_per_group",
        [
            (
                0,
                1,
                [
                    [
                        "test_1",
                        "test_2",
                        "test_3",
                        "test_4",
                        "test_5",
                        "test_6",
                        "test_7",
                        "test_8",
                        "test_9",
                        "test_10",
                    ]
                ],
            ),
            (
                1,
                2,
                [
                    ["test_1", "test_3", "test_5", "test_7", "test_9"],
                    ["test_2", "test_4", "test_6", "test_8", "test_10"],
                ],
            ),
            (
                2,
                3,
                [
                    ["test_1", "test_4", "test_7", "test_10"],
                    ["test_2", "test_5", "test_8"],
                    ["test_3", "test_6", "test_9"],
                ],
            ),
            (
                3,
                4,
                [
                    ["test_1", "test_5", "test_9"],
                    ["test_2", "test_6", "test_10"],
                    ["test_3", "test_7"],
                    ["test_4", "test_8"],
                ],
            ),
        ],
    )
    def test_it_splits(self, param_idx, splits, expected_tests_per_group, example_suite, durations_path):
        assert len(list(itertools.chain(*expected_tests_per_group))) == 10

        for durations in [
            # Legacy format - can be removed in v1
            [
                *[[f"test_it_splits{param_idx}/test_it_splits.py::test_{num}", 1] for num in range(1, 6)],
                *[[f"test_it_splits{param_idx}/test_it_splits.py::test_{num}", 2] for num in range(6, 11)],
            ],
            # Current format
            {
                **{f"test_it_splits{param_idx}/test_it_splits.py::test_{num}": 1 for num in range(1, 6)},
                **{f"test_it_splits{param_idx}/test_it_splits.py::test_{num}": 2 for num in range(6, 11)},
            },
        ]:

            with open(durations_path, "w") as f:
                json.dump(durations, f)

            results = [
                example_suite.inline_run(
                    "--splits",
                    str(splits),
                    "--group",
                    str(group + 1),
                    "--durations-path",
                    durations_path,
                )
                for group in range(splits)
            ]

            for result, expected_tests in zip(results, expected_tests_per_group):
                result.assertoutcome(passed=len(expected_tests))
                assert _passed_test_names(result) == expected_tests

    def test_it_does_not_split_with_invalid_args(self, example_suite, durations_path):
        durations = {"test_it_does_not_split_with_invalid_args.py::test_1": 1}
        with open(durations_path, "w") as f:
            json.dump(durations, f)

        # Plugin doesn't run when splits is passed but group is missing
        result = example_suite.inline_run("--splits", "2", "--durations-path", durations_path)  # no --group
        assert result.ret == ExitCode.USAGE_ERROR

        # Plugin doesn't run when group is passed but splits is missing
        result = example_suite.inline_run("--group", "2", "--durations-path", durations_path)  # no --splits
        assert result.ret == ExitCode.USAGE_ERROR

        # Runs if they both are
        result = example_suite.inline_run("--splits", "2", "--group", "1", "--durations-path", durations_path)
        assert result.ret == ExitCode.OK
        result.assertoutcome(passed=5)

    def test_it_adapts_splits_based_on_new_and_deleted_tests(self, example_suite, durations_path):
        # Only 4/10 tests listed here, avg duration 1 sec
        test_path = (
            "test_it_adapts_splits_based_on_new_and_deleted_tests0/"
            "test_it_adapts_splits_based_on_new_and_deleted_tests.py::{}"
        )
        durations = {
            test_path.format("test_1"): 1,
            test_path.format("test_5"): 2.6,
            test_path.format("test_6"): 0.2,
            test_path.format("test_10"): 0.2,
            test_path.format("test_THIS_IS_NOT_IN_THE_SUITE"): 1000,
        }

        with open(durations_path, "w") as f:
            json.dump(durations, f)

        result = example_suite.inline_run("--splits", "3", "--group", "1", "--durations-path", durations_path)
        result.assertoutcome(passed=4)
        assert _passed_test_names(result) == ["test_1", "test_4", "test_8", "test_10"]

        result = example_suite.inline_run("--splits", "3", "--group", "2", "--durations-path", durations_path)
        result.assertoutcome(passed=2)
        assert _passed_test_names(result) == ["test_2", "test_5"]

        result = example_suite.inline_run("--splits", "3", "--group", "3", "--durations-path", durations_path)
        result.assertoutcome(passed=4)
        assert _passed_test_names(result) == ["test_3", "test_6", "test_7", "test_9"]

    def test_handles_case_of_no_durations_for_group(self, example_suite, durations_path):
        with open(durations_path, "w") as f:
            json.dump({}, f)

        result = example_suite.inline_run("--splits", "1", "--group", "1", "--durations-path", durations_path)
        assert result.ret == ExitCode.OK
        result.assertoutcome(passed=10)

    def test_it_splits_with_other_collect_hooks(self, testdir, durations_path):
        expected_tests_per_group = [
            ["test_1", "test_2", "test_3"],
            ["test_4", "test_5"],
        ]

        tests_to_run = "".join(f"@pytest.mark.mark_one\ndef test_{num}(): pass\n" for num in range(1, 6))
        tests_to_exclude = "".join(f"def test_{num}(): pass\n" for num in range(6, 11))
        testdir.makepyfile(f"import pytest\n{tests_to_run}\n{tests_to_exclude}")

        durations = (
            {
                **{f"test_it_splits_when_paired_with_marker_expressions.py::test_{num}": 1 for num in range(1, 3)},
                **{f"test_it_splits_when_paired_with_marker_expressions.py::test_{num}": 2 for num in range(3, 6)},
            },
        )
        with open(durations_path, "w") as f:
            json.dump(durations[0], f)

        results = [
            testdir.inline_run("--splits", 2, "--group", group, "--durations-path", durations_path, "-m" "mark_one")
            for group in range(1, 3)
        ]

        for result, expected_tests in zip(results, expected_tests_per_group):
            result.assertoutcome(passed=len(expected_tests))
            assert _passed_test_names(result) == expected_tests


class TestRaisesUsageErrors:
    def test_returns_nonzero_when_group_but_not_splits(self, example_suite, capsys):
        result = example_suite.inline_run("--group", "1")
        assert result.ret == 4

        outerr = capsys.readouterr()
        assert "argument `--splits` is required" in outerr.err

    def test_returns_nonzero_when_splits_but_not_group(self, example_suite, capsys):
        result = example_suite.inline_run("--splits", "1")
        assert result.ret == 4

        outerr = capsys.readouterr()
        assert "argument `--group` is required" in outerr.err

    def test_returns_nonzero_when_group_below_one(self, example_suite, capsys):
        result = example_suite.inline_run("--splits", "3", "--group", "0")
        assert result.ret == 4

        outerr = capsys.readouterr()
        assert "argument `--group` must be >= 1 and <= 3" in outerr.err

    def test_returns_nonzero_when_group_larger_than_splits(self, example_suite, capsys):
        result = example_suite.inline_run("--splits", "3", "--group", "4")
        assert result.ret == 4

        outerr = capsys.readouterr()
        assert "argument `--group` must be >= 1 and <= 3" in outerr.err

    def test_returns_nonzero_when_splits_below_one(self, example_suite, capsys):
        result = example_suite.inline_run("--splits", "0", "--group", "1")
        assert result.ret == 4

        outerr = capsys.readouterr()
        assert "argument `--splits` must be >= 1" in outerr.err


class TestHasExpectedOutput:
    def test_prints_splitting_summary_when_durations_present(self, example_suite, capsys, durations_path):
        test_name = "test_prints_splitting_summary_when_durations_present"
        with open(durations_path, "w") as f:
            json.dump([[f"{test_name}0/{test_name}.py::test_1", 0.5]], f)
        result = example_suite.inline_run("--splits", "1", "--group", "1", "--durations-path", durations_path)
        assert result.ret == 0

        outerr = capsys.readouterr()
        assert "[pytest-split] Running group 1/1" in outerr.out

    def test_does_not_print_splitting_summary_when_no_pytest_split_arguments(self, example_suite, capsys):
        result = example_suite.inline_run()
        assert result.ret == 0

        outerr = capsys.readouterr()
        assert "[pytest-split]" not in outerr.out

    def test_prints_correct_number_of_selected_and_deselected_tests(self, example_suite, capsys, durations_path):
        test_name = "test_prints_splitting_summary_when_durations_present"
        with open(durations_path, "w") as f:
            json.dump([[f"{test_name}0/{test_name}.py::test_1", 0.5]], f)
        result = example_suite.inline_run("--splits", "5", "--group", "1", "--durations-path", durations_path)
        assert result.ret == 0

        outerr = capsys.readouterr()
        assert "collected 10 items / 8 deselected / 2 selected" in outerr.out


class TestSplitTests:
    def test__split_test(self):
        durations = {"a": 1, "b": 1, "c": 1}
        item = namedtuple("dummy_item", "nodeid")
        items = [item(x) for x in durations.keys()]
        first, second, third = split_tests(splits=3, items=items, durations=durations)

        # each split should have one test
        assert first.selected == [item("a")]
        assert first.deselected == [item("b"), item("c")]
        assert first.duration == 1

        assert second.selected == [item("b")]
        assert second.deselected == [item("a"), item("c")]
        assert second.duration == 1

        assert third.selected == [item("c")]
        assert third.deselected == [item("a"), item("b")]
        assert third.duration == 1

    @pytest.mark.skip("current algorithm does not cover this")
    def test__split_test_handles_large_duration_at_end(self):
        durations = {"a": 1, "b": 1, "c": 1, "d": 3}
        item = namedtuple("dummy_item", "nodeid")
        items = [item(x) for x in ["a", "b", "c", "d"]]
        splits = split_tests(splits=2, items=items, durations=durations)

        first, second = splits
        assert first.selected == [item("d")]
        assert second.selected == [item(x) for x in ["a", "b", "c"]]

    def test__split_tests_handles_tests_with_missing_durations(self):
        durations = {"a": 1}
        item = namedtuple("dummy_item", "nodeid")
        items = [item(x) for x in ["a", "b"]]
        splits = split_tests(splits=2, items=items, durations=durations)

        first, second = splits
        assert first.selected == [item("a")]
        assert second.selected == [item("b")]

    def test__split_tests_handles_tests_in_durations_but_missing_from_items(self):
        durations = {"a": 1, "b": 1}
        item = namedtuple("dummy_item", "nodeid")
        items = [item(x) for x in ["a"]]
        splits = split_tests(splits=2, items=items, durations=durations)

        first, second = splits
        assert first.selected == [item("a")]
        assert second.selected == []

    def test__split_tests_calculates_avg_test_duration_only_on_present_tests(self):
        # If the algo includes test e's duration to calculate the averge then
        # a will be expected to take a long time, and so 'a' will become its
        # own group. Intended behaviour is that a gets estimated duration 1 and
        # this will create more balanced groups.
        durations = {"b": 1, "c": 1, "d": 1, "e": 10000}
        item = namedtuple("dummy_item", "nodeid")
        items = [item(x) for x in ["a", "b", "c", "d"]]
        splits = split_tests(splits=2, items=items, durations=durations)

        first, second = splits
        assert first.selected == [item("a"), item("c")]
        assert second.selected == [item("b"), item("d")]


def _passed_test_names(result):
    return [passed.nodeid.split("::")[-1] for passed in result.listoutcomes()[0]]
