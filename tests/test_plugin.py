import itertools
import json
import os
from typing import ClassVar

import pytest
from _pytest.main import ExitCode  # type: ignore[attr-defined]
from pytest_split.algorithms import Algorithms

pytest_plugins = ["pytester"]

EXAMPLE_SUITE_TEST_COUNT = 10


@pytest.fixture()
def example_suite(testdir):
    testdir.makepyfile(
        "".join(
            f"def test_{num}(): pass\n"
            for num in range(1, EXAMPLE_SUITE_TEST_COUNT + 1)
        )
    )
    return testdir


@pytest.fixture()
def durations_path(tmpdir):
    return str(tmpdir.join(".durations"))


class TestStoreDurations:
    def test_it_stores_replace(self, example_suite, durations_path):
        example_suite.runpytest("--store-durations", "--durations-path", durations_path)

        with open(durations_path) as f:
            durations = json.load(f)

        assert list(durations.keys()) == [
            "test_it_stores_replace.py::test_1",
            "test_it_stores_replace.py::test_10",
            "test_it_stores_replace.py::test_2",
            "test_it_stores_replace.py::test_3",
            "test_it_stores_replace.py::test_4",
            "test_it_stores_replace.py::test_5",
            "test_it_stores_replace.py::test_6",
            "test_it_stores_replace.py::test_7",
            "test_it_stores_replace.py::test_8",
            "test_it_stores_replace.py::test_9",
        ]

        for duration in durations.values():
            assert isinstance(duration, float)

    def test_it_stores_keep(self, example_suite, durations_path):
        example_suite.runpytest("--store-durations", "--durations-path", durations_path)

        with open(durations_path) as f:
            durations = json.load(f)

        default_keys = [
            "test_it_stores_keep.py::test_1",
            "test_it_stores_keep.py::test_10",
            "test_it_stores_keep.py::test_2",
            "test_it_stores_keep.py::test_3",
            "test_it_stores_keep.py::test_4",
            "test_it_stores_keep.py::test_5",
            "test_it_stores_keep.py::test_6",
            "test_it_stores_keep.py::test_7",
            "test_it_stores_keep.py::test_8",
            "test_it_stores_keep.py::test_9",
        ]

        assert list(durations.keys()) == default_keys

        for duration in durations.values():
            assert isinstance(duration, float)

        example_suite.makepyfile("def test_11(): pass")
        example_suite.runpytest(
            "--store-durations", "keep", "--durations-path", durations_path
        )

        with open(durations_path) as f:
            durations_keep = json.load(f)
        assert list(durations_keep.keys()) == [
            *default_keys,
            "test_it_stores_keep0/test_it_stores_keep.py::test_11",
        ]
        for k in default_keys:
            assert durations_keep[k] == durations[k]

    def test_it_overrides_existing_durations(self, example_suite, durations_path):
        existing_duration_test_name = "test_it_overrides_existing_durations0/test_it_overrides_existing_durations.py::test_1"
        old_value = 99
        with open(durations_path, "w") as f:
            json.dump({existing_duration_test_name: old_value}, f)

        example_suite.runpytest("--store-durations", "--durations-path", durations_path)

        with open(durations_path) as f:
            durations = json.load(f)

        assert durations[existing_duration_test_name] != old_value
        assert len(durations) == EXAMPLE_SUITE_TEST_COUNT

    def test_it_doesnt_remove_old_durations(self, example_suite, durations_path):
        old_durations = {"test_old1": 1, "test_old2": 2}
        with open(durations_path, "w") as f:
            json.dump(old_durations, f)

        example_suite.runpytest("--store-durations", "--durations-path", durations_path)

        with open(durations_path) as f:
            durations = json.load(f)

        for item in old_durations:
            assert item in durations
        assert len(durations) == EXAMPLE_SUITE_TEST_COUNT + len(old_durations)

    def test_it_removes_old_when_cli_flag_used(self, example_suite, durations_path):
        old_durations = {"test_old1": 1, "test_old2": 2}
        with open(durations_path, "w") as f:
            json.dump(old_durations, f)

        example_suite.runpytest(
            "--store-durations", "--durations-path", durations_path, "--clean-durations"
        )

        with open(durations_path) as f:
            durations = json.load(f)

        for item in old_durations:
            assert item not in durations
        assert len(durations) == EXAMPLE_SUITE_TEST_COUNT

    def test_it_does_not_store_without_flag(self, example_suite, durations_path):
        example_suite.runpytest("--durations-path", durations_path)
        assert not os.path.exists(durations_path)


