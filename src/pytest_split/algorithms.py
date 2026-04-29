import enum
import heapq
from abc import ABC, abstractmethod
from operator import itemgetter
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from _pytest import nodes


class TestGroup(NamedTuple):
    selected: "list[nodes.Item]"
    deselected: "list[nodes.Item]"
    duration: float


class AlgorithmBase(ABC):
    """Abstract base class for the algorithm implementations."""

    @abstractmethod
    def __call__(
        self, splits: int, durations: "dict[nodes.Item, float]"
    ) -> "list[TestGroup]":
        pass

    def __hash__(self) -> int:
        return hash(self.__class__.__name__)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AlgorithmBase):
            return NotImplemented
        return self.__class__.__name__ == other.__class__.__name__


class LeastDurationAlgorithm(AlgorithmBase):
    """
    Split tests into groups by runtime.
    It walks the test items, starting with the test with largest duration.
    It assigns the test with the largest runtime to the group with the smallest duration sum.

    The algorithm sorts the items by their duration. Since the sorting algorithm is stable, ties will be broken by
    maintaining the original order of items. It is therefore important that the order of items be identical on all nodes
    that use this plugin. Due to issue #25 this might not always be the case.

    The order of ``selected`` items in each returned group is implementation-defined; the plugin reorders the chosen
    group in pytest's collection order before execution.

    :param splits: How many groups we're splitting in.
    :param durations: Mapping from each test item to its duration. Build it with :func:`compute_durations`.
    :return:
        List of groups
    """

    def __call__(
        self, splits: int, durations: "dict[nodes.Item, float]"
    ) -> "list[TestGroup]":
        # Sort by duration descending so the heap-based assignment
        # processes the largest tests first - greedy first-fit-decreasing
        # for the smallest-running-total bin.
        sorted_items_with_durations = sorted(
            durations.items(), key=itemgetter(1), reverse=True
        )

        selected: list[list[nodes.Item]] = [[] for _ in range(splits)]
        deselected: list[list[nodes.Item]] = [[] for _ in range(splits)]
        duration: list[float] = [0 for _ in range(splits)]

        # create a heap of the form (summed_durations, group_index)
        heap: list[tuple[float, int]] = [(0, i) for i in range(splits)]
        heapq.heapify(heap)
        for item, item_duration in sorted_items_with_durations:
            # get group with smallest sum
            summed_durations, group_idx = heapq.heappop(heap)
            new_group_durations = summed_durations + item_duration

            # store assignment
            selected[group_idx].append(item)
            duration[group_idx] = new_group_durations
            for i in range(splits):
                if i != group_idx:
                    deselected[i].append(item)

            # store new duration - in case of ties it sorts by the group_idx
            heapq.heappush(heap, (new_group_durations, group_idx))

        return [
            TestGroup(
                selected=selected[i], deselected=deselected[i], duration=duration[i]
            )
            for i in range(splits)
        ]


class DurationBasedChunksAlgorithm(AlgorithmBase):
    """
    Split tests into groups by runtime.
    Ensures tests are split into non-overlapping groups.
    The original list of test items is split into groups by finding boundary indices i_0, i_1, i_2
    and creating group_1 = items[0:i_0], group_2 = items[i_0, i_1], group_3 = items[i_1, i_2], ...

    :param splits: How many groups we're splitting in.
    :param durations: Mapping from each test item to its duration. Build it with :func:`compute_durations`.
    :return: List of TestGroup
    """

    def __call__(
        self, splits: int, durations: "dict[nodes.Item, float]"
    ) -> "list[TestGroup]":
        time_per_group = sum(durations.values()) / splits

        selected: list[list[nodes.Item]] = [[] for i in range(splits)]
        deselected: list[list[nodes.Item]] = [[] for i in range(splits)]
        duration: list[float] = [0 for i in range(splits)]

        group_idx = 0
        for item, item_duration in durations.items():
            if duration[group_idx] >= time_per_group:
                group_idx += 1

            selected[group_idx].append(item)
            for i in range(splits):
                if i != group_idx:
                    deselected[i].append(item)
            duration[group_idx] += item_duration

        return [
            TestGroup(
                selected=selected[i], deselected=deselected[i], duration=duration[i]
            )
            for i in range(splits)
        ]


def compute_durations(
    items: "list[nodes.Item]", cached_durations: "dict[str, float]"
) -> "dict[nodes.Item, float]":
    """
    Build the splitting input from collected items and their cached durations.

    Items missing from ``cached_durations`` get the average duration of the
    cached entries that are relevant to this suite; with no cached data at
    all, every item gets ``1`` as a placeholder.
    """
    # Filtering down durations to relevant ones ensures the avg isn't skewed by irrelevant data
    relevant = {
        item.nodeid: cached_durations[item.nodeid]
        for item in items
        if item.nodeid in cached_durations
    }
    if relevant:
        avg = sum(relevant.values()) / len(relevant)
    else:
        # If there are no durations, give every test the same arbitrary value
        avg = 1
    return {item: relevant.get(item.nodeid, avg) for item in items}


def select_in_collection_order(
    group: TestGroup, items: "list[nodes.Item]"
) -> TestGroup:
    """
    Rebuild ``group`` so that ``selected`` and ``deselected`` filter
    ``items`` in their original collection order, keyed on nodeid.
    """
    selected_ids = {it.nodeid for it in group.selected}
    return TestGroup(
        selected=[it for it in items if it.nodeid in selected_ids],
        deselected=[it for it in items if it.nodeid not in selected_ids],
        duration=group.duration,
    )


class Algorithms(enum.Enum):
    duration_based_chunks = DurationBasedChunksAlgorithm()
    least_duration = LeastDurationAlgorithm()

    @staticmethod
    def names() -> "list[str]":
        return [x.name for x in Algorithms]
