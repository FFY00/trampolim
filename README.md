# trampolim

[![test](https://github.com/FFY00/trampolim/actions/workflows/test.yml/badge.svg)](https://github.com/FFY00/trampolim/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/FFY00/trampolim/branch/main/graph/badge.svg?token=QAfQGa1bld)](https://codecov.io/gh/FFY00/trampolim)
[![check](https://github.com/FFY00/trampolim/actions/workflows/check.yml/badge.svg)](https://github.com/FFY00/trampolim/actions/workflows/check.yml)

A modern Python build backend.

### Features

- Task system, allowing to run arbitrary Python code during the build process (**Planned**)
- Easy to use CLI -- build, publish, check for errors and recommended practices (**Planned**)
- Automatic version detection from git repos and archives

### Usage

`trampolim` implements [PEP 621](https://www.python.org/dev/peps/pep-0621).
Your `pyproject.toml` should look something like this:

```toml
[build-system]
build-backend = 'trampolim'
requires = ['trampolim']

[project]
name = 'sample_project'
version = '1.0.0'
description = 'A sample project'
readme = 'README.md'
requires-python = '>=3.7'
license = { file = 'LICENSE' }
authors = [
  { name = 'Filipe Laíns', email = 'lains@riseup.net' },
]
maintainers = [
  { name = 'Filipe Laíns', email = 'lains@riseup.net' },
]
classifiers = [
  'Development Status :: 4 - Beta',
  'Programming Language :: Python'
]

dependencies = [
  'dependency',
  'some-backport ; python_version < "3.8"',
]

[project.optional-dependencies]
test = [
  'pytest',
  'pytest-cov',
]

[project.scripts]
sample_entrypoint = 'sample_project:entrypoint_function'

[project.urls]
homepage = 'my-sample-project-website.example.com'
documentation = 'github.com/some-user/sample-project'
repository = 'github.com/some-user/sample-project'
changelog = 'github.com/some-user/sample-project/blob/master/CHANGELOG.rst'
```
