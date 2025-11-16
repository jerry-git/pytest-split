# pytest-split

[![PyPI](https://img.shields.io/pypi/v/pytest-split?style=flat-square)](https://pypi.python.org/pypi/pytest-split/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pytest-split?style=flat-square)](https://pypi.python.org/pypi/pytest-split/)
[![PyPI - License](https://img.shields.io/pypi/l/pytest-split?style=flat-square)](https://pypi.python.org/pypi/pytest-split/)
[![Coookiecutter - Wolt](https://img.shields.io/badge/cookiecutter-Wolt-00c2e8?style=flat-square&logo=cookiecutter&logoColor=D4AA00&link=https://github.com/woltapp/wolt-python-package-cookiecutter)](https://github.com/woltapp/wolt-python-package-cookiecutter)


---

**Documentation**: [https://jerry-git.github.io/pytest-split](https://jerry-git.github.io/pytest-split)

**Source Code**: [https://github.com/jerry-git/pytest-split](https://github.com/jerry-git/pytest-split)

**PyPI**: [https://pypi.org/project/pytest-split/](https://pypi.org/project/pytest-split/)

---

Pytest plugin which splits the test suite to equally sized "sub suites" based on test execution time.

## Motivation
* Splitting the test suite is a prerequisite for parallelization (who does not want faster CI builds?). It's valuable to have sub suites which execution time is around the same.
* [`pytest-test-groups`](https://pypi.org/project/pytest-test-groups/) is great but it does not take into account the execution time of sub suites which can lead to notably unbalanced execution times between the sub suites.
* [`pytest-xdist`](https://pypi.org/project/pytest-xdist/) is great but it's not suitable for all use cases.
For example, some test suites may be fragile considering the order in which the tests are executed.
This is of course a fundamental problem in the suite itself but sometimes it's not worth the effort to refactor, especially if the suite is huge (and smells a bit like legacy).
Additionally, `pytest-split` may be a better fit in some use cases considering distributed execution.

## Installation
```sh
pip install pytest-split
```

## Usage
First we have to store test durations from a complete test suite run.
This produces .test_durations file which should be stored in the repo in order to have it available during future test runs.
The file path is configurable via `--durations-path` CLI option.
```sh
pytest --store-durations
```

Then we can have as many splits as we want:
```sh
pytest --splits 3 --group 1
pytest --splits 3 --group 2
pytest --splits 3 --group 3
```

Time goes by, new tests are added and old ones are removed/renamed during development. No worries!
`pytest-split` assumes mean test execution time (calculated based on the stored information) for every test which does not have duration information stored.
Thus, there's no need to store durations after changing the test suite.
However, when there are major changes in the suite compared to what's stored in .test_durations, it's recommended to update the duration information with `--store-durations` to ensure that the splitting is in balance.

The splitting algorithm can be controlled with the `--splitting-algorithm` CLI option and defaults to `duration_based_chunks`. For more information about the different algorithms and their tradeoffs, please see the section below.

### CLI commands
#### slowest-tests
Lists the slowest tests based on the information stored in the test durations file. See `slowest-tests --help` for more
 information.

## Interactions with other pytest plugins
* [`pytest-random-order`](https://github.com/jbasko/pytest-random-order) and [`pytest-randomly`](https://github.com/pytest-dev/pytest-randomly):
   ⚠️ `pytest-split` running with the `duration_based_chunks` algorithm is **incompatible** with test-order-randomization plugins.
  Test selection in the groups happens after randomization, potentially causing some tests to be selected in several groups and others not at all.
  Instead, a global random seed needs to be computed before running the tests (for example using `$RANDOM` from the shell) and that single seed then needs to be used for all groups by setting the `--random-order-seed` option.

* [`nbval`](https://github.com/computationalmodelling/nbval): `pytest-split` could, in principle, break up a single IPython Notebook into different test groups. This most likely causes broken up pieces to fail (for the very least, package `import`s are usually done at Cell 1, and so, any broken up piece that doesn't contain Cell 1 will certainly fail). To avoid this, after splitting step is done, test groups are reorganized based on a simple algorithm illustrated in the following cartoon:

![image](https://user-images.githubusercontent.com/14086031/145830494-07afcaf0-5a0f-4817-b9ee-f84a459652a8.png)

where the letters (A to E) refer to individual IPython Notebooks, and the numbers refer to the corresponding cell number.

## Splitting algorithms
The plugin supports multiple algorithms to split tests into groups.
Each algorithm makes different tradeoffs, but generally `least_duration` should give more balanced groups.

| Algorithm      | Maintains Absolute Order | Maintains Relative Order | Split Quality | Works with random ordering |
|----------------|--------------------------|--------------------------|---------------|----------------------------|
| duration_based_chunks | ✅                | ✅                       | Good          | ❌                         |
| least_duration | ❌                       | ✅                       | Better        | ✅                         |

Explanation of the terms in the table:
* Absolute Order: whether each group contains all tests between first and last element in the same order as the original list of tests
* Relative Order: whether each test in each group has the same relative order to its neighbours in the group as in the original list of tests
* Works with random ordering: whether the algorithm works with test-shuffling tools such as [`pytest-randomly`](https://github.com/pytest-dev/pytest-randomly)

The `duration_based_chunks` algorithm aims to find optimal boundaries for the list of tests and every test group contains all tests between the start and end boundary.
The `least_duration` algorithm walks the list of tests and assigns each test to the group with the smallest current duration.


[**Demo with GitHub Actions**](https://github.com/jerry-git/pytest-split-gh-actions-demo)


## Development

* Clone this repository
* Requirements:
  * [Poetry](https://python-poetry.org/)
  * Python 3.8+
* Create a virtual environment and install the dependencies

```sh
poetry install
```

* Activate the virtual environment

```sh
poetry shell
```

### Testing

```sh
pytest
```

### Documentation

The documentation is automatically generated from the content of the [docs directory](https://github.com/jerry-git/pytest-split/tree/master/docs) and from the docstrings
 of the public signatures of the source code. The documentation is updated and published as a [Github Pages page](https://pages.github.com/) automatically as part each release.

### Releasing

Trigger the [Draft release workflow](https://github.com/jerry-git/pytest-split/actions/workflows/draft_release.yml)
(press _Run workflow_). This will update the changelog & version and create a GitHub release which is in _Draft_ state.

Find the draft release from the
[GitHub releases](https://github.com/jerry-git/pytest-split/releases) and publish it. When
 a release is published, it'll trigger [release](https://github.com/jerry-git/pytest-split/blob/master/.github/workflows/release.yml) workflow which creates PyPI
 release and deploys updated documentation.

### Pre-commit

Pre-commit hooks run all the auto-formatting (`ruff format`), linters (e.g. `ruff` and `mypy`), and other quality
 checks to make sure the changeset is in good shape before a commit/push happens.

You can install the hooks with (runs for each commit):

```sh
pre-commit install
```

Or if you want them to run only for each push:

```sh
pre-commit install -t pre-push
```

Or if you want e.g. want to run all checks manually for all files:

```sh
pre-commit run --all-files
```

---

This project was generated using the [wolt-python-package-cookiecutter](https://github.com/woltapp/wolt-python-package-cookiecutter) template.
