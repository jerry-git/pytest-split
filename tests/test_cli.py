import argparse
import json
import sys
from io import StringIO
from unittest.mock import patch

import pytest
from pytest_split import cli


@pytest.fixture()
def durations_file(tmpdir):
    durations_path = str(tmpdir.join(".durations"))
    durations = {f"test_{i}": float(i) for i in range(1, 11)}
    with open(durations_path, "w") as f:
        json.dump(durations, f)
    with open(durations_path) as f:
        yield f


def test_slowest_tests(durations_file):
    with patch(
        "pytest_split.cli.argparse.ArgumentParser", autospec=True
    ) as arg_parser, patch("sys.stdout", new_callable=StringIO):
        arg_parser().parse_args.return_value = argparse.Namespace(
            durations_path=durations_file, count=3
        )
        cli.list_slowest_tests()

        output = sys.stdout.getvalue()  # type: ignore[attr-defined]
        assert output == ("10.00 test_10\n9.00 test_9\n8.00 test_8\n")


@pytest.fixture()
def multiple_durations_files(tmpdir):
    files_paths = []
    for combine_i in range(1, 5):
        tmpdir.mkdir(f"{combine_i}_folder")
        durations_path = str(tmpdir.join(f"{combine_i}_folder").join(".durations"))
        durations = {f"test_{combine_i}_{i}": float(i) for i in range(1, 11)}
        with open(durations_path, "w") as f:
            json.dump(durations, f)
        files_paths.append(durations_path)

    return files_paths


def test_combine_tests(durations_file, multiple_durations_files, tmpdir):
    durations_path = durations_file.name
    new_durations_files = len(multiple_durations_files)
    new_durations = new_durations_files * 10

    with patch(
        "pytest_split.cli.argparse.ArgumentParser", autospec=True
    ) as arg_parser, patch("sys.stdout", new_callable=StringIO):
        arg_parser().parse_args.return_value = argparse.Namespace(
            durations_path=durations_path,
            durations_pattern="*/.durations",
            root_folder=tmpdir,
            keep_original=True,
        )
        cli.run_combine_tests()

        output = sys.stdout.getvalue()  # type: ignore[attr-defined]
        assert output == (
            f"{new_durations_files} files combined, with a total of {new_durations+10} entries\n"
        )

    # Test not keeping original
    with patch(
        "pytest_split.cli.argparse.ArgumentParser", autospec=True
    ) as arg_parser, patch("sys.stdout", new_callable=StringIO):
        arg_parser().parse_args.return_value = argparse.Namespace(
            durations_path=durations_path,
            durations_pattern="*/.durations",
            root_folder=tmpdir,
            keep_original=False,
        )
        cli.run_combine_tests()

        output = sys.stdout.getvalue()  # type: ignore[attr-defined]
        assert output == (
            f"{new_durations_files} files combined, with a total of {new_durations} entries\n"
        )
