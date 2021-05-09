# SPDX-License-Identifier: MIT

import os
import os.path
import re

from typing import Any, Dict, List, Mapping, Optional, Tuple

import packaging.markers
import packaging.requirements
import packaging.version

import trampolim._build


class Metadata():
    def __init__(self, data: Mapping[str, Any]) -> None:
        self._data = data

    def __contains__(self, key: Any) -> bool:
        if not isinstance(key, str):  # pragma: no cover
            return False
        try:
            val = self._data['tool']['trampolim']
            for part in key.split('.'):
                val = val[part]
            return True
        except KeyError:
            return False

    def _get(self, key: str) -> Any:
        val = self._data
        for part in key.split('.'):
            val = val[part]
        return val

    def _get_str(self, key: str) -> Optional[str]:
        try:
            val = self._get(key)
            if not isinstance(val, str):
                raise trampolim._build.ConfigurationError(
                    f'Field `{key}` has an invalid type, '
                    f'expecting a string (got `{val}`)',
                    key=key,
                )
            return val
        except KeyError:
            return None

    def _get_list(self, key: str) -> List[str]:
        try:
            val = self._get(key)
            if not isinstance(val, list):
                raise trampolim._build.ConfigurationError(
                    f'Field `{key}` has an invalid type, '
                    f'expecting a list of strings (got `{val}`)',
                    key=val,
                )
            for item in val:
                if not isinstance(item, str):
                    raise trampolim._build.ConfigurationError(
                        f'Field `{key}` contains item with invalid type, '
                        f'expecting a string (got `{item}`)',
                        key=key,
                    )
            return val
        except KeyError:
            return []

    def _get_dict(self, key: str) -> Dict[str, str]:
        try:
            val = self._get(key)
            if not isinstance(val, dict):
                raise trampolim._build.ConfigurationError(
                    f'Field `{key}` has an invalid type, '
                    f'expecting a dictionary of strings (got `{val}`)',
                    key=key,
                )
            for subkey, item in val.items():
                if not isinstance(item, str):
                    raise trampolim._build.ConfigurationError(
                        f'Field `{key}.{subkey}` has an invalid type, '
                        f'expecting a string (got `{item}`)',
                        key=f'{key}.{subkey}',
                    )
            return val
        except KeyError:
            return {}

    def _get_people(self, key: str) -> List[Tuple[str, str]]:
        try:
            val = self._get(key)
            if not (
                isinstance(val, list)
                and all(isinstance(x, dict) for x in val)
                and all(
                    isinstance(item, str)
                    for items in [_dict.values() for _dict in val]
                    for item in items
                )
            ):
                raise trampolim._build.ConfigurationError(
                    f'Field `{key}` has an invalid type, expecting a list of '
                    f'dictionaries containing the `name` and/or `email` keys (got `{val}`)',
                    key=key,
                )
            return [
                (entry.get('name', 'Unknown'), entry.get('email'))
                for entry in val
            ]
        except KeyError:
            return []


