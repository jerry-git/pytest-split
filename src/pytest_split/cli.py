import argparse
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Dict


def list_slowest_tests() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--durations-path",
        help=(
            "Path to the file in which durations are stored, "
            "default is .test_durations in the current working directory"
        ),
        default=".test_durations",
        type=argparse.FileType(),
    )
    parser.add_argument(
        "-c",
        "--count",
        help="How many slowest to list",
        default=10,
        type=int,
    )
    args = parser.parse_args()
    return _list_slowest_tests(json.load(args.durations_path), args.count)


def _list_slowest_tests(durations: "Dict[str, float]", count: int) -> None:
    slowest_tests = tuple(
        sorted(durations.items(), key=lambda item: item[1], reverse=True)
    )[:count]
    for test, duration in slowest_tests:
        print(f"{duration:.2f} {test}")  # noqa: T001
