import argparse
import json
import sys
from io import StringIO
from unittest.mock import patch

import pytest

from pytest_split import cli


@pytest.fixture
def durations_file(tmpdir):
    durations_path = str(tmpdir.join(".durations"))
    durations = {f"test_{i}": float(i) for i in range(1, 11)}
    with open(durations_path, "w") as f:
        json.dump(durations, f)
    with open(durations_path, "r") as f:
        yield f


def test_slowest_tests(durations_file):
    with patch("pytest_split.cli.argparse.ArgumentParser", autospec=True) as arg_parser, patch(
        "sys.stdout", new_callable=StringIO
    ):
        arg_parser().parse_args.return_value = argparse.Namespace(durations_path=durations_file, count=3)
        cli.list_slowest_tests()

        output = sys.stdout.getvalue()
        assert output == "10.00 test_10\n" "9.00 test_9\n" "8.00 test_8\n"
