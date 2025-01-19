import itertools
from collections import namedtuple
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from typing import List, Set

    from _pytest.nodes import Item

from pytest_split.algorithms import (
    AlgorithmBase,
    Algorithms,
)

item = namedtuple("item", "nodeid")  # noqa: PYI024


@dataclass
class DummyPytestItem:
    name: str
    nodeid: str

    def __repr__(self) -> str:
        return "<{} {}>".format(self.__class__.__name__, getattr(self, "name", None))

    def __eq__(self, value: object) -> bool:
        self.nodeid == value.nodeid

class TestAlgorithms:
    @pytest.mark.parametrize("algo_name", Algorithms.names())
    def test__split_test(self, algo_name):
        durations = {"a": 1, "b": 1, "c": 1}
        items = [item(x) for x in durations]
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
    def test__split_tests_handles_tests_in_durations_but_missing_from_items(
        self, algo_name
    ):
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

    def test__split_test_handles_large_duration_at_end(self):
        """NOTE: only least_duration does this correctly"""
        durations = {"a": 1, "b": 1, "c": 1, "d": 3}
        items = [item(x) for x in ["a", "b", "c", "d"]]
        algo = Algorithms["least_duration"].value
        splits = algo(splits=2, items=items, durations=durations)

        first, second = splits
        assert first.selected == [item("d")]
        assert second.selected == [item(x) for x in ["a", "b", "c"]]

    @pytest.mark.parametrize(
        ("algo_name", "expected"),
        [
            ("duration_based_chunks", [[item("a"), item("b")], [item("c"), item("d")]]),
            ("least_duration", [[item("a"), item("c")], [item("b"), item("d")]]),
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
        splits = algo(splits=2, items=items, durations=durations)

        first, second = splits
        expected_first, expected_second = expected
        assert first.selected == expected_first
        assert second.selected == expected_second

    @pytest.mark.parametrize(
        ("algo_name", "expected"),
        [
            (
                "duration_based_chunks",
                [[item("a"), item("b"), item("c"), item("d"), item("e")], []],
            ),
            (
                "least_duration",
                [[item("e")], [item("a"), item("b"), item("c"), item("d")]],
            ),
        ],
    )
    def test__split_tests_maintains_relative_order_of_tests(self, algo_name, expected):
        durations = {"a": 2, "b": 3, "c": 4, "d": 5, "e": 10000}
        items = [item(x) for x in ["a", "b", "c", "d", "e"]]
        algo = Algorithms[algo_name].value
        splits = algo(splits=2, items=items, durations=durations)

        first, second = splits
        expected_first, expected_second = expected
        assert first.selected == expected_first
        assert second.selected == expected_second

    def test__split_tests_same_set_regardless_of_order(self):
        """NOTE: only least_duration does this correctly"""
        tests = ["a", "b", "c", "d", "e", "f", "g"]
        durations = {t: 1 for t in tests}
        items = [item(t) for t in tests]
        algo = Algorithms["least_duration"].value
        for n in (2, 3, 4):
            selected_each: List[Set[Item]] = [set() for _ in range(n)]
            for order in itertools.permutations(items):
                splits = algo(splits=n, items=order, durations=durations)
                for i, group in enumerate(splits):
                    if not selected_each[i]:
                        selected_each[i] = set(group.selected)
                    assert selected_each[i] == set(group.selected)

    def test__algorithms_members_derived_correctly(self):
        for a in Algorithms.names():
            assert issubclass(Algorithms[a].value.__class__, AlgorithmBase)

    def test__split_tests_correctly_same_names_with_real_items(self, tmp_path):
        """Test that least_duration algorithm works correctly with real pytest Items
        that have same names but different paths."""
        items = [
            DummyPytestItem(
                name="test_something_a", nodeid="dir_a/test.py::test_something_a"
            ),
            DummyPytestItem(
                name="test_something_a", nodeid="dir_b/test.py::test_something_a"
            ),
            DummyPytestItem(
                name="test_something_b", nodeid="dir_a/test.py::test_something_b"
            ),
            DummyPytestItem(
                name="test_something_b", nodeid="dir_b/test.py::test_something_b"
            ),
        ]

        first_randomization = (0, 1, 2, 3)
        second_randomization = (1, 0, 3, 2)

        expected_groups = [[items[0], items[1]], [items[2], items[3]]]

        durations = {item.nodeid: 1 for item in items}

        algo = Algorithms["least_duration"].value
        split_number = 2

        for randomization in (first_randomization, second_randomization):
            randomized_items = [items[index] for index in randomization]
            splits = algo(
                splits=split_number, items=randomized_items, durations=durations
            )

            for index, group in enumerate(splits):
                assert (
                    sorted(group.selected, key=lambda item: item.nodeid)
                    == expected_groups[index]
                )

class MyAlgorithm(AlgorithmBase):
    def __call__(self, a, b, c):
        """no-op"""


class MyOtherAlgorithm(AlgorithmBase):
    def __call__(self, a, b, c):
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
