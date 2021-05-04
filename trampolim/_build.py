# SPDX-License-Identifier: MIT

import functools
import glob
import itertools
import os
import os.path

from typing import Any, List, Optional, Sequence, Type, Union

import toml


Path = Union[str, os.PathLike]


class BuildError(Exception):
    '''Build backend error.'''


class Project():
    def __init__(self) -> None:
        with open('pyproject.toml') as f:
            self._pyproject = toml.load(f)

        if 'project' not in self._pyproject:
            raise BuildError('Missing section `project` in pyproject.toml')

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
            raise BuildError(
                f'Field `project.{key}` has an invalid type, '
                f'expecting string (got `{type(value)}`)'
            )

    def _validate(self) -> None:
        '''Validate the project table.'''
        for field in ('name', 'license'):
            if field not in self._project:
                raise BuildError(f'Field `project.{field}` missing pyproject.toml')

        # name
        self._validate_type('name', str)

        # version
        self._validate_type('version', str)

        # license
        if 'file' not in self._project['license'] and 'text' not in self._project['license']:
            raise BuildError(
                'Invalid `project.license` value in pyproject.toml, '
                f'expecting either `file` or `text` (got `{self._project["license"]}`)'
            )
        for field in ('file', 'text'):
            try:
                self._validate_type('.'.join(['license', field]), str)
            except KeyError:
                continue
        if self.license_file and not os.path.isfile(self.license_file):
            raise BuildError(f'License file not found (`{self.license_file}`)')

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
        '''Project top-level modules.'''
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