class TestSplitToSuites:
    parameters: ClassVar = [
        (
            1,
            1,
            "duration_based_chunks",
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
            ],
        ),
        (
            1,
            1,
            "least_duration",
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
            ],
        ),
        (
            2,
            1,
            "duration_based_chunks",
            ["test_1", "test_2", "test_3", "test_4", "test_5", "test_6", "test_7"],
        ),
        (2, 2, "duration_based_chunks", ["test_8", "test_9", "test_10"]),
        (2, 1, "least_duration", ["test_3", "test_5", "test_7", "test_9", "test_10"]),
        (2, 2, "least_duration", ["test_1", "test_2", "test_4", "test_6", "test_8"]),
        (
            3,
            1,
            "duration_based_chunks",
            ["test_1", "test_2", "test_3", "test_4", "test_5"],
        ),
        (3, 2, "duration_based_chunks", ["test_6", "test_7", "test_8"]),
        (3, 3, "duration_based_chunks", ["test_9", "test_10"]),
        (3, 1, "least_duration", ["test_3", "test_8", "test_10"]),
        (3, 2, "least_duration", ["test_4", "test_6", "test_9"]),
        (3, 3, "least_duration", ["test_1", "test_2", "test_5", "test_7"]),
        (4, 1, "duration_based_chunks", ["test_1", "test_2", "test_3", "test_4"]),
        (4, 2, "duration_based_chunks", ["test_5", "test_6", "test_7"]),
        (4, 3, "duration_based_chunks", ["test_8", "test_9"]),
        (4, 4, "duration_based_chunks", ["test_10"]),
        (4, 1, "least_duration", ["test_9", "test_10"]),
        (4, 2, "least_duration", ["test_1", "test_4", "test_6"]),
        (4, 3, "least_duration", ["test_2", "test_5", "test_7"]),
        (4, 4, "least_duration", ["test_3", "test_8"]),
    ]
    legacy_duration: ClassVar = [True, False]
    all_params: ClassVar = [
        (*param, legacy_flag)
        for param, legacy_flag in itertools.product(parameters, legacy_duration)
    ]
    enumerated_params: ClassVar = [(i, *param) for i, param in enumerate(all_params)]

    @pytest.mark.parametrize(
        ("test_idx", "splits", "group", "algo", "expected", "legacy_flag"),
        enumerated_params,
    )
    def test_it_splits(  # noqa: PLR0913
        self,
        test_idx,
        splits,
        group,
        algo,
        expected,
        legacy_flag,
        example_suite,
        durations_path,
    ):
        durations = {
            **{
                f"test_it_splits{test_idx}/test_it_splits.py::test_{num}": 1
                for num in range(1, 6)
            },
            **{
                f"test_it_splits{test_idx}/test_it_splits.py::test_{num}": 2
                for num in range(6, 11)
            },
        }
        if legacy_flag:
            # formats durations to legacy format
            durations = [list(tup) for tup in durations.items()]  # type: ignore[assignment]

        with open(durations_path, "w") as f:
            json.dump(durations, f)

        result = example_suite.inline_run(
            "--splits",
            str(splits),
            "--group",
            str(group),
            "--durations-path",
            durations_path,
            "--splitting-algorithm",
            algo,
        )
        result.assertoutcome(passed=len(expected))
        assert _passed_test_names(result) == expected

    def test_it_adapts_splits_based_on_new_and_deleted_tests(
        self, example_suite, durations_path
    ):
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

        result = example_suite.inline_run(
            "--splits", "3", "--group", "1", "--durations-path", durations_path
        )
        result.assertoutcome(passed=4)
        assert _passed_test_names(result) == ["test_1", "test_2", "test_3", "test_4"]

        result = example_suite.inline_run(
            "--splits", "3", "--group", "2", "--durations-path", durations_path
        )
        result.assertoutcome(passed=3)
        assert _passed_test_names(result) == ["test_5", "test_6", "test_7"]

        result = example_suite.inline_run(
            "--splits", "3", "--group", "3", "--durations-path", durations_path
        )
        result.assertoutcome(passed=3)
        assert _passed_test_names(result) == ["test_8", "test_9", "test_10"]

    def test_handles_case_of_no_durations_for_group(
        self, example_suite, durations_path
    ):
        with open(durations_path, "w") as f:
            json.dump({}, f)

        result = example_suite.inline_run(
            "--splits", "1", "--group", "1", "--durations-path", durations_path
        )
        assert result.ret == ExitCode.OK
        result.assertoutcome(passed=10)

    def test_it_splits_with_other_collect_hooks(self, testdir, durations_path):
        expected_tests_per_group = [
            ["test_1", "test_2", "test_3"],
            ["test_4", "test_5"],
        ]

        tests_to_run = "".join(
            f"@pytest.mark.mark_one\ndef test_{num}(): pass\n" for num in range(1, 6)
        )
        tests_to_exclude = "".join(f"def test_{num}(): pass\n" for num in range(6, 11))
        testdir.makepyfile(f"import pytest\n{tests_to_run}\n{tests_to_exclude}")

        durations = (
            {
                **{
                    f"test_it_splits_when_paired_with_marker_expressions.py::test_{num}": 1
                    for num in range(1, 3)
                },
                **{
                    f"test_it_splits_when_paired_with_marker_expressions.py::test_{num}": 2
                    for num in range(3, 6)
                },
            },
        )
        with open(durations_path, "w") as f:
            json.dump(durations[0], f)

        results = [
            testdir.inline_run(
                "--splits",
                2,
                "--group",
                group,
                "--durations-path",
                durations_path,
                "-m mark_one",
            )
            for group in range(1, 3)
        ]

        for result, expected_tests in zip(results, expected_tests_per_group):
            result.assertoutcome(passed=len(expected_tests))
            assert _passed_test_names(result) == expected_tests