class StandardMetadata(Metadata):
    def __init__(self, data: Mapping[str, Any]) -> None:
        super().__init__(data)

        if 'project' not in self._data:
            raise trampolim._build.ConfigurationError('Section `project` missing in pyproject.toml')

        self.dynamic = self._get_list('project.dynamic')
        if 'name' in self.dynamic:
            raise trampolim._build.ConfigurationError('Unsupported field `name` in `project.dynamic`')

        name = self._get_str('project.name')
        if not name:
            raise trampolim._build.ConfigurationError('Field `project.name` missing')
        self.name = re.sub(r'[-_.]+', '-', name).lower()

        version = self._get_str('project.version')
        self.version = packaging.version.Version(version) if version else None

        requires_python = self._get_str('project.requires-python')
        self.requires_python = packaging.specifiers.Specifier(requires_python) if requires_python else None

        self.license_file, self.license_text = self._get_license()
        self.readme_file, self.readme_text, self.readme_content_type = self._get_readme()
        self.optional_dependencies = self._get_optional_dependencies()
        self.entrypoints = self._get_entrypoints()

        self.description = self._get_str('project.description')
        self.authors = self._get_people('project.authors')
        self.maintainers = self._get_people('project.maintainers')
        self.keywords = self._get_list('project.keywords')
        self.classifiers = self._get_list('project.classifiers')
        self.dependencies = self._get_list('project.dependencies')
        self.urls = self._get_dict('project.urls')
        self.scripts = self._get_dict('project.scripts')
        self.gui_scripts = self._get_dict('project.gui-scripts')

    def _get_license(self) -> Tuple[Optional[str], Optional[str]]:
        if 'license' not in self._data['project']:
            return (None, None)

        _license = self._get_dict('project.license')
        for field in _license:
            if field not in ('file', 'text'):
                raise trampolim._build.ConfigurationError(
                    f'Unexpected field `project.license.{field}`',
                    key=f'project.license.{field}',
                )

        file = self._get_str('project.license.file')
        text = self._get_str('project.license.text')

        if (file and text) or (not file and not text):
            raise trampolim._build.ConfigurationError(
                f'Invalid `project.license` value, expecting either `file` or `text` (got `{_license}`)',
                key='project.license',
            )

        if file:
            if not os.path.isfile(file):
                raise trampolim._build.ConfigurationError(
                    f'License file not found (`{file}`)',
                    key='project.license.file',
                )
            with open(file) as f:
                text = f.read()

        return (file, text)

    def _get_readme(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:  # noqa: C901
        if 'readme' not in self._data['project']:
            return (None, None, None)

        file: Optional[str]
        text: Optional[str]
        content_type: Optional[str]

        readme = self._get('project.readme')
        if isinstance(readme, str):
            # readme is a file
            text = None
            file = readme
            if file.endswith('.md'):
                content_type = 'text/markdown'
            elif file.endswith('.rst'):
                content_type = 'text/x-rst'
            else:
                raise trampolim._build.ConfigurationError(
                    f'Could not infer content type for readme file `{file}`',
                    key='project.readme',
                )
        elif isinstance(readme, dict):
            # readme is a dict containing either 'file' or 'text', and content-type
            for field in readme:
                if field not in ('content-type', 'file', 'text'):
                    raise trampolim._build.ConfigurationError(
                        f'Unexpected field `project.readme.{field}`',
                        key=f'project.readme.{field}',
                    )
            content_type = self._get_str('project.readme.content-type')
            file = self._get_str('project.readme.file')
            text = self._get_str('project.readme.text')
            if (file and text) or (not file and not text):
                raise trampolim._build.ConfigurationError(
                    f'Invalid `project.readme` value, expecting either `file` or `text` (got `{readme}`)',
                    key='project.license',
                )
            if not content_type:
                raise trampolim._build.ConfigurationError(
                    'Field `project.readme.content-type` missing',
                    key='project.readme.content-type',
                )
        else:
            raise trampolim._build.ConfigurationError(
                f'Field `project.readme` has an invalid type, expecting either, '
                f'a string or dictionary of strings (got `{readme}`)',
                key='project.readme',
            )

        if file:
            if not os.path.isfile(file):
                raise trampolim._build.ConfigurationError(
                    f'Readme file not found (`{file}`)',
                    key='project.license.file',
                )
            with open(file) as f:
                text = f.read()

        return (file, text, content_type)

    def _get_optional_dependencies(self) -> Dict[str, List[str]]:
        try:
            val = self._data['project']['optional-dependencies']
            if not isinstance(val, dict):
                raise trampolim._build.ConfigurationError(
                    'Field `project.optional-dependencies` has an invalid type, expecting a '
                    f'dictionary of PEP 508 requirement strings (got `{val}`)'
                )
            for extra, requirements in val.items():
                assert isinstance(extra, str)
                if not isinstance(requirements, list):
                    raise trampolim._build.ConfigurationError(
                        f'Field `project.optional-dependencies.{extra}` has an invalid type, expecting a '
                        f'dictionary PEP 508 requirement strings (got `{requirements}`)'
                    )
                for req in requirements:
                    if not isinstance(req, str):
                        raise trampolim._build.ConfigurationError(
                            f'Field `project.optional-dependencies.{extra}` has an invalid type, '
                            f'expecting a PEP 508 requirement string (got `{req}`)'
                        )
                    try:
                        packaging.requirements.Requirement(req)
                    except packaging.requirements.InvalidRequirement as e:
                        raise trampolim._build.ConfigurationError(
                            f'Field `project.optional-dependencies.{extra}` contains '
                            f'an invalid PEP 508 requirement string `{req}` (`{str(e)}`)'
                        )
            return val
        except KeyError:
            return {}

    def _get_entrypoints(self) -> Dict[str, Dict[str, str]]:
        try:
            val = self._data['project']['entry-points']
            if not isinstance(val, dict):
                raise trampolim._build.ConfigurationError(
                    'Field `project.entry-points` has an invalid type, expecting a '
                    f'dictionary of entrypoint sections (got `{val}`)'
                )
            for section, entrypoints in val.items():
                assert isinstance(section, str)
                if not isinstance(entrypoints, dict):
                    raise trampolim._build.ConfigurationError(
                        f'Field `project.entry-points.{section}` has an invalid type, expecting a '
                        f'dictionary of entrypoints (got `{entrypoints}`)'
                    )
                for name, entrypoint in entrypoints.items():
                    assert isinstance(name, str)
                    if not isinstance(entrypoint, str):
                        raise trampolim._build.ConfigurationError(
                            f'Field `project.entry-points.{section}.{name}` has an invalid type, '
                            f'expecting a string (got `{entrypoint}`)'
                        )
            return val
        except KeyError:
            return {}


class TrampolimMetadata(Metadata):
    def __init__(self, data: Mapping[str, Any]) -> None:
        super().__init__(data)
        self.top_level_modules = self._get_list('tool.trampolim.top-level-modules')
