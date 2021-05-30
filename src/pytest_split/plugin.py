import json
import os
from collections import defaultdict, OrderedDict
from typing import TYPE_CHECKING, Tuple, Generator
from warnings import warn

import _pytest
import pytest
from _pytest.config import create_terminal_writer
from _pytest.config.argparsing import Parser
from _pytest.main import Session

if TYPE_CHECKING:
    from typing import List

    from _pytest import nodes
    from _pytest.config import Config

# Ugly hacks for freezegun compatibility:
# https://github.com/spulec/freezegun/issues/286
STORE_DURATIONS_SETUP_AND_TEARDOWN_THRESHOLD = 60 * 10  # seconds
CACHE_PATH = ".pytest_cache/v/cache/pytest_split"

@pytest.hookimpl()
def pytest_addoption(parser: Parser) -> None:
    """
    Declare plugin options.
    """
    group = parser.getgroup(
        "Split tests into groups which execution time is about the same. "
        "Run first the whole suite with --store-durations to save information "
        "about test execution times"
    )
    group.addoption(
        "--durations-path",
        dest="durations_path",
        help=(
            "Path to the file in which durations are (to be) stored. "
            f"By default, durations will be written to {CACHE_PATH}"
        ),
        default=os.path.join(os.getcwd(), CACHE_PATH),
    )
    group.addoption(
        "--splits",
        dest="splits",
        type=int,
        help="The number of groups to split the tests into",
    )
    group.addoption(
        "--group",
        dest="group",
        type=int,
        help="The group of tests that should be executed (first one is 1)",
    )


@pytest.hookimpl(trylast=True)
def pytest_configure(config: "Config") -> None:
    """
    Configure plugin.
    """
    if (config.option.splits and not config.option.group) or (
        config.option.group and not config.option.split
    ):
        warn(
            "It looks like you passed an argument to run pytest with pytest-split, "
            "but both the `splits` and `group` arguments are required for pytest-split to run"
        )
    if config.option.splits and config.option.group:
        config.pluginmanager.register(PytestSplitPlugin(config), "pytestsplitplugin")


class PytestSplitPlugin:
    cache_file = "cache/pytest-split"

    def __init__(self, config: "Config") -> None:
        """
        Load cache and configure plugin.
        """
        self.cached_durations = dict(config.cache.get(self.cache_file, {}))
        if not self.cached_durations:
            warn(
                "No test durations found. Pytest-split will "
                "split tests evenly when no durations are found, "
                "so you should expect better results in following "
                "runs when test timings have been documented."
            )

    def pytest_collection_modifyitems(self, config: "Config", items: "List[nodes.Item]") -> Generator[None, None, None]:
        """
        Instruct Pytest to run the tests we've selected.

        This method is called by Pytest right after Pytest internals finishes
        collecting tests.

        See https://github.com/pytest-dev/pytest/blob/main/src/_pytest/main.py#L670.
        """
        # Load plugin arguments
        splits: int = config.option.splits
        group: int = config.option.group
        durations_report_path: str = config.option.durations_path

        total_tests_count = len(items)
        stored_durations = OrderedDict(config.cache.get(self.cache_file, {}))

        start_idx, end_idx = self._calculate_suite_start_and_end_idx(splits, group, items, stored_durations)
        items[:] = items[start_idx:end_idx]

        writer = create_terminal_writer(config)
        message = writer.markup(
            " Running group {}/{} ({}/{} tests)\n".format(
                group, splits, len(items), total_tests_count
            )
        )
        writer.line(message)

    def pytest_sessionfinish(self, session: "Session") -> None:
        if session.config.option.store_durations:
            report_path = session.config.option.durations_path
            terminal_reporter = session.config.pluginmanager.get_plugin(
                "terminalreporter"
            )
            durations = defaultdict(float)
            for test_reports in terminal_reporter.stats.values():
                for test_report in test_reports:
                    if hasattr(test_report, "duration"):
                        stage = getattr(test_report, "when", "")
                        duration = test_report.duration
                        # These ifs be removed after this is solved:
                        # https://github.com/spulec/freezegun/issues/286
                        if duration < 0:
                            continue
                        if (
                            stage in ("teardown", "setup")
                            and duration > STORE_DURATIONS_SETUP_AND_TEARDOWN_THRESHOLD
                        ):
                            # Ignore not legit teardown durations
                            continue
                        durations[test_report.nodeid] += test_report.duration

            with open(report_path, "w") as f:
                f.write(json.dumps(list(durations.items()), indent=2))

            terminal_writer = create_terminal_writer(session.config)
            message = terminal_writer.markup(
                " Stored test durations in {}\n".format(report_path)
            )
            terminal_reporter.write(message)

    @staticmethod
    def _calculate_suite_start_and_end_idx(splits: int, group: int, items: "List[nodes.Item]", stored_durations: OrderedDict) -> Tuple[int, int]:
        item_node_ids = [item.nodeid for item in items]
        stored_durations = {
            k: v for k, v in stored_durations.items() if k in item_node_ids
        }
        avg_duration_per_test = sum(stored_durations.values()) / len(stored_durations)

        durations = OrderedDict()
        for node_id in item_node_ids:
            durations[node_id] = stored_durations.get(node_id, avg_duration_per_test)

        time_per_group = sum(durations.values()) / splits
        start_time = time_per_group * (group - 1)
        end_time = time_per_group + start_time
        start_idx = end_idx = duration_rolling_sum = 0

        for idx, duration in enumerate(durations.values()):
            duration_rolling_sum += duration
            if group != 1 and not start_idx and duration_rolling_sum > start_time:
                start_idx = idx
                if group == splits:
                    break
            elif group != splits and not end_idx and duration_rolling_sum > end_time:
                end_idx = idx
                break
        if not end_idx:
            end_idx = len(items)

        return start_idx, end_idx
