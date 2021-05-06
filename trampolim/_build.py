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

from typing import IO, Dict, List, Optional, Sequence, Tuple, Union

import packaging.markers
import packaging.requirements
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
    _VALID_KEYS = {
        'license': [
            'file',
            'text',
        ],
        'readme': [
            'content-type',
            'file',
            'text',
        ]
    }
    _VALID_DYNAMIC = [
        'version',
    ]

    def __init__(self, _toml: Optional[str] = None) -> None:
        if _toml is not None:
            self._pyproject = toml.loads(_toml)
        else:
            with open('pyproject.toml') as f:
                self._pyproject = toml.load(f)

        if 'project' not in self._pyproject:
            raise ConfigurationError('Missing section `project` in pyproject.toml')

        self._project = self._pyproject['project']

        dynamic = self._pget_list('dynamic')
        self._dynamic = dynamic if dynamic else []
        for field in self._dynamic:
            if field not in self._VALID_DYNAMIC:
                raise ConfigurationError(f'Unsupported field in `project.dynamic`: `project.{field}`')

        self._validate()

        self.version  # calculate version

        # warn users about test/tests modules -- they probably don't want them installed!
        for module in ('test', 'tests'):
            if module in self.root_modules:
                warnings.warn(
                    f'Top-level module `{module}` selected, are you sure you want to install it??',
                    TrampolimWarning,
                )

    def _validate(self) -> None:
        '''Validate the project table.'''
        if 'name' not in self._project:
            raise ConfigurationError('Field `project.name` missing pyproject.toml')

        # license
        if 'license' in self._project:
            license = self._pget_dict('license')
            if (
                ('file' not in license and 'text' not in license) or
                ('file' in license and 'text' in license)
            ):
                raise ConfigurationError(
                    'Invalid `project.license` value in pyproject.toml, '
                    f'expecting either `file` or `text` (got `{license}`)'
                )
            if self.license_file and not os.path.isfile(self.license_file):
                raise ConfigurationError(f'License file not found (`{self.license_file}`)')

        # readme
        if 'readme' in self._project and not isinstance(self._project['readme'], str):
            readme = self._pget_dict('readme')
            if (
                ('file' not in readme and 'text' not in readme) or
                ('file' in readme and 'text' in readme)
            ):
                raise ConfigurationError(
                    'Invalid `project.readme` value in pyproject.toml, '
                    f'expecting either `file` or `text` (got `{readme}`)'
                )
        if self.readme_file and not os.path.isfile(self.readme_file):
            raise ConfigurationError(f'Readme file not found (`{self.readme_file}`)')

        # try to fetch the fields to run validation -- we do validation on the getters because mypy
        self.name
        self.description
        self.dependencies
        self.optional_dependencies
        self.requires_python
        self.keywords
        self.license_file
        self.license_text
        self.readme_file
        self.readme_text
        self.readme_content_type
        self.authors
        self.maintainers
        self.classifiers
        self.homepage
        self.documentation
        self.repository
        self.changelog
        self.scripts
        self.gui_scripts
        self.entrypoints

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
        name = self._pget_str('name')
        assert name
        return re.sub(r'[-_.]+', '-', name).lower()

    @cached_property
    def version(self) -> str:  # noqa: C901
        '''Project version.'''

        if 'version' in self._project:
            version = self._project['version']
            assert isinstance(version, str)
            return version

        if 'version' not in self._dynamic:
            raise ConfigurationError(
                'Missing required field `project.version` (if you want to infer the project version '
                'automatically, `version` needs to be added to the `project.dynamic` list field)'
            )

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
                    if name == 'tag' and '$' not in value:
                        assert isinstance(value, str)
                        return value.strip(' v')
            if 'commit' in data and '$' not in data['commit']:
                assert isinstance(data['commit'], str)
                return data['commit']

        # from git repo
        try:
            return subprocess.check_output([
                'git', 'describe', '--tags'
            ]).decode().strip(' v').replace('-', '.')
        except (FileNotFoundError, subprocess.CalledProcessError):
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

    def _pget_str(self, key: str) -> Optional[str]:
        try:
            val = self._project
            for part in key.split('.'):
                val = val[part]
            if not isinstance(val, str):
                raise ConfigurationError(
                    f'Field `project.{key}` has an invalid type, '
                    f'expecting a string (got `{val}`)'
                )
            return val
        except KeyError:
            return None

    def _pget_list(self, key: str) -> List[str]:
        try:
            val = self._project
            for part in key.split('.'):
                val = val[part]
            if not isinstance(val, list):
                raise ConfigurationError(
                    f'Field `project.{key}` has an invalid type, '
                    f'expecting a list of strings (got `{val}`)'
                )
            for item in val:
                if not isinstance(item, str):
                    raise ConfigurationError(
                        f'Field `project.{key}` contains item with invalid type, '
                        f'expecting a string (got `{item}`)'
                    )
            return val
        except KeyError:
            return []

    def _pget_dict(self, key: str) -> Dict[str, str]:
        try:
            val = self._project
            for part in key.split('.'):
                val = val[part]
            if not isinstance(val, dict):
                raise ConfigurationError(
                    f'Field `project.{key}` has an invalid type, '
                    f'expecting a dictionary of strings (got `{val}`)'
                )
            valid_keys = self._VALID_KEYS.get(key)
            for subkey, item in val.items():
                if valid_keys and subkey not in valid_keys:
                    raise ConfigurationError(f'Unexpected field `project.{key}.{subkey}`')
                if not isinstance(item, str):
                    raise ConfigurationError(
                        f'Field `project.{key}.{subkey}` has an invalid type, '
                        f'expecting a string (got `{item}`)'
                    )
            return val
        except KeyError:
            return {}

    def _pget_people(self, key: str) -> List[Tuple[str, str]]:
        try:
            val = self._project
            for part in key.split('.'):
                val = val[part]
            if not (
                isinstance(val, list)
                and all(isinstance(x, dict) for x in val)
                and all(
                    isinstance(item, str)
                    for items in [_dict.values() for _dict in val]
                    for item in items
                )
            ):
                raise ConfigurationError(
                    f'Field `project.{key}` has an invalid type, expecting a list of '
                    f'dictionaries containing the `name` and/or `email` keys (got `{val}`)'
                )
            return [
                (entry.get('name', 'Unknown'), entry.get('email'))
                for entry in val
            ]
        except KeyError:
            return []

    @cached_property
    def description(self) -> Optional[str]:
        '''Project description.'''
        return self._pget_str('description')

    @cached_property
    def dependencies(self) -> List[str]:
        '''Project dependencies.'''
        return self._pget_list('dependencies')

    @cached_property
    def optional_dependencies(self) -> Dict[str, List[str]]:
        '''Project optional dependencies.'''
        try:
            val = self._project['optional-dependencies']
            if not isinstance(val, dict):
                raise ConfigurationError(
                    'Field `project.optional-dependencies` has an invalid type, expecting a '
                    f'dictionary of PEP 508 requirement strings (got `{val}`)'
                )
            for extra, requirements in val.items():
                assert isinstance(extra, str)
                if not isinstance(requirements, list):
                    raise ConfigurationError(
                        f'Field `project.optional-dependencies.{extra}` has an invalid type, expecting a '
                        f'dictionary PEP 508 requirement strings (got `{requirements}`)'
                    )
                for req in requirements:
                    if not isinstance(req, str):
                        raise ConfigurationError(
                            f'Field `project.optional-dependencies.{extra}` has an invalid type, '
                            f'expecting a PEP 508 requirement string (got `{req}`)'
                        )
                    try:
                        packaging.requirements.Requirement(req)
                    except packaging.requirements.InvalidRequirement as e:
                        raise ConfigurationError(
                            f'Field `project.optional-dependencies.{extra}` contains '
                            f'an invalid PEP 508 requirement string `{req}` (`{str(e)}`)'
                        )
            return val
        except KeyError:
            return {}

    @cached_property
    def requires_python(self) -> Optional[str]:
        '''Project Python requirements.'''
        return self._pget_str('requires-python')

    @cached_property
    def keywords(self) -> List[str]:
        '''Project keywords.'''
        return self._pget_list('keywords')

    @cached_property
    def license_file(self) -> Optional[str]:
        '''Project license file (if any).'''
        return self._pget_str('license.file')

    @cached_property
    def license_text(self) -> Optional[str]:
        '''Project license text.'''
        if self.license_file:
            with open(self.license_file) as f:
                return f.read()
        else:
            val = self._pget_str('license.text')
            if val and '\n' in val:  # pragma: no cover
                raise ConfigurationError('Newlines are not supported in the `project.license.text` field')
            return val

    @cached_property
    def readme_file(self) -> Optional[str]:
        '''Project readme file (if any).'''
        if 'readme' not in self._project:
            return None
        val = self._project['readme']
        if isinstance(val, str):
            return val
        return self._pget_dict('readme').get('file')

    @cached_property
    def readme_text(self) -> Optional[str]:
        '''Project readme text.'''
        if self.readme_file:
            with open(self.readme_file) as f:
                return f.read()
        else:
            return self._pget_str('readme.text')

    @cached_property
    def readme_content_type(self) -> Optional[str]:
        '''Project readme content type.'''
        if 'readme' not in self._project:
            return None
        if isinstance(self._project['readme'], str):
            assert self.readme_file
            if self.readme_file.endswith('.md'):
                return 'text/markdown'
            if self.readme_file.endswith('.rst'):
                return 'text/x-rst'
            raise TrampolimError(f'Could not infer content type for readme file `{self.readme_file}`')
        val = self._pget_dict('readme')
        if 'content-type' not in val:
            raise ConfigurationError('Missing field `project.readme.content-type`')
        return val['content-type']

    @cached_property
    def authors(self) -> List[Tuple[str, str]]:
        '''Project authors.'''
        return self._pget_people('authors')

    @cached_property
    def maintainers(self) -> List[Tuple[str, str]]:
        '''Project maintainers.'''
        return self._pget_people('maintainers')

    @cached_property
    def classifiers(self) -> List[str]:
        '''Project trove classifiers.'''
        return self._pget_list('classifiers')

    @cached_property
    def homepage(self) -> Optional[str]:
        '''Project homepage.'''
        return self._pget_str('urls.homepage')

    @cached_property
    def documentation(self) -> Optional[str]:
        '''Project documentation.'''
        return self._pget_str('urls.documentation')

    @cached_property
    def repository(self) -> Optional[str]:
        '''Project repository.'''
        return self._pget_str('urls.repository')

    @cached_property
    def changelog(self) -> Optional[str]:
        '''Project repository.'''
        return self._pget_str('urls.changelog')

    @cached_property
    def scripts(self) -> Dict[str, str]:
        '''Project console script entrypoints.'''
        return self._pget_dict('scripts')

    @cached_property
    def gui_scripts(self) -> Dict[str, str]:
        '''Project GUI script entrypoints.'''
        return self._pget_dict('gui-scripts')

    @cached_property
    def entrypoints(self) -> Dict[str, Dict[str, str]]:
        '''Project extra entrypoints.'''
        try:
            val = self._project['entry-points']
            if not isinstance(val, dict):
                raise ConfigurationError(
                    'Field `project.entry-points` has an invalid type, expecting a '
                    f'dictionary of entrypoint sections (got `{val}`)'
                )
            for section, entrypoints in val.items():
                assert isinstance(section, str)
                if not isinstance(entrypoints, dict):
                    raise ConfigurationError(
                        f'Field `project.entry-points.{section}` has an invalid type, expecting a '
                        f'dictionary of entrypoints (got `{entrypoints}`)'
                    )
                for name, entrypoint in entrypoints.items():
                    assert isinstance(name, str)
                    if not isinstance(entrypoint, str):
                        raise ConfigurationError(
                            f'Field `project.entry-points.{section}.{name}` has an invalid type, '
                            f'expecting a string (got `{entrypoint}`)'
                        )
            return val
        except KeyError:
            return {}

    def _person_list(self, people: List[Tuple[str, str]]) -> str:
        return ', '.join([
            '{}{}'.format(
                name,
                f' <{_email}>' if _email else ''
            )
            for name, _email in people
        ])

    @property
    def metadata(self) -> 'RFC822Message':  # noqa: C901
        '''dist-info METADATA.'''
        metadata = RFC822Message()
        metadata['Metadata-Version'] = '2.1'
        metadata['Name'] = self.name
        metadata['Version'] = self.version
        # skip 'Platform' -- we currently only support pure
        # skip 'Supported-Platform' -- we currently only support pure
        metadata['Summary'] = self.description
        metadata['Keywords'] = ' '.join(self.keywords)
        metadata['Home-page'] = self.homepage
        # skip 'Download-URL'
        metadata['Author'] = metadata['Author-Email'] = self._person_list(self.authors)
        if self.maintainers != self.authors:
            metadata['Maintainer'] = metadata['Maintainer-Email'] = self._person_list(self.maintainers)
        # TODO: 'License'
        for classifier in self.classifiers:
            metadata['Classifier'] = classifier
        # skip 'Provides-Dist'
        # skip 'Obsoletes-Dist'
        # skip 'Requires-External'
        if self.documentation:
            metadata['Project-URL'] = f'Documentation, {self.documentation}'
        if self.repository:
            metadata['Project-URL'] = f'Repository, {self.repository}'
        if self.changelog:
            metadata['Project-URL'] = f'Changelog, {self.changelog}'
        # TODO: 'Description-Content-Type'
        if self.requires_python:
            metadata['Requires-Python'] = self.requires_python
        for dep in self.dependencies:
            metadata['Requires-Dist'] = dep
        for extra, requirements in self.optional_dependencies.items():
            metadata['Provides-Extra'] = extra
            for req_string in requirements:
                req = packaging.requirements.Requirement(req_string)
                if req.marker:  # append our extra to the marker
                    req.marker = packaging.markers.Marker(
                        str(req.marker) + f' and extra == "{extra}"'
                    )
                else:  # add our extra marker
                    req.marker = packaging.markers.Marker(f'extra == "{extra}"')
                metadata['Requires-Dist'] = str(req)
        if self.readme_content_type:
            metadata['Description-Content-Type'] = self.readme_content_type
        metadata.body = self.readme_text
        # print(str(metadata), end='')
        return metadata


