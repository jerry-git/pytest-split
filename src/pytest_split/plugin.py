import json
import os
from typing import TYPE_CHECKING
from warnings import warn

from _pytest.config import create_terminal_writer, hookimpl

if TYPE_CHECKING:
    from typing import List, Tuple

    from _pytest import nodes
    from _pytest.config import Config
    from _pytest.config.argparsing import Parser

# Ugly hacks for freezegun compatibility:
# https://github.com/spulec/freezegun/issues/286
STORE_DURATIONS_SETUP_AND_TEARDOWN_THRESHOLD = 60 * 10  # seconds
CACHE_PATH = ".pytest_cache/v/cache/pytest_split"


def pytest_addoption(parser: "Parser") -> None:
    """
    Declare plugin options.
    """
    group = parser.getgroup(
        "Split tests into groups which execution time is about the same. "
        "Run first the whole suite with --store-durations to save information "
        "about test execution times"
    )
    group.addoption(
        "--store-durations",
        dest="store_durations",
        action="store_true",
        help="Store durations into '--durations-path'",
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


def pytest_configure(config: "Config") -> None:
    """
    Enable the plugin if appropriate arguments are passed.
    """
    if config.option.splits and not config.option.group:
        warn(
            "Both the `splits` and `group` arguments are required for pytest-split "
            "to run. Remove the `splits` argument or add a `groups` argument."
        )
    elif config.option.group and not config.option.splits:
        warn(
            "Both the `splits` and `group` arguments are required for pytest-split "
            "to run. Remove the `groups` argument or add a `splits` argument."
        )
    elif config.option.splits and config.option.group:
        config.pluginmanager.register(PytestSplitPlugin(config), "pytestsplitplugin")

    if config.option.store_durations:
        config.pluginmanager.register(PytestSplitCachePlugin(config), "pytestsplitcacheplugin")


class Base:
    def __init__(self, config: "Config") -> None:
        """
        Load cache and configure plugin.
        """
        self.config = config
        self.writer = create_terminal_writer(self.config)

        try:
            with open(config.option.durations_path, "r") as f:
                self.cached_durations = json.loads(f.read())
        except FileNotFoundError:
            self.cached_durations = {}


class PytestSplitPlugin(Base):
    def __init__(self, config: "Config"):
        super().__init__(config)
        if not self.cached_durations:
            message = self.writer.markup(
                "\nNo test durations found. Pytest-split will "
                "split tests evenly when no durations are found. "
                "\nYou can expect better results in consequent runs, "
                "when test timings have been documented.\n"
            )
            self.writer.line(message)

    @hookimpl(tryfirst=True)
    def pytest_collection_modifyitems(self, config: "Config", items: "List[nodes.Item]") -> None:
        """
        Instruct Pytest to run the tests we've selected.

        This method is called by Pytest right after Pytest internals finishes
        collecting tests.

        See https://github.com/pytest-dev/pytest/blob/main/src/_pytest/main.py#L670.
        """
        splits: int = config.option.splits
        group: int = config.option.group

        selected_tests, deselected_tests = self._split_tests(splits, group, items, self.cached_durations)

        items[:] = selected_tests
        config.hook.pytest_deselected(items=deselected_tests)

        self.writer.line(self.writer.markup(f"\n\nRunning group {group}/{splits}\n"))
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
    def pytest_sessionfinish(self) -> None:
        """
        Write test runtimes to cache.

        Method is called by Pytest after the test-suite has run.
        https://github.com/pytest-dev/pytest/blob/main/src/_pytest/main.py#L308
        """
        terminal_reporter = self.config.pluginmanager.get_plugin("terminalreporter")
        test_durations = {}

        for test_reports in terminal_reporter.stats.values():
            for test_report in test_reports:
                if hasattr(test_report, "duration"):
                    # These ifs be removed after this is solved:
                    # https://github.com/spulec/freezegun/issues/286
                    if test_report.duration < 0:
                        continue
                    if (
                        getattr(test_report, "when", "") in ("teardown", "setup")
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

        message = self.writer.markup("\n\nStored test durations in {}\n".format(self.config.option.durations_path))
        self.writer.line(message)
