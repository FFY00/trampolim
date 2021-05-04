# SPDX-License-Identifier: MIT

import functools
import glob
import gzip
import io
import itertools
import os
import os.path
import tarfile
import typing

from typing import IO, Any, List, Optional, Sequence, Type, Union

import toml


Path = Union[str, os.PathLike]


class TrampolimError(Exception):
    '''Backend error.'''


class ConfigurationError(TrampolimError):
    '''Error in the backend configuration.'''


class Project():
    def __init__(self) -> None:
        with open('pyproject.toml') as f:
            self._pyproject = toml.load(f)

        if 'project' not in self._pyproject:
            raise ConfigurationError('Missing section `project` in pyproject.toml')

        self._project = self._pyproject['project']

        self._validate()

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
        return [
            path for path in itertools.chain(*[
                glob.glob(os.path.join(module, '**'), recursive=True)
                for module in self.root_modules
            ])
            if os.path.isfile(path) and not path.endswith('.pyc')
        ]

    @property
    def root_modules(self) -> Sequence[str]:
        '''Project top-level modules.

        By default will look for files in the root folder for modules containing
        a __init__.py.
        '''
        return list(map(
            lambda x: os.path.dirname(x),
            glob.glob(os.path.join('*', '__init__.py')),
        ))

    @functools.cached_property
    def name(self) -> str:
        '''Project name.'''
        name = self._project['name']
        assert isinstance(name, str)
        return name

    @functools.cached_property
    def version(self) -> str:
        '''Project version.'''
        # TODO: Allow dynamic -- discover from git or archive
        version = self._project['version']
        assert isinstance(version, str)
        return version

    @functools.cached_property
    def license_file(self) -> Optional[str]:
        '''Project license file (if any).'''
        try:
            file = self._project['license']['file']
            assert isinstance(file, str)
            return file
        except KeyError:
            return None

    @functools.cached_property
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
        return f'{self._project.name}'

    def build(self, path: Path) -> None:
        # reproducibility
        source_date_epoch = os.environ.get('SOURCE_DATE_EPOCH')
        mtime = int(source_date_epoch) if source_date_epoch else None

        # open files
        file = typing.cast(
            IO[bytes],
            gzip.GzipFile(
                os.path.join(path, f'{self.name}.tar.gz'),
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
        for path in self._project.source:
            tar.add(path)

        # add license
        if self._project.license_file:
            tar.add(str(self._project.license_file))
        else:
            tar.addfile(
                tarfile.TarInfo('LICENSE'),
                io.BytesIO(self._project.license.encode()),
            )

        # cleanup
        tar.close()
        file.close()
