# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Changed
- Introduce Ruff
- Fixed usage of [deprecated pytest API](https://docs.pytest.org/en/latest/deprecations.html#configuring-hook-specs-impls-using-markers)


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

[Unreleased]: https://github.com/jerry-git/pytest-split/compare/0.8.0...master
[0.8.0]: https://github.com/jerry-git/pytest-split/compare/0.7.0...0.8.0
[0.7.0]: https://github.com/jerry-git/pytest-split/compare/0.6.0...0.7.0
[0.6.0]: https://github.com/jerry-git/pytest-split/compare/0.5.0...0.6.0
[0.5.0]: https://github.com/jerry-git/pytest-split/compare/0.4.0...0.5.0
[0.4.0]: https://github.com/jerry-git/pytest-split/tree/0.4.0
