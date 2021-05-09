# SPDX-License-Identifier: MIT

import email
import glob
import gzip
import io
import os
import os.path
import subprocess
import sys
import tarfile
import typing
import warnings

from typing import IO, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import packaging.markers
import packaging.requirements
import packaging.version
import toml

import trampolim._metadata


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

        self._stdmeta = trampolim._metadata.StandardMetadata(self._pyproject)
        self._trampolim_meta = trampolim._metadata.TrampolimMetadata(self._pyproject)

        for field in self._stdmeta.dynamic:
            if field not in self._VALID_DYNAMIC:
                raise ConfigurationError(f'Unsupported field `{field}` in `project.dynamic`')

        self.version  # calculate version

        # warn users about test/tests modules -- they probably don't want them installed!
        for module in ('test', 'tests'):
            if module in self.root_modules:
                warnings.warn(
                    f'Top-level module `{module}` selected, are you sure you want to install it??',
                    TrampolimWarning,
                )

    @property
    def source(self) -> List[str]:
        '''Project source.'''
        source = []

        # TODO: ignore files not escaped as specified in PEP 427
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
        if 'top-level-modules' in self._trampolim_meta:
            return self._trampolim_meta.top_level_modules

        name = self.name.replace('-', '_')
        files = os.listdir()
        if f'{name}.py' in files:  # file module
            return [f'{name}.py']
        if name in files:  # dir module
            return [name]
        raise TrampolimError(f'Could not find the top-level module(s) (looking for `{name}`)')

    @property
    def name(self) -> str:
        '''Project name.'''
        return self._stdmeta.name

    @cached_property
    def version(self) -> packaging.version.Version:  # noqa: C901
        '''Project version.'''

        if self._stdmeta.version:
            return self._stdmeta.version

        if 'version' not in self._stdmeta.dynamic:
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

    @property
    def description(self) -> Optional[str]:
        '''Project description.'''
        return self._stdmeta.description

    @property
    def dependencies(self) -> List[str]:
        '''Project dependencies.'''
        return self._stdmeta.dependencies

    @property
    def optional_dependencies(self) -> Dict[str, List[str]]:
        '''Project optional dependencies.'''
        return self._stdmeta.optional_dependencies

    @property
    def requires_python(self) -> Optional[packaging.specifiers.Specifier]:
        '''Project Python requirements.'''
        return self._stdmeta.requires_python

    @property
    def keywords(self) -> List[str]:
        '''Project keywords.'''
        return self._stdmeta.keywords

    @property
    def license_file(self) -> Optional[str]:
        '''Project license file (if any).'''
        return self._stdmeta.license_file

    @property
    def license_text(self) -> Optional[str]:
        '''Project license text.'''
        return self._stdmeta.license_text

    @property
    def readme_file(self) -> Optional[str]:
        '''Project readme file (if any).'''
        return self._stdmeta.readme_file

    @property
    def readme_text(self) -> Optional[str]:
        '''Project readme text.'''
        return self._stdmeta.readme_text

    @property
    def readme_content_type(self) -> Optional[str]:
        '''Project readme content type.'''
        return self._stdmeta.readme_content_type

    @property
    def authors(self) -> List[Tuple[str, str]]:
        '''Project authors.'''
        return self._stdmeta.authors

    @property
    def maintainers(self) -> List[Tuple[str, str]]:
        '''Project maintainers.'''
        return self._stdmeta.maintainers or self._stdmeta.authors

    @property
    def classifiers(self) -> List[str]:
        '''Project trove classifiers.'''
        return self._stdmeta.classifiers

    @property
    def urls(self) -> Mapping[str, str]:
        '''Project homepage.'''
        return self._stdmeta.urls

    @property
    def scripts(self) -> Dict[str, str]:
        '''Project console script entrypoints.'''
        return self._stdmeta.scripts

    @property
    def gui_scripts(self) -> Dict[str, str]:
        '''Project GUI script entrypoints.'''
        return self._stdmeta.gui_scripts

    @property
    def entrypoints(self) -> Dict[str, Dict[str, str]]:
        '''Project extra entrypoints.'''
        return self._stdmeta.entrypoints

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
        metadata['Metadata-Version'] = '2.2'
        metadata['Name'] = self.name
        metadata['Version'] = str(self.version)
        # skip 'Platform' -- we currently only support pure
        # skip 'Supported-Platform' -- we currently only support pure
        metadata['Summary'] = self.description
        metadata['Keywords'] = ' '.join(self.keywords)
        if 'homepage' in self.urls:
            metadata['Home-page'] = self.urls['homepage']
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
        for name, url in self.urls.items():
            metadata['Project-URL'] = f'{name.capitalize()}, {url}'
        if self.requires_python:
            metadata['Requires-Python'] = str(self.requires_python)
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
        return metadata


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

        # add pyproject.toml
        tar.add('pyproject.toml', f'{self.name}/pyproject.toml')

        # add source
        for source_path in self._project.source:
            tar.add(source_path, f'{self.name}/{source_path}')

        # add license
        if self._project.license_file:
            tar.add(self._project.license_file, f'{self.name}/{self._project.license_file}')
        elif self._project.license_text:
            license_raw = self._project.license_text.encode()
            info = tarfile.TarInfo(f'{self.name}/LICENSE')
            info.size = len(license_raw)
            with io.BytesIO(license_raw) as data:
                tar.addfile(info, data)

        # add readme
        if self._project.readme_file:
            tar.add(self._project.readme_file, f'{self.name}/{self._project.readme_file}')

        # PKG-INFO
        pkginfo = self._project.metadata.as_bytes()
        info = tarfile.TarInfo(f'{self.name}/PKG-INFO')
        info.size = len(pkginfo)
        with io.BytesIO(pkginfo) as data:
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
