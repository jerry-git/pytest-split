from collections import namedtuple

import pytest

from pytest_split.algorithms import Algorithms

item = namedtuple("item", "nodeid")


class TestAlgorithms:
    @pytest.mark.parametrize("algo_name", Algorithms.names())
    def test__split_test(self, algo_name):
        durations = {"a": 1, "b": 1, "c": 1}
        items = [item(x) for x in durations.keys()]
        algo = Algorithms[algo_name].value
        first, second, third = algo(splits=3, items=items, durations=durations)

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

    @pytest.mark.parametrize("algo_name", Algorithms.names())
    def test__split_tests_handles_tests_in_durations_but_missing_from_items(self, algo_name):
        durations = {"a": 1, "b": 1}
        items = [item(x) for x in ["a"]]
        algo = Algorithms[algo_name].value
        splits = algo(splits=2, items=items, durations=durations)

        first, second = splits
        assert first.selected == [item("a")]
        assert second.selected == []

    @pytest.mark.parametrize("algo_name", Algorithms.names())
    def test__split_tests_handles_tests_with_missing_durations(self, algo_name):
        durations = {"a": 1}
        items = [item(x) for x in ["a", "b"]]
        algo = Algorithms[algo_name].value
        splits = algo(splits=2, items=items, durations=durations)

        first, second = splits
        assert first.selected == [item("a")]
        assert second.selected == [item("b")]

    @pytest.mark.parametrize("algo_name", Algorithms.names())
    @pytest.mark.skip("current algorithm does handle this well")
    def test__split_test_handles_large_duration_at_end(self, algo_name):
        durations = {"a": 1, "b": 1, "c": 1, "d": 3}
        items = [item(x) for x in ["a", "b", "c", "d"]]
        algo = Algorithms[algo_name].value
        splits = algo(splits=2, items=items, durations=durations)

        first, second = splits
        assert first.selected == [item("d")]
        assert second.selected == [item(x) for x in ["a", "b", "c"]]

    @pytest.mark.parametrize(
        "algo_name, expected",
        [
            ("duration_based_chunks", [[item("a"), item("b")], [item("c"), item("d")]]),
            ("least_duration", [[item("a"), item("c")], [item("b"), item("d")]]),
        ],
    )
    def test__split_tests_calculates_avg_test_duration_only_on_present_tests(self, algo_name, expected):
        # If the algo includes test e's duration to calculate the averge then
        # a will be expected to take a long time, and so 'a' will become its
        # own group. Intended behaviour is that a gets estimated duration 1 and
        # this will create more balanced groups.
        durations = {"b": 1, "c": 1, "d": 1, "e": 10000}
        items = [item(x) for x in ["a", "b", "c", "d"]]
        algo = Algorithms[algo_name].value
        splits = algo(splits=2, items=items, durations=durations)

        first, second = splits
        expected_first, expected_second = expected
        assert first.selected == expected_first
        assert second.selected == expected_second
