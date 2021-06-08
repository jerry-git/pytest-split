import json
import os
from typing import TYPE_CHECKING

import pytest
from _pytest.config import create_terminal_writer, hookimpl
from _pytest.reports import TestReport

if TYPE_CHECKING:
    from typing import List, Optional, Tuple, Union

    from _pytest import nodes
    from _pytest.config import Config
    from _pytest.config.argparsing import Parser
    from _pytest.main import ExitCode

# Ugly hack for freezegun compatibility: https://github.com/spulec/freezegun/issues/286
STORE_DURATIONS_SETUP_AND_TEARDOWN_THRESHOLD = 60 * 10  # seconds


def pytest_addoption(parser: "Parser") -> None:
    """
    Declare pytest-split's options.
    """
    group = parser.getgroup(
        "Split tests into groups which execution time is about the same. "
        "Run with --store-durations to store information about test execution times."
    )
    group.addoption(
        "--store-durations",
        dest="store_durations",
        action="store_true",
        help="Store durations into '--durations-path'.",
    )
    group.addoption(
        "--durations-path",
        dest="durations_path",
        help=(
            "Path to the file in which durations are (to be) stored, "
            "default is .test_durations in the current working directory"
        ),
        default=os.path.join(os.getcwd(), ".test_durations"),
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


@pytest.mark.tryfirst
def pytest_cmdline_main(config: "Config") -> "Optional[Union[int, ExitCode]]":
    """
    Validate options.
    """
    group = config.getoption("group")
    splits = config.getoption("splits")

    if splits is None and group is None:
        return None

    if splits and group is None:
        raise pytest.UsageError("argument `--group` is required")

    if group and splits is None:
        raise pytest.UsageError("argument `--splits` is required")

    if splits < 1:
        raise pytest.UsageError("argument `--splits` must be >= 1")

    if group < 1 or group > splits:
        raise pytest.UsageError(f"argument `--group` must be >= 1 and <= {splits}")

    return None


def pytest_configure(config: "Config") -> None:
    """
    Enable the plugins we need.
    """
    if config.option.splits and config.option.group:
        config.pluginmanager.register(PytestSplitPlugin(config), "pytestsplitplugin")

    if config.option.store_durations:
        config.pluginmanager.register(PytestSplitCachePlugin(config), "pytestsplitcacheplugin")


class Base:
    def __init__(self, config: "Config") -> None:
        """
        Load durations and set up a terminal writer.

        This logic is shared for both the split- and cache plugin.
        """
        self.config = config
        self.writer = create_terminal_writer(self.config)

        try:
            with open(config.option.durations_path, "r") as f:
                self.cached_durations = json.loads(f.read())
        except FileNotFoundError:
            self.cached_durations = {}

        # This code provides backwards compatibility after we switched
        # from saving durations in a list-of-lists to a dict format
        # Remove this when bumping to v1
        if isinstance(self.cached_durations, list):
            self.cached_durations = {test_name: duration for test_name, duration in self.cached_durations}


class PytestSplitPlugin(Base):
    def __init__(self, config: "Config"):
        super().__init__(config)

        self._messages: "List[str]" = []

        if not self.cached_durations:
            message = self.writer.markup(
                "\n[pytest-split] No test durations found. Pytest-split will "
                "split tests evenly when no durations are found. "
                "\n[pytest-split] You can expect better results in consequent runs, "
                "when test timings have been documented.\n"
            )
            self.writer.line(message)

    @hookimpl(tryfirst=True)
    def pytest_collection_modifyitems(self, config: "Config", items: "List[nodes.Item]") -> None:
        """
        Collect and select the tests we want to run, and deselect the rest.
        """
        splits: int = config.option.splits
        group: int = config.option.group

        selected_tests, deselected_tests = self._split_tests(splits, group, items, self.cached_durations)

        items[:] = selected_tests
        config.hook.pytest_deselected(items=deselected_tests)

        self.writer.line(self.writer.markup(f"\n\n[pytest-split] Running group {group}/{splits}\n"))
        return None

    @staticmethod
    def _split_tests(
        splits: int,
        group: int,
        items: "List[nodes.Item]",
        stored_durations: dict,
    ) -> "Tuple[list, list]":
        """
        Split tests into groups by runtime.

        :param splits: How many groups we're splitting in.
        :param group: Which group this run represents.
        :param items: Test items passed down by Pytest.
        :param stored_durations: Our cached test runtimes.
        :return:
            Tuple of two lists.
            The first list represents the tests we want to run,
            while the other represents the tests we want to deselect.
        """
        # Filtering down durations to relevant ones ensures the avg isn't skewed by irrelevant data
        test_ids = [item.nodeid for item in items]
        durations = {k: v for k, v in stored_durations.items() if k in test_ids}

        if durations:
            avg_duration_per_test = sum(durations.values()) / len(durations)
        else:
            # If there are no durations, give every test the same arbitrary value
            avg_duration_per_test = 1

        tests_and_durations = {item: durations.get(item.nodeid, avg_duration_per_test) for item in items}
        time_per_group = sum(tests_and_durations.values()) / splits
        selected, deselected = [], []

        for _group in range(1, splits + 1):
            group_tests, group_runtime = [], 0

            for item in dict(tests_and_durations):
                if group_runtime > time_per_group:
                    break

                group_tests.append(item)
                group_runtime += tests_and_durations.pop(item)

            if _group == group:
                selected = group_tests
            else:
                deselected.extend(group_tests)

        return selected, deselected


class PytestSplitCachePlugin(Base):
    """
    The cache plugin writes durations to our durations file.
    """

    def pytest_sessionfinish(self) -> None:
        """
        Method is called by Pytest after the test-suite has run.
        https://github.com/pytest-dev/pytest/blob/main/src/_pytest/main.py#L308
        """
        terminal_reporter = self.config.pluginmanager.get_plugin("terminalreporter")
        test_durations = {}

        for test_reports in terminal_reporter.stats.values():
            for test_report in test_reports:
                if isinstance(test_report, TestReport):

                    # These ifs be removed after this is solved: # https://github.com/spulec/freezegun/issues/286
                    if test_report.duration < 0:
                        continue
                    if (
                        test_report.when in ("teardown", "setup")
                        and test_report.duration > STORE_DURATIONS_SETUP_AND_TEARDOWN_THRESHOLD
                    ):
                        # Ignore not legit teardown durations
                        continue

                    # Add test durations to map
                    if test_report.nodeid not in test_durations:
                        test_durations[test_report.nodeid] = 0
                    test_durations[test_report.nodeid] += test_report.duration

        # Update the full cached-durations object
        for k, v in test_durations.items():
            self.cached_durations[k] = v

        # Save durations
        with open(self.config.option.durations_path, "w") as f:
            json.dump(self.cached_durations, f)

        message = self.writer.markup(
            "\n\n[pytest-split] Stored test durations in {}".format(self.config.option.durations_path)
        )
        self.writer.line(message)
