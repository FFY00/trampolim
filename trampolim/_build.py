# SPDX-License-Identifier: MIT

import email
import glob
import gzip
import io
import os
import os.path
import re
import subprocess
import sys
import tarfile
import typing
import warnings

from typing import IO, Any, List, Optional, Sequence, Type, Union

import toml


if sys.version_info < (3, 8):
    from backports.cached_property import cached_property
else:
    from functools import cached_property


Path = Union[str, os.PathLike]


class TrampolimError(Exception):
    '''Backend error.'''


class ConfigurationError(TrampolimError):
    '''Error in the backend configuration.'''


class TrampolimWarning(Warning):
    '''Backend warning.'''


class Project():
    def __init__(self, _toml: Optional[str] = None) -> None:
        if _toml is not None:
            self._pyproject = toml.loads(_toml)
        else:
            with open('pyproject.toml') as f:
                self._pyproject = toml.load(f)

        if 'project' not in self._pyproject:
            raise ConfigurationError('Missing section `project` in pyproject.toml')

        self._project = self._pyproject['project']

        self._validate()

        self.version  # calculate version

        # warn users about test/tests modules -- they probably don't want them installed!
        for module in ('test', 'tests'):
            if module in self.root_modules:
                warnings.warn(
                    f'Top-level module `{module}` selected, are you sure you want to install it??',
                    TrampolimWarning,
                )

    def _validate_type(self, key: str, type: Type[Any]) -> None:
        '''Validate a key type in the project table.

        Throws KeyError if the key is not found.
        '''
        value = self._project
        for part in key.split('.'):
            value = value[part]
        if not isinstance(value, type):
            raise ConfigurationError(
                f'Field `project.{key}` has an invalid type, '
                f'expecting string (got `{type(value)}`)'
            )

    def _validate(self) -> None:
        '''Validate the project table.'''
        for field in ('name', 'license'):
            if field not in self._project:
                raise ConfigurationError(f'Field `project.{field}` missing pyproject.toml')

        # name
        self._validate_type('name', str)

        # version
        if 'version' in self._project:
            self._validate_type('version', str)

        # license
        if 'file' not in self._project['license'] and 'text' not in self._project['license']:
            raise ConfigurationError(
                'Invalid `project.license` value in pyproject.toml, '
                f'expecting either `file` or `text` (got `{self._project["license"]}`)'
            )
        for field in ('file', 'text'):
            try:
                self._validate_type('.'.join(['license', field]), str)
            except KeyError:
                continue
        if self.license_file and not os.path.isfile(self.license_file):
            raise ConfigurationError(f'License file not found (`{self.license_file}`)')

    @property
    def source(self) -> List[str]:
        '''Project source.'''
        source = []

        for module in self.root_modules:
            if module.endswith('.py'):  # file
                source.append(module)
            else:  # dir
                source += [
                    path for path in glob.glob(os.path.join(module, '**'), recursive=True)
                    if os.path.isfile(path) and not path.endswith('.pyc')
                ]
        return source

    @property
    def root_modules(self) -> Sequence[str]:
        '''Project top-level modules.

        By default will look for the normalized name of the project name
        replacing `-` with `_`.
        '''
        name = self.name.replace('-', '_')
        files = os.listdir()
        if f'{name}.py' in files:  # file module
            return [f'{name}.py']
        if name in files:  # dir module
            return [name]
        raise TrampolimError(f'Could not find the top-level module(s) (looking for `{name}`)')

    @cached_property
    def name(self) -> str:
        '''Project name.'''
        name = self._project['name']
        assert isinstance(name, str)
        return re.sub(r'[-_.]+', '-', name).lower()

    @cached_property
    def version(self) -> str:  # noqa: C901
        '''Project version.'''

        if 'version' in self._project:
            version = self._project['version']
            assert isinstance(version, str)
            return version

        if 'TRAMPOLIM_VCS_VERSION' in os.environ:
            return os.environ['TRAMPOLIM_VCS_VERSION']

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
                    if name == 'tag':
                        assert isinstance(value, str)
                        return value.strip(' v')
            if 'commit' in data:
                assert isinstance(data['commit'], str)
                return data['commit']

        # from git repo
        try:
            return subprocess.check_output([
                'git', 'describe', '--tags'
            ]).decode().strip(' v').replace('-', '.')
        except FileNotFoundError:
            pass

        raise TrampolimError(
            'Could not find the project version from VCS (you can set the '
            'TRAMPOLIM_VCS_VERSION environment variable to manually override the version)'
        )

    @cached_property
    def license_file(self) -> Optional[str]:
        '''Project license file (if any).'''
        try:
            file = self._project['license']['file']
            assert isinstance(file, str)
            return file
        except KeyError:
            return None

    @cached_property
    def license(self) -> str:
        '''Project license text.'''
        assert self._project['license']
        if self.license_file:
            with open(self.license_file) as f:
                return f.read()
        else:
            text = self._project['license']['text']
            assert isinstance(text, str)
            return text


class SdistBuilder():
    '''Simple sdist builder.

    Will only include by default the files relevant for source code distribution
    and the required files to be able to build binary distributions.
    '''
    def __init__(self, project: Project) -> None:
        self._project = project

    @property
    def name(self) -> str:
        return f'{self._project.name}.tar.gz'

    def build(self, path: Path) -> None:
        # reproducibility
        source_date_epoch = os.environ.get('SOURCE_DATE_EPOCH')
        mtime = int(source_date_epoch) if source_date_epoch else None

        # open files
        file = typing.cast(
            IO[bytes],
            gzip.GzipFile(
                os.path.join(path, self.name),
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

        # add pyproject.toml
        tar.add('pyproject.toml')

        # add source
        for source_path in self._project.source:
            tar.add(source_path)

        # add license
        if self._project.license_file:
            tar.add(str(self._project.license_file))
        else:
            license_raw = self._project.license.encode()
            info = tarfile.TarInfo('LICENSE')
            info.size = len(license_raw)
            with io.BytesIO(license_raw) as data:
                tar.addfile(info, data)

        # cleanup
        tar.close()
        file.close()
