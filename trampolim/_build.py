# SPDX-License-Identifier: MIT

import contextlib
import dataclasses
import email
import functools
import glob
import gzip
import importlib.util
import io
import itertools
import os
import os.path
import shutil
import subprocess
import sys
import tarfile
import typing
import warnings

from typing import IO, ContextManager, Iterable, Iterator, List, Optional, Sequence, Set, Union

import packaging.markers
import packaging.requirements
import packaging.version
import pep621
import toml

import trampolim._metadata
import trampolim._tasks
import trampolim.types


if sys.version_info < (3, 8):
    from backports.cached_property import cached_property
else:
    from functools import cached_property


Path = Union[str, os.PathLike]


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
def cd(path: str) -> Iterator[None]:
    cwd = os.getcwd()
    os.chdir(path)

    try:
        yield
    finally:
        os.chdir(cwd)


def ensure_empty_dir(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path)


def copy_to_dir(files: Iterable[str], out: str) -> None:
    for file in files:
        dirpath = os.path.dirname(file)
        if dirpath:
            destdirpath = os.path.join(out, dirpath)
            os.makedirs(destdirpath, exist_ok=True)
            shutil.copystat(dirpath, destdirpath)
        shutil.copy2(
            file,
            os.path.join(out, file),
            follow_symlinks=False,
        )


