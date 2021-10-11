# SPDX-License-Identifier: MIT

import contextlib
import dataclasses
import email
import functools
import importlib.util
import itertools
import os
import os.path
import pathlib
import shutil
import subprocess
import sys
import warnings

from typing import ContextManager, Iterable, Iterator, List, Mapping, NamedTuple, Optional, Sequence, Set, Union

import packaging.markers
import packaging.requirements
import packaging.version
import pep621
import tomli

import trampolim._metadata
import trampolim._tasks
import trampolim.types


if sys.version_info < (3, 8):
    from backports.cached_property import cached_property
else:
    from functools import cached_property


Path = Union[str, os.PathLike]


class PythonSource(NamedTuple):
    origin: pathlib.Path
    source: Set[pathlib.Path]


class TrampolimError(Exception):
    '''Backend error.'''


class ConfigurationError(TrampolimError):
    '''Error in the backend configuration.'''
    def __init__(self, msg: str, *, key: Optional[str] = None):
        super().__init__(msg)
        self._key = key

    @property
    def key(self) -> Optional[str]:  # pragma: no cover
        return self._key


class TrampolimWarning(Warning):
    '''Backend warning.'''


def load_file_module(name: str, path: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec
    if not spec.loader:  # pragma: no cover
        raise ImportError(f'Unable to import `{path}`: no loader')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    return module


@contextlib.contextmanager
def cd(path: Path) -> Iterator[None]:
    cwd = os.getcwd()
    os.chdir(os.fspath(path))

    try:
        yield
    finally:
        os.chdir(cwd)


def ensure_empty_dir(path: pathlib.Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(exist_ok=True, parents=True)


def copy_to_dir(files: Iterable[pathlib.Path], out: pathlib.Path) -> None:
    for file in files:
        if os.path.dirname(file):
            destdirpath = out / file.parent
            destdirpath.mkdir(exist_ok=True, parents=True)
            shutil.copystat(file.parent, destdirpath)
        shutil.copy2(
            file,
            out / file,
            follow_symlinks=False,
        )


class Project():
    _VALID_DYNAMIC = [
        'version',
    ]

    def __init__(self, _toml: Optional[str] = None) -> None:
        if _toml is not None:
            self._pyproject = tomli.loads(_toml)
        else:
            with open('pyproject.toml', 'rb') as f:
                self._pyproject = tomli.load(f)

        self._meta = pep621.StandardMetadata.from_pyproject(self._pyproject)
        self._trampolim_meta = trampolim._metadata.TrampolimMetadata.from_pyproject(self._pyproject)

        if self._trampolim_meta.module_location:
            try:
                pathlib.Path(self._trampolim_meta.module_location).relative_to(os.curdir)
            except ValueError:
                raise ConfigurationError(
                    'Location in `tool.trampolim.module-location` is not relative '
                    f'to the project source: {self._trampolim_meta.module_location}'
                ) from None

        for field in self._meta.dynamic:
            if field not in self._VALID_DYNAMIC:
                raise ConfigurationError(f'Unsupported field `{field}` in `project.dynamic`')

        self.version  # calculate version

        self._path = os.getcwd()
        self._extra_binary_source: Set[pathlib.Path] = set()

        # warn users about test/tests modules -- they probably don't want them installed!
        for module in ('test', 'tests'):
            if module in self.root_modules:
                warnings.warn(
                    f'Top-level module `{module}` selected, are you sure you want to install it??',
                    TrampolimWarning,
                )

        working_dir = pathlib.Path('.trampolim').absolute()
        # copy distribution source to working directory
        self._dist_srcpath: pathlib.Path = working_dir / 'dist-source'
        ensure_empty_dir(self._dist_srcpath)
        copy_to_dir(
            itertools.chain(self.distribution_source, self.build_system_source),
            self._dist_srcpath,
        )
        # copy binary source to working directory
        self._bin_srcpath: pathlib.Path = working_dir / 'bin-source'
        ensure_empty_dir(self._bin_srcpath)
        copy_to_dir(
            itertools.chain(self.binary_source.values(), self.build_system_source),
            self._bin_srcpath,
        )

        # collect tasks
        if os.path.isfile('.trampolim.py'):
            config = load_file_module('trampolim_config', '.trampolim.py')
            self._tasks = [
                getattr(config, attr)
                for attr in dir(config)
                if not attr.startswith('_') and isinstance(
                    getattr(config, attr), trampolim._tasks.Task
                )
            ]
        else:
            self._tasks = []

    @functools.lru_cache(maxsize=None)
    def run_tasks(self) -> None:
        '''Runs the project build tasks.

        If the ``SOURCE_DATE_EPOCH`` environment variable is present, extra
        sources files added by tasks will have their atime and mtime set to it.
        '''
        with self.cd_binary_source():
            for task in self._tasks:
                print(f'> Running `{task.name}`')
                session = trampolim._tasks.Session(self)
                task.run(session)
                self._extra_binary_source |= {
                    pathlib.Path(*path.split('/'))
                    for path in session.extra_source
                }
                # TODO: print summary

        # set the extra source atime and mtime
        source_date_epoch = os.environ.get('SOURCE_DATE_EPOCH')
        if source_date_epoch:
            timestamp = int(source_date_epoch)
            with self.cd_binary_source():
                for file in self._extra_binary_source:
                    os.utime(file, times=(timestamp, timestamp))

    def cd_dist_source(self) -> ContextManager[None]:
        return cd(self._dist_srcpath)

    def cd_binary_source(self) -> ContextManager[None]:
        return cd(self._bin_srcpath)

    @property
    def name(self) -> str:
        assert isinstance(self._meta.name, str)
        return self._meta.name

    @property
    def normalized_name(self) -> str:
        return self.name.replace('-', '_')

    @property
    def build_system_source(self) -> Iterable[pathlib.Path]:
        return map(pathlib.Path, filter(None, [
            'pyproject.toml',
            '.trampolim.py' if os.path.isfile('.trampolim.py') else None,
            self._meta.license.file if self._meta.license else None,
            self._meta.readme.file if self._meta.readme else None,
        ]))

    @property
    def distribution_source(self) -> Iterable[pathlib.Path]:
        '''Project source, excluding modules -- for source distributions.'''
        return (
            set(self.build_system_source)
            | self.config_source_include
            | self.python_source.source
        )

    @property
    def binary_source(self) -> Mapping[pathlib.Path, pathlib.Path]:
        '''Python package source, excluding modules -- for binary distributions.'''
        source = {
            path: path
            for path in self._extra_binary_source
        }
        source.update({
            path.relative_to(self.python_source.origin): path
            for path in self.python_source.source
        })
        return source

    @property
    def modules_location(self) -> pathlib.Path:
        return pathlib.Path(
            self._trampolim_meta.module_location or os.path.curdir
        ).relative_to(os.path.curdir)

    @property
    def root_modules(self) -> Sequence[str]:
        '''Project top-level modules.

        By default will look for the normalized name of the project name
        replacing `-` with `_`.
        '''
        if self._trampolim_meta.top_level_modules:
            return self._trampolim_meta.top_level_modules

        name = self.name.replace('-', '_')
        files = os.listdir(self._trampolim_meta.module_location or os.path.curdir)
        if f'{name}.py' in files:  # file module
            return [f'{name}.py']
        if name in files:  # dir module
            return [name]
        raise TrampolimError(f'Could not find the top-level module(s) (looking for `{name}`)')

    @property
    def python_source(self) -> PythonSource:
        '''Full source for the modules in root_modules.'''
        source = set()
        # TODO: ignore files not escaped as specified in PEP 427
        for module in self.root_modules:
            if module.endswith('.py'):  # file
                source.add(self.modules_location / module)
            else:  # dir
                source |= {
                    path
                    for directory in self.modules_location.joinpath(module).rglob('**')
                    for path in directory.iterdir()
                    if path.is_file() and path.suffix != '.pyc'
                }
        return PythonSource(self.modules_location, source)

    @property
    def config_source_include(self) -> Set[pathlib.Path]:
        '''Extra source include paths specified in the config.'''
        return {
            pathlib.Path(*path.split('/'))
            for path in self._trampolim_meta.source_include
        }

    @property
    def meta(self) -> trampolim.types.FrozenMetadata:
        '''Project metadata.'''
        return trampolim.types.FrozenMetadata(
            **dataclasses.asdict(self._meta),
            **dataclasses.asdict(self._trampolim_meta),
        )  # type: ignore[call-arg]

    @cached_property
    def version(self) -> packaging.version.Version:  # noqa: C901
        '''Project version.'''

        if self._meta.version:
            # static metadata
            assert isinstance(self._meta.version, packaging.version.Version)
            return self._meta.version

        version_file = pathlib.Path('.trampolim', 'version')
        if version_file.is_file():
            if 'version' in self._meta.dynamic:
                # XXX: This should probably be done automatically by the pep621 module.
                self._meta.dynamic.remove('version')
            self._meta.version = packaging.version.Version(version_file.read_text())
            assert isinstance(self._meta.version, packaging.version.Version)
            return self._meta.version

        if 'version' not in self._meta.dynamic:
            raise ConfigurationError(
                'Missing required field `project.version` (if you want to infer the project version '
                'automatically, `version` needs to be added to the `project.dynamic` list field)'
            )

        if 'TRAMPOLIM_VCS_VERSION' in os.environ:
            # manual overwrite
            self._meta.version = packaging.version.Version(os.environ['TRAMPOLIM_VCS_VERSION'])
        elif os.path.isfile('.git-archive.txt'):
            # from git archive
            # http://git-scm.com/book/en/v2/Customizing-Git-Git-Attributes
            # https://git-scm.com/docs/pretty-formats
            with open('.git-archive.txt') as f:
                data = email.message_from_file(f)
            if 'ref-names' in data:
                for ref in data['ref-names'].split(', '):
                    try:
                        name, value = ref.split(': ', maxsplit=1)
                    except ValueError:
                        continue
                    if name == 'tag' and '$' not in value:
                        assert isinstance(value, str)
                        return packaging.version.Version(value.strip(' v'))
            if 'commit' in data and '$' not in data['commit']:
                assert isinstance(data['commit'], str)
                self._meta.version = packaging.version.Version(f'0.dev0+{data["commit"]}')
        else:
            # from git repo
            try:
                tag, r, commit = subprocess.check_output([
                    'git', 'describe', '--tags', '--long'
                ]).decode().strip(' v').split('-')
                self._meta.version = packaging.version.Version(
                    f'{tag}' if r == '0' else f'{tag}.{r}+{commit}'
                )
            except (FileNotFoundError, subprocess.CalledProcessError, TypeError):
                pass

        if self._meta.version:
            if 'version' in self._meta.dynamic:
                # XXX: This should probably be done automatically by the pep621 module.
                self._meta.dynamic.remove('version')  # we set the version, so it is no longer dynamic
            assert isinstance(self._meta.version, packaging.version.Version)
            return self._meta.version

        raise TrampolimError(
            'Could not find the project version from VCS (you can set the '
            'TRAMPOLIM_VCS_VERSION environment variable to manually override the version)'
        )

    @property
    def python_tags(self) -> List[str]:
        return ['py3']

    @property
    def python_tag(self) -> str:
        return '.'.join(self.python_tags)

    @property
    def abi_tag(self) -> str:
        return 'none'

    @property
    def platform_tag(self) -> str:
        return 'any'
