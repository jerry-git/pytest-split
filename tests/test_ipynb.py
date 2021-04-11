import itertools
import json
import os

import pytest


pytest_plugins = ["pytester"]


@pytest.fixture
def example_suite(testdir):
    testdir.makefile(
        ".ipynb",
        """
        {
          "cells": [
            {"cell_type": "code", "source": ["assert 1 == 1"]},
            {"cell_type": "code", "source": ["assert 1 == 1"]},
            {"cell_type": "code", "source": ["assert 1 == 1"]},
            {"cell_type": "code", "source": ["assert 1 == 1"]},
            {"cell_type": "code", "source": ["assert 1 == 1"]}
          ]
        }
        """
    )
    yield testdir


@pytest.fixture
def durations_path(tmpdir):
    return str(tmpdir.join(".durations"))


class TestStoreDurations:
    def test_it_stores(self, example_suite, durations_path):
        example_suite.runpytest("--nbval", "--store-durations", "--durations-path", durations_path)
        with open(durations_path) as f:
            durations = json.load(f)

        stored_tests = [d[0] for d in durations]
        assert stored_tests == [
            "test_it_stores.ipynb::Cell 0",
            "test_it_stores.ipynb::Cell 1",
            "test_it_stores.ipynb::Cell 2",
            "test_it_stores.ipynb::Cell 3",
            "test_it_stores.ipynb::Cell 4"
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
        [(0, 1, [["Cell 0", "Cell 1", "Cell 2", "Cell 3", "Cell 4"]]),
         (1, 2, [["Cell 0", "Cell 1", "Cell 2", "Cell 3", "Cell 4"]]),
         (2, 3, [["Cell 0", "Cell 1", "Cell 2", "Cell 3", "Cell 4"]])]
    )
    def test_it_splits(
        self,
        param_idx,
        splits,
        expected_tests_per_group,
        example_suite,
        durations_path
    ):
        assert len(list(itertools.chain(*expected_tests_per_group))) == 5

        durations = [
            ["test_it_splits{}/test_it_splits.ipynb::Cell 0".format(param_idx), 1],
            ["test_it_splits{}/test_it_splits.ipynb::Cell 1".format(param_idx), 1],
            ["test_it_splits{}/test_it_splits.ipynb::Cell 2".format(param_idx), 1],
            ["test_it_splits{}/test_it_splits.ipynb::Cell 3".format(param_idx), 1],
            ["test_it_splits{}/test_it_splits.ipynb::Cell 4".format(param_idx), 1]
        ]

        with open(durations_path, "w") as f:
            json.dump(durations, f)

        results = []
        for group in range(splits):
            results.append(
                example_suite.inline_run(
                    "--nbval",
                    "--splits", str(splits),
                    "--group", str(group + 1),
                    "--durations-path", durations_path
                )
            )

        for result, expected_tests in zip(results, expected_tests_per_group):
            result.assertoutcome(passed=len(expected_tests))
            assert _passed_test_names(result) == expected_tests


def _passed_test_names(result):
    return [passed.nodeid.split("::")[-1] for passed in result.listoutcomes()[0]]


if __name__ == "__main__":
    args = "test_ipynb.py"
    pytest.main(args.split(" "))
