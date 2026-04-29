import itertools
from collections import namedtuple
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.nodes import Item

from pytest_split.algorithms import (
    AlgorithmBase,
    Algorithms,
    TestGroup,
    compute_durations,
    select_in_collection_order,
)

item = namedtuple("item", "nodeid")  # noqa: PYI024


class TestAlgorithms:
    @pytest.mark.parametrize("algo_name", Algorithms.names())
    def test__split_test(self, algo_name):
        durations = {"a": 1, "b": 1, "c": 1}
        items = [item(x) for x in durations]
        algo = Algorithms[algo_name].value

        first, second, third = algo(
            splits=3, durations=compute_durations(items, durations)
        )

        # each split should have one test
        assert first == TestGroup(
            selected=[item("a")],
            deselected=[item("b"), item("c")],
            duration=1,
        )
        assert second == TestGroup(
            selected=[item("b")],
            deselected=[item("a"), item("c")],
            duration=1,
        )
        assert third == TestGroup(
            selected=[item("c")],
            deselected=[item("a"), item("b")],
            duration=1,
        )

    @pytest.mark.parametrize("algo_name", Algorithms.names())
    def test__split_tests_handles_tests_in_durations_but_missing_from_items(
        self, algo_name
    ):
        durations = {"a": 1, "b": 1}
        items = [item(x) for x in ["a"]]
        algo = Algorithms[algo_name].value

        first, second = algo(splits=2, durations=compute_durations(items, durations))

        assert first == TestGroup(
            selected=[item("a")], deselected=[], duration=1
        )
        assert second == TestGroup(
            selected=[], deselected=[item("a")], duration=0
        )

    @pytest.mark.parametrize("algo_name", Algorithms.names())
    def test__split_tests_handles_tests_with_missing_durations(self, algo_name):
        durations = {"a": 1}
        items = [item(x) for x in ["a", "b"]]
        algo = Algorithms[algo_name].value

        first, second = algo(splits=2, durations=compute_durations(items, durations))

        assert first == TestGroup(
            selected=[item("a")], deselected=[item("b")], duration=1
        )
        assert second == TestGroup(
            selected=[item("b")], deselected=[item("a")], duration=1
        )

    def test__split_test_handles_large_duration_at_end(self):
        """NOTE: only least_duration does this correctly"""
        durations = {"a": 1, "b": 1, "c": 1, "d": 3}
        items = [item(x) for x in ["a", "b", "c", "d"]]
        algo = Algorithms["least_duration"].value

        first, second = algo(splits=2, durations=compute_durations(items, durations))

        assert first == TestGroup(
            selected=[item("d")],
            deselected=[item("a"), item("b"), item("c")],
            duration=3,
        )
        assert second == TestGroup(
            selected=[item("a"), item("b"), item("c")],
            deselected=[item("d")],
            duration=3,
        )

    @pytest.mark.parametrize(
        ("algo_name", "expected"),
        [
            (
                "duration_based_chunks",
                [
                    TestGroup(
                        selected=[item("a"), item("b")],
                        deselected=[item("c"), item("d")],
                        duration=2,
                    ),
                    TestGroup(
                        selected=[item("c"), item("d")],
                        deselected=[item("a"), item("b")],
                        duration=2,
                    ),
                ],
            ),
            (
                "least_duration",
                [
                    TestGroup(
                        selected=[item("a"), item("c")],
                        deselected=[item("b"), item("d")],
                        duration=2,
                    ),
                    TestGroup(
                        selected=[item("b"), item("d")],
                        deselected=[item("a"), item("c")],
                        duration=2,
                    ),
                ],
            ),
        ],
    )
    def test__split_tests_calculates_avg_test_duration_only_on_present_tests(
        self, algo_name, expected
    ):
        # If the algo includes test e's duration to calculate the averge then
        # a will be expected to take a long time, and so 'a' will become its
        # own group. Intended behaviour is that a gets estimated duration 1 and
        # this will create more balanced groups.
        durations = {"b": 1, "c": 1, "d": 1, "e": 10000}
        items = [item(x) for x in ["a", "b", "c", "d"]]
        algo = Algorithms[algo_name].value

        groups = algo(splits=2, durations=compute_durations(items, durations))

        assert groups == expected

    @pytest.mark.parametrize(
        ("algo_name", "expected"),
        [
            (
                "duration_based_chunks",
                [
                    TestGroup(
                        selected=[item(x) for x in "abcde"],
                        deselected=[],
                        duration=10014,
                    ),
                    TestGroup(
                        selected=[],
                        deselected=[item(x) for x in "abcde"],
                        duration=0,
                    ),
                ],
            ),
            (
                "least_duration",
                # selected/deselected are in heap-pop order (duration desc)
                # since the algorithm no longer restores input order.
                [
                    TestGroup(
                        selected=[item("e")],
                        deselected=[item(x) for x in "dcba"],
                        duration=10000,
                    ),
                    TestGroup(
                        selected=[item(x) for x in "dcba"],
                        deselected=[item("e")],
                        duration=14,
                    ),
                ],
            ),
        ],
    )
    def test__split_tests_maintains_relative_order_of_tests(self, algo_name, expected):
        durations = {"a": 2, "b": 3, "c": 4, "d": 5, "e": 10000}
        items = [item(x) for x in ["a", "b", "c", "d", "e"]]
        algo = Algorithms[algo_name].value

        groups = algo(splits=2, durations=compute_durations(items, durations))

        assert groups == expected

    def test__split_tests_same_set_regardless_of_order(self):
        """NOTE: only least_duration does this correctly"""
        tests = ["a", "b", "c", "d", "e", "f", "g"]
        durations = {t: 1 for t in tests}
        items = [item(t) for t in tests]
        algo = Algorithms["least_duration"].value
        for n in (2, 3, 4):
            selected_each: list[set[Item]] = [set() for _ in range(n)]
            for order in itertools.permutations(items):
                splits = algo(
                    splits=n,
                    durations=compute_durations(list(order), durations),
                )
                for i, group in enumerate(splits):
                    if not selected_each[i]:
                        selected_each[i] = set(group.selected)
                    assert selected_each[i] == set(group.selected)

    def test__algorithms_members_derived_correctly(self):
        for a in Algorithms.names():
            assert issubclass(Algorithms[a].value.__class__, AlgorithmBase)


