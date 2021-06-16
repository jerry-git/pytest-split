# Pytest-split

[![Test Workflow](https://github.com/jerry-git/pytest-split/actions/workflows/test.yml/badge.svg?branch=master
)](https://github.com/jerry-git/pytest-split/actions/workflows/test.yml?query=branch%3Amaster)
[![PyPI version](https://badge.fury.io/py/pytest-split.svg)](https://pypi.python.org/pypi/pytest-split/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/pytest-split.svg)](https://pypi.python.org/pypi/pytest-split/)

Pytest plugin which splits the test suite to equally sized "sub suites" based on test execution time.

## Motivation
* Splitting the test suite is a prerequisite for parallelization (who does not want faster CI builds?). It's valuable to have sub suites which execution time is around the same.
* [`pytest-test-groups`](https://pypi.org/project/pytest-test-groups/) is great but it does not take into account the execution time of sub suites which can lead to notably unbalanced execution times between the sub suites.
* [`pytest-xdist`](https://pypi.org/project/pytest-xdist/) is great but it's not suitable for all use cases.
For example, some test suites may be fragile considering the order in which the tests are executed.
This is of course a fundamental problem in the suite itself but sometimes it's not worth the effort to refactor, especially if the suite is huge (and smells a bit like legacy).
Additionally, `pytest-split` may be a better fit in some use cases considering distributed execution.

## Installation
```
pip install pytest-split
```

## Usage
First we have to store test durations from a complete test suite run.
This produces .test_durations file which should be stored in the repo in order to have it available during future test runs.
The file path is configurable via `--durations-path` CLI option.
```
pytest --store-durations
```

Then we can have as many splits as we want:
```
pytest --splits 3 --group 1
pytest --splits 3 --group 2
pytest --splits 3 --group 3
```

Time goes by, new tests are added and old ones are removed/renamed during development. No worries!
`pytest-split` assumes average test execution time (calculated based on the stored information) for every test which does not have duration information stored.
Thus, there's no need to store durations after changing the test suite.
However, when there are major changes in the suite compared to what's stored in .test_durations, it's recommended to update the duration information with `--store-durations` to ensure that the splitting is in balance.


[**Demo with GitHub Actions**](https://github.com/jerry-git/pytest-split-gh-actions-demo)
