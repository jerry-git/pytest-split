import itertools
import json
import os

import pytest


pytest_plugins = ["pytester"]


@pytest.fixture
def example_suite(testdir):
    testdir.makepyfile(
        """
    def test_1(): pass
    def test_2(): pass
    def test_3(): pass
    def test_4(): pass
    def test_5(): pass
    def test_6(): pass
    def test_7(): pass
    def test_8(): pass
    def test_9(): pass
    def test_10(): pass
    """
    )
    yield testdir


@pytest.fixture
def durations_path(tmpdir):
    return str(tmpdir.join(".durations"))


class TestStoreDurations:
    def test_it_stores(self, example_suite, durations_path):
        example_suite.runpytest("--store-durations", "--durations-path", durations_path)
        with open(durations_path) as f:
            durations = json.load(f)

        stored_tests = [d[0] for d in durations]
        assert stored_tests == [
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

        durations_per_test = [d[1] for d in durations]
        for duration in durations_per_test:
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
                    ["test_1", "test_2", "test_3", "test_4", "test_5", "test_6"],
                    ["test_7", "test_8", "test_9", "test_10"],
                ],
            ),
            (
                2,
                3,
                [
                    ["test_1", "test_2", "test_3", "test_4", "test_5"],
                    ["test_6", "test_7"],
                    ["test_8", "test_9", "test_10"],
                ],
            ),
            (
                3,
                4,
                [
                    ["test_1", "test_2", "test_3"],
                    ["test_4", "test_5", "test_6"],
                    ["test_7", "test_8"],
                    ["test_9", "test_10"],
                ],
            ),
        ],
    )
    def test_it_splits(
        self, param_idx, splits, expected_tests_per_group, example_suite, durations_path
    ):
        assert len(list(itertools.chain(*expected_tests_per_group))) == 10

        durations = [
            ["test_it_splits{}/test_it_splits.py::test_1".format(param_idx), 1],
            ["test_it_splits{}/test_it_splits.py::test_2".format(param_idx), 1],
            ["test_it_splits{}/test_it_splits.py::test_3".format(param_idx), 1],
            ["test_it_splits{}/test_it_splits.py::test_4".format(param_idx), 1],
            ["test_it_splits{}/test_it_splits.py::test_5".format(param_idx), 1],
            ["test_it_splits{}/test_it_splits.py::test_6".format(param_idx), 2],
            ["test_it_splits{}/test_it_splits.py::test_7".format(param_idx), 2],
            ["test_it_splits{}/test_it_splits.py::test_8".format(param_idx), 2],
            ["test_it_splits{}/test_it_splits.py::test_9".format(param_idx), 2],
            ["test_it_splits{}/test_it_splits.py::test_10".format(param_idx), 2],
        ]

        with open(durations_path, "w") as f:
            json.dump(durations, f)

        results = []
        for group in range(splits):
            results.append(
                example_suite.inline_run(
                    "--splits",
                    str(splits),
                    "--group",
                    str(group + 1),
                    "--durations-path",
                    durations_path,
                )
            )

        for result, expected_tests in zip(results, expected_tests_per_group):
            result.assertoutcome(passed=len(expected_tests))
            assert _passed_test_names(result) == expected_tests

    def test_it_does_not_split_with_invalid_args(self, example_suite, durations_path):
        durations = [["test_it_does_not_split_with_invalid_args.py::test_1", 1]]
        with open(durations_path, "w") as f:
            json.dump(durations, f)

        result = example_suite.inline_run(
            "--splits", "2", "--group", "1"
        )  # no durations report in default location
        result.assertoutcome(passed=10)

    def test_it_adapts_splits_based_on_new_and_deleted_tests(
        self, example_suite, durations_path
    ):
        # Only 4/10 tests listed here, avg duration 1 sec
        test_path = (
            "test_it_adapts_splits_based_on_new_and_deleted_tests0/"
            "test_it_adapts_splits_based_on_new_and_deleted_tests.py::{}"
        )
        durations = [
            [test_path.format("test_1"), 1],
            [test_path.format("test_5"), 2.6],
            [test_path.format("test_6"), 0.2],
            [test_path.format("test_10"), 0.2],
            [test_path.format("test_THIS_IS_NOT_IN_THE_SUITE"), 1000],
        ]

        with open(durations_path, "w") as f:
            json.dump(durations, f)

        result = example_suite.inline_run(
            "--splits", "3", "--group", "1", "--durations-path", durations_path
        )  # no --group
        result.assertoutcome(passed=3)
        assert _passed_test_names(result) == ["test_1", "test_2", "test_3"]

        result = example_suite.inline_run(
            "--splits", "3", "--group", "2", "--durations-path", durations_path
        )  # no --group
        result.assertoutcome(passed=2)
        assert _passed_test_names(result) == ["test_4", "test_5"]

        result = example_suite.inline_run(
            "--splits", "3", "--group", "3", "--durations-path", durations_path
        )  # no --group
        result.assertoutcome(passed=5)
        assert _passed_test_names(result) == [
            "test_6",
            "test_7",
            "test_8",
            "test_9",
            "test_10",
        ]


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
        result = example_suite.inline_run("--splits", "3", "--group", 0)
        assert result.ret == 4

        outerr = capsys.readouterr()
        assert "argument `--group` must be >= 1 and <= 3" in outerr.err

    def test_returns_nonzero_when_group_larger_than_splits(self, example_suite, capsys):
        result = example_suite.inline_run("--splits", "3", "--group", 4)
        assert result.ret == 4

        outerr = capsys.readouterr()
        assert "argument `--group` must be >= 1 and <= 3" in outerr.err

    def test_returns_nonzero_when_splits_below_one(self, example_suite, capsys):
        result = example_suite.inline_run("--splits", "0", "--group", "1")
        assert result.ret == 4

        outerr = capsys.readouterr()
        assert "argument `--splits` must be >= 1" in outerr.err


class TestHasExpectedOutput:
    def test_prints_splitting_summary(self, example_suite, capsys):
        result = example_suite.inline_run("--splits", "1", "--group", 1)
        assert result.ret == 0

        outerr = capsys.readouterr()
        assert "[pytest-split] Running group 1/1 (10/10) tests" in outerr.out

    def test_prints_splitting_summary_when_splits_missing(self, example_suite, capsys):
        result = example_suite.inline_run("--splits", 1, "--group", "1")
        assert result.ret == 0

        outerr = capsys.readouterr()
        assert "[pytest-split] Not splitting tests because the durations_report is missing" in outerr.out

    def test_prints_splitting_summary_when_durations_missing(self, example_suite, capsys, durations_path):
        test_name = "test_prints_splitting_summary_when_durations_missing"
        with open(durations_path, "w") as f:
            json.dump([[f"{test_name}0/{test_name}.py::test_1", 0.5]], f)

        result = example_suite.inline_run(
            "--splits", 1, "--group", "1", "--durations-path", durations_path, "--store-durations"
        )
        assert result.ret == 0

        outerr = capsys.readouterr()
        assert "[pytest-split] Not splitting tests because we are storing durations" in outerr.out

    def test_prints_splitting_summary_when_no_pytest_split_arguments(self, example_suite, capsys):
        result = example_suite.inline_run()
        assert result.ret == 0

        outerr = capsys.readouterr()
        assert "[pytest-split] Running group 1/1 (10/10) tests" in outerr.out


def _passed_test_names(result):
    return [passed.nodeid.split("::")[-1] for passed in result.listoutcomes()[0]]
