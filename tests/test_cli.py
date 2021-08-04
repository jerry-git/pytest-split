import argparse
import json
from unittest.mock import patch

import pytest

from pytest_split import cli


@pytest.fixture
def durations_file(tmpdir):
    durations_path = str(tmpdir.join(".durations"))
    durations = {"test_1": 1.0, "test_2": 2.0, "test_3": 3.0}
    with open(durations_path, "w") as f:
        json.dump(durations, f)
    with open(durations_path, "r") as f:
        yield f


def test_slowest_tests(durations_file):
    # just a semi dummy test to check that it doesn't blow up
    with patch("pytest_split.cli.argparse.ArgumentParser") as arg_parser:
        arg_parser().parse_args.return_value = argparse.Namespace(durations_path=durations_file, count=5)

        cli.list_slowest_tests()