class TestComputeDurations:
    def test_uses_real_durations_avg_fills_missing_ignores_irrelevant(self):
        # "ghost" isn't in the suite so it's excluded from the avg, and "c"
        # gets the avg of "a" and "b": (2.0 + 4.0) / 2 = 3.0.
        items = [item("a"), item("b"), item("c")]
        cached = {"a": 2.0, "b": 4.0, "ghost": 10000.0}
        assert compute_durations(items, cached) == {
            item("a"): 2.0,
            item("b"): 4.0,
            item("c"): 3.0,
        }

    def test_falls_back_to_one_when_no_relevant_durations(self):
        assert compute_durations([item("a"), item("b")], {}) == {
            item("a"): 1,
            item("b"): 1,
        }

    def test_returned_dict_iterates_in_input_order(self):
        items = [item("c"), item("a"), item("b")]
        assert list(compute_durations(items, {"a": 1, "b": 2, "c": 3})) == items


class TestSelectInCollectionOrder:
    def test_rebuilds_selected_and_deselected_in_input_order(self):
        items = [item("a"), item("b"), item("c"), item("d")]
        # Algorithm returned membership in some other order.
        group = TestGroup(
            selected=[item("c"), item("a")],
            deselected=[item("d"), item("b")],
            duration=5.0,
        )

        result = select_in_collection_order(group, items)

        assert result.selected == [item("a"), item("c")]
        assert result.deselected == [item("b"), item("d")]
        assert result.duration == 5.0


class MyAlgorithm(AlgorithmBase):
    def __call__(self, a, b):
        """no-op"""


class MyOtherAlgorithm(AlgorithmBase):
    def __call__(self, a, b):
        """no-op"""


class TestAbstractAlgorithm:
    def test__hash__returns_correct_result(self):
        algo = MyAlgorithm()
        assert algo.__hash__() == hash(algo.__class__.__name__)

    def test__hash__returns_same_hash_for_same_class_instances(self):
        algo1 = MyAlgorithm()
        algo2 = MyAlgorithm()
        assert algo1.__hash__() == algo2.__hash__()

    def test__hash__returns_different_hash_for_different_classes(self):
        algo1 = MyAlgorithm()
        algo2 = MyOtherAlgorithm()
        assert algo1.__hash__() != algo2.__hash__()

    def test__eq__returns_true_for_same_instance(self):
        algo = MyAlgorithm()
        assert algo.__eq__(algo) is True

    def test__eq__returns_false_for_different_instance(self):
        algo1 = MyAlgorithm()
        algo2 = MyOtherAlgorithm()
        assert algo1.__eq__(algo2) is False

    def test__eq__returns_true_for_same_algorithm_different_instance(self):
        algo1 = MyAlgorithm()
        algo2 = MyAlgorithm()
        assert algo1.__eq__(algo2) is True

    def test__eq__returns_false_for_non_algorithm_object(self):
        algo = MyAlgorithm()
        other = "not an algorithm"
        assert algo.__eq__(other) is NotImplemented
