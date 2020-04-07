import json
import os
from collections import defaultdict, OrderedDict

from _pytest.config import create_terminal_writer

# Ugly hacks for freezegun compatibility: https://github.com/spulec/freezegun/issues/286
STORE_DURATIONS_SETUP_AND_TEARDOWN_THRESHOLD = 60 * 10  # seconds


def pytest_addoption(parser):
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


def pytest_collection_modifyitems(session, config, items):
    splits = config.option.splits
    group = config.option.group
    store_durations = config.option.store_durations
    durations_report_path = config.option.durations_path

    if any((splits, group)):
        if not all((splits, group)):
            return
        if not os.path.isfile(durations_report_path):
            return
        if store_durations:
            # Don't split if we are storing durations
            return
    total_tests_count = len(items)
    if splits and group:
        with open(durations_report_path) as f:
            stored_durations = OrderedDict(json.load(f))

        start_idx, end_idx = _calculate_suite_start_and_end_idx(
            splits, group, items, stored_durations
        )
        items[:] = items[start_idx:end_idx]

        terminal_reporter = config.pluginmanager.get_plugin("terminalreporter")
        terminal_writer = create_terminal_writer(config)
        message = terminal_writer.markup(
            " Running group {}/{} ({}/{} tests)\n".format(
                group, splits, len(items), total_tests_count
            )
        )
        terminal_reporter.write(message)


def pytest_sessionfinish(session, exitstatus):
    if session.config.option.store_durations:
        report_path = session.config.option.durations_path
        terminal_reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        durations = defaultdict(float)
        for test_reports in terminal_reporter.stats.values():
            for test_report in test_reports:
                if hasattr(test_report, "duration"):
                    stage = getattr(test_report, "when", "")
                    duration = test_report.duration
                    # These ifs be removed after this is solved: https://github.com/spulec/freezegun/issues/286
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


def _calculate_suite_start_and_end_idx(splits, group, items, stored_durations):
    item_node_ids = [item.nodeid for item in items]
    stored_durations = {k: v for k, v in stored_durations.items() if k in item_node_ids}
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
