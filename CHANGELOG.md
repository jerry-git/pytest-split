# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Changed
- `AlgorithmBase.__call__` now takes a single `durations: dict[Item, float]`
  argument instead of separate `items` and `durations` arguments. Custom
  algorithm subclasses must update their signature. Use the new public
  `pytest_split.algorithms.compute_durations(items, cached_durations)` helper to
  build the dict the same way the plugin does.
- Algorithms now own only group membership; the order of `selected` items in
  the returned `TestGroup`s is implementation-defined. The plugin rebuilds the
  chosen group's `selected` and `deselected` lists in pytest's collection
  order before the test session executes, so end-to-end behaviour is
  unchanged.
- `duration_based_chunks` now computes group membership from a canonical
  (nodeid-sorted) traversal, so splits are stable across pytest collection
  orders (e.g. when parametrising over a `set`/`frozenset`/`dict.keys()` whose
  iteration order is hash-randomised). Within-group execution order is
  unchanged: pytest still runs each group's tests in the order it collected
  them. Notebook cell node-ids that contain numeric suffixes
  (`nb.ipynb::cell_0..cell_10`) sort alphabetically (`cell_0, cell_1, cell_10,
  cell_11, cell_2, …`) for the membership pass; `ensure_ipynb_compatibility`
  still pulls all sibling cells into the same group, so user-visible behaviour
  is correct.

### Fixed
- Fix malformed bullet points rendering in GitHub Pages documentation

## [0.11.0] - 2026-02-03
### Added
- Support for pytest 9.x
- Support for Python 3.14

### Changed
- Migrated `poetry.dev-dependencies` to `poetry.group.dev.dependencies`

### Removed
- Support for Python 3.8 and 3.9 (end-of-life)

## [0.10.0] - 2024-10-16
### Added
- Support for Python 3.13.

## [0.9.0] - 2024-06-19
### Changed
- Cruft update to get up to date with the parent cookiecutter template

### Removed
- Support for Python 3.7

## [0.8.2] - 2024-01-29
### Added
- Support for pytest 8.x
- Python 3.12 to CI test matrix

## [0.8.1] - 2023-04-12
### Changed
- Introduce Ruff
- Fixed usage of [deprecated pytest API](https://docs.pytest.org/en/latest/deprecations.html#configuring-hook-specs-impls-using-markers)

### Added
- Python 3.11 to CI test matrix

## [0.8.0] - 2022-04-22
### Fixed
- The `least_duration` algorithm should now split deterministically regardless of starting test order.
  This should fix the main problem when running with test-randomization packages such as `pytest-randomly` or `pytest-random-order`
  See #52

## [0.7.0] - 2022-03-13
### Added
- Support for pytest 7.x, see https://github.com/jerry-git/pytest-split/pull/47

## [0.6.0] - 2022-01-10
### Added
- PR template
- Test against 3.10
- Compatibility with IPython Notebooks

## [0.5.0] - 2021-11-09
### Added
- Wolt cookiecutter + cruft setup, see https://github.com/jerry-git/pytest-split/pull/33

## [0.4.0] - 2021-11-09
### Changed
- Durations file content in prettier format, see https://github.com/jerry-git/pytest-split/pull/31

[Unreleased]: https://github.com/jerry-git/pytest-split/compare/0.11.0...master
[0.11.0]: https://github.com/jerry-git/pytest-split/compare/0.10.0...0.11.0
[0.10.0]: https://github.com/jerry-git/pytest-split/compare/0.9.0...0.10.0
[0.9.0]: https://github.com/jerry-git/pytest-split/compare/0.8.2...0.9.0
[0.8.2]: https://github.com/jerry-git/pytest-split/compare/0.8.1...0.8.2
[0.8.1]: https://github.com/jerry-git/pytest-split/compare/0.8.0...0.8.1
[0.8.0]: https://github.com/jerry-git/pytest-split/compare/0.7.0...0.8.0
[0.7.0]: https://github.com/jerry-git/pytest-split/compare/0.6.0...0.7.0
[0.6.0]: https://github.com/jerry-git/pytest-split/compare/0.5.0...0.6.0
[0.5.0]: https://github.com/jerry-git/pytest-split/compare/0.4.0...0.5.0
[0.4.0]: https://github.com/jerry-git/pytest-split/tree/0.4.0