class SdistBuilder():
    '''Simple sdist builder.

    Will only include by default the files relevant for source code distribution
    and the required files to be able to build binary distributions.
    '''
    def __init__(self, project: Project) -> None:
        self._project = project

    @property
    def file(self) -> str:
        return f'{self._project.name}-{self._project.version}.tar.gz'

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

        # add pyproject.toml
        tar.add('pyproject.toml')

        # add source
        for source_path in self._project.source:
            tar.add(source_path)

        # add license
        if self._project.license_file:
            tar.add(str(self._project.license_file))
        elif self._project.license_text:
            license_raw = self._project.license_text.encode()
            info = tarfile.TarInfo('LICENSE')
            info.size = len(license_raw)
            with io.BytesIO(license_raw) as data:
                tar.addfile(info, data)

        # cleanup
        tar.close()
        file.close()


class RFC822Message():
    def __init__(self) -> None:
        self._headers: Dict[str, List[str]] = {}
        self.body: Optional[str] = None

    def __setitem__(self, name: str, value: Optional[str]) -> None:
        if not value:
            return
        if name not in self._headers:
            self._headers[name] = []
        self._headers[name].append(value)

    def __str__(self) -> str:
        text = ''
        for name, entries in self._headers.items():
            for entry in entries:
                text += f'{name}: {entry}\n'
        if self.body:
            text += '\n' + self.body
        return text

    def as_bytes(self) -> bytes:
        return str(self).encode()