class TestRaisesUsageErrors:
    def test_returns_nonzero_when_group_but_not_splits(self, example_suite, capsys):
        result = example_suite.inline_run("--group", "1")
        assert result.ret == ExitCode.USAGE_ERROR

        outerr = capsys.readouterr()
        assert "argument `--splits` is required" in outerr.err

    def test_returns_nonzero_when_splits_but_not_group(self, example_suite, capsys):
        result = example_suite.inline_run("--splits", "1")
        assert result.ret == ExitCode.USAGE_ERROR

        outerr = capsys.readouterr()
        assert "argument `--group` is required" in outerr.err

    def test_returns_nonzero_when_group_below_one(self, example_suite, capsys):
        result = example_suite.inline_run("--splits", "3", "--group", "0")
        assert result.ret == ExitCode.USAGE_ERROR

        outerr = capsys.readouterr()
        assert "argument `--group` must be >= 1 and <= 3" in outerr.err

    def test_returns_nonzero_when_group_larger_than_splits(self, example_suite, capsys):
        result = example_suite.inline_run("--splits", "3", "--group", "4")
        assert result.ret == ExitCode.USAGE_ERROR

        outerr = capsys.readouterr()
        assert "argument `--group` must be >= 1 and <= 3" in outerr.err

    def test_returns_nonzero_when_splits_below_one(self, example_suite, capsys):
        result = example_suite.inline_run("--splits", "0", "--group", "1")
        assert result.ret == ExitCode.USAGE_ERROR

        outerr = capsys.readouterr()
        assert "argument `--splits` must be >= 1" in outerr.err

    def test_returns_nonzero_when_invalid_algorithm_name(self, example_suite, capsys):
        result = example_suite.inline_run(
            "--splits", "0", "--group", "1", "--splitting-algorithm", "NON_EXISTENT"
        )
        assert result.ret == ExitCode.USAGE_ERROR

        outerr = capsys.readouterr()
        for err_content in [
            "argument --splitting-algorithm: invalid choice: 'NON_EXISTENT' ",
            *Algorithms.names(),
        ]:
            assert err_content in outerr.err


class TestHasExpectedOutput:
    def test_prints_splitting_summary_when_durations_present(
        self, example_suite, capsys, durations_path
    ):
        test_name = "test_prints_splitting_summary_when_durations_present"
        with open(durations_path, "w") as f:
            json.dump([[f"{test_name}0/{test_name}.py::test_1", 0.5]], f)
        result = example_suite.inline_run(
            "--splits", "1", "--group", "1", "--durations-path", durations_path
        )
        assert result.ret == ExitCode.OK

        outerr = capsys.readouterr()
        assert "[pytest-split] Running group 1/1" in outerr.out

    def test_does_not_print_splitting_summary_when_no_pytest_split_arguments(
        self, example_suite, capsys
    ):
        result = example_suite.inline_run()
        assert result.ret == ExitCode.OK

        outerr = capsys.readouterr()
        assert "[pytest-split]" not in outerr.out

    def test_prints_correct_number_of_selected_and_deselected_tests(
        self, example_suite, capsys, durations_path
    ):
        test_name = "test_prints_splitting_summary_when_durations_present"
        with open(durations_path, "w") as f:
            json.dump([[f"{test_name}0/{test_name}.py::test_1", 0.5]], f)
        result = example_suite.inline_run(
            "--splits", "5", "--group", "1", "--durations-path", durations_path
        )
        assert result.ret == ExitCode.OK

        outerr = capsys.readouterr()
        assert "collected 10 items / 8 deselected / 2 selected" in outerr.out

    def test_prints_estimated_duration(self, example_suite, capsys, durations_path):
        test_name = "test_prints_estimated_duration"
        with open(durations_path, "w") as f:
            json.dump([[f"{test_name}0/{test_name}.py::test_1", 0.5]], f)
        result = example_suite.inline_run(
            "--splits", "5", "--group", "1", "--durations-path", durations_path
        )
        assert result.ret == ExitCode.OK

        outerr = capsys.readouterr()
        assert (
            "[pytest-split] Running group 1/5 (estimated duration: 1.00s)" in outerr.out
        )

    def test_prints_used_algorithm(self, example_suite, capsys, durations_path):
        test_name = "test_prints_used_algorithm"
        with open(durations_path, "w") as f:
            json.dump([[f"{test_name}0/{test_name}.py::test_1", 0.5]], f)

        result = example_suite.inline_run(
            "--splits", "5", "--group", "1", "--durations-path", durations_path
        )
        assert result.ret == ExitCode.OK

        outerr = capsys.readouterr()
        assert (
            "[pytest-split] Splitting tests with algorithm: duration_based_chunks"
            in outerr.out
        )


def _passed_test_names(result):
    return [passed.nodeid.split("::")[-1] for passed in result.listoutcomes()[0]]