class Project():
    _VALID_DYNAMIC = [
        'version',
    ]

    def __init__(self, _toml: Optional[str] = None) -> None:
        if _toml is not None:
            self._pyproject = toml.loads(_toml)
        else:
            with open('pyproject.toml') as f:
                self._pyproject = toml.load(f)

        self._meta = pep621.StandardMetadata.from_pyproject(self._pyproject)
        self._trampolim_meta = trampolim._metadata.TrampolimMetadata.from_pyproject(self._pyproject)

        for field in self._meta.dynamic:
            if field not in self._VALID_DYNAMIC:
                raise ConfigurationError(f'Unsupported field `{field}` in `project.dynamic`')

        self.version  # calculate version

        self._path = os.getcwd()
        self._extra_binary_source: Set[str] = set()

        # warn users about test/tests modules -- they probably don't want them installed!
        for module in ('test', 'tests'):
            if module in self.root_modules:
                warnings.warn(
                    f'Top-level module `{module}` selected, are you sure you want to install it??',
                    TrampolimWarning,
                )

        # copy distribution source to working directory
        self._dist_srcpath: str = os.path.abspath(os.path.join('.trampolim', 'dist-source'))
        ensure_empty_dir(self._dist_srcpath)
        copy_to_dir(
            itertools.chain(self.distribution_source, self.build_system_source),
            self._dist_srcpath,
        )
        # copy binary source to working directory
        self._bin_srcpath: str = os.path.abspath(os.path.join('.trampolim', 'bin-source'))
        ensure_empty_dir(self._bin_srcpath)
        copy_to_dir(
            itertools.chain(self.binary_source, self.build_system_source),
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
                self._extra_binary_source |= set(session.extra_source)
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
    def build_system_source(self) -> Iterable[str]:
        return iter(filter(None, [
            'pyproject.toml',
            '.trampolim.py' if os.path.isfile('.trampolim.py') else None,
            self._meta.license.file if self._meta.license else None,
            self._meta.readme.file if self._meta.readme else None,
        ]))

    @property
    def distribution_source(self) -> Iterable[str]:
        '''Project source -- for source distributions.'''
        return self.modules_source | self.config_source_include

    @property
    def binary_source(self) -> Iterable[str]:
        '''Python package source -- for binary distributions.'''
        return self.modules_source | self._extra_binary_source

    @property
    def root_modules(self) -> Sequence[str]:
        '''Project top-level modules.

        By default will look for the normalized name of the project name
        replacing `-` with `_`.
        '''
        if self._trampolim_meta.top_level_modules:
            return self._trampolim_meta.top_level_modules

        name = self.name.replace('-', '_')
        files = os.listdir()
        if f'{name}.py' in files:  # file module
            return [f'{name}.py']
        if name in files:  # dir module
            return [name]
        raise TrampolimError(f'Could not find the top-level module(s) (looking for `{name}`)')

    @property
    def modules_source(self) -> Set[str]:
        '''Full source for the modules in root_modules.'''
        source = set()
        # TODO: ignore files not escaped as specified in PEP 427
        for module in self.root_modules:
            if module.endswith('.py'):  # file
                source.add(module)
            else:  # dir
                source |= {
                    path for path in glob.glob(os.path.join(module, '**'), recursive=True)
                    if os.path.isfile(path) and not path.endswith('.pyc')
                }
        return source

    @property
    def config_source_include(self) -> Set[str]:
        '''Extra source include paths specified in the config.'''
        return {
            os.path.sep.join(path.split('/'))
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
            assert isinstance(self._meta.version, packaging.version.Version)
            return self._meta.version

        if 'version' not in self._meta.dynamic:
            raise ConfigurationError(
                'Missing required field `project.version` (if you want to infer the project version '
                'automatically, `version` needs to be added to the `project.dynamic` list field)'
            )

        if 'TRAMPOLIM_VCS_VERSION' in os.environ:
            return packaging.version.Version(os.environ['TRAMPOLIM_VCS_VERSION'])

        # from git archive
        # http://git-scm.com/book/en/v2/Customizing-Git-Git-Attributes
        # https://git-scm.com/docs/pretty-formats
        if os.path.isfile('.git-archive.txt'):
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
                return packaging.version.Version(f'0.dev0+{data["commit"]}')

        # from git repo
        try:
            tag, r, commit = subprocess.check_output([
                'git', 'describe', '--tags'
            ]).decode().strip(' v').split('-')
            return packaging.version.Version(f'{tag}.{r}+{commit}')
        except (FileNotFoundError, subprocess.CalledProcessError, TypeError):
            pass

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


class SdistBuilder():
    '''Simple sdist builder.

    Will only include by default the files relevant for source code distribution
    and the required files to be able to build binary distributions.
    '''
    def __init__(self, project: Project) -> None:
        self._project = project

    @property
    def name(self) -> str:
        return f'{self._project.name}-{self._project.version}'

    @property
    def file(self) -> str:
        return f'{self.name}.tar.gz'

    def build(self, path: Path) -> None:
        # reproducibility
        source_date_epoch = os.environ.get('SOURCE_DATE_EPOCH')
        mtime = int(source_date_epoch) if source_date_epoch else None

        # open files
        file = typing.cast(
            IO[bytes],
            gzip.GzipFile(
                os.path.join(path, self.file),
                mode='wb',
                mtime=mtime,
            ),
        )
        tar = tarfile.TarFile(
            str(path),
            mode='w',
            fileobj=file,
            format=tarfile.PAX_FORMAT,  # changed in 3.8 to GNU
        )

        with self._project.cd_dist_source():
            # add pyproject.toml
            tar.add('pyproject.toml', f'{self.name}/pyproject.toml')

            # add .trampolim.py
            try:
                tar.add('.trampolim.py', f'{self.name}/.trampolim.py')
            except FileNotFoundError:  # pragma: no cover
                pass

            # add source
            for source_path in self._project.distribution_source:
                tar.add(source_path, f'{self.name}/{source_path}')

            # add license
            license_ = self._project._meta.license
            if license_:
                if license_.file:
                    tar.add(license_.file, f'{self.name}/{license_.file}')
                elif license_.text:
                    license_raw = license_.text.encode()
                    info = tarfile.TarInfo(f'{self.name}/LICENSE')
                    info.size = len(license_raw)
                    with io.BytesIO(license_raw) as data:
                        tar.addfile(info, data)

            # add readme
            readme = self._project._meta.readme
            if readme:
                tar.add(readme.file, f'{self.name}/{readme.file}')

        # PKG-INFO
        pkginfo = bytes(self._project._meta.as_rfc822())
        info = tarfile.TarInfo(f'{self.name}/PKG-INFO')
        info.size = len(pkginfo)
        with io.BytesIO(pkginfo) as data:
            tar.addfile(info, data)

        # cleanup
        tar.close()
        file.close()
