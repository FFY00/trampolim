# SPDX-License-Identifier: MIT

import textwrap

import pytest

import trampolim
import trampolim._build


@pytest.mark.parametrize(
    ('data', 'error'),
    [
        ('', 'Missing section `project` in pyproject.toml'),
        ('[project]', 'Field `project.name` missing pyproject.toml'),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
            '''),
            'Field `project.version` missing pyproject.toml',
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                version = '1.0.0'
            '''),
            'Field `project.license` missing pyproject.toml',
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                version = '1.0.0'
                license = {}
            '''),
            'Invalid `project.license` value in pyproject.toml, '
            r'expecting either `file` or `text` \(got `{}`\)',
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                version = '1.0.0'
                license = { made-up = ':(' }
            '''),
            'Invalid `project.license` value in pyproject.toml, '
            r'expecting either `file` or `text` \(got `{\'made-up\': \':\(\'}`\)',
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                version = '1.0.0'
                license = { file = true }
            '''),
            r'Field `project.license.file` has an invalid type, expecting string \(got `True`\)',
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                version = '1.0.0'
                license = { text = true }
            '''),
            r'Field `project.license.text` has an invalid type, expecting string \(got `True`\)',
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                version = '1.0.0'
                license = { file = 'this-file-does-not-exist' }
            '''),
            r'License file not found \(`this-file-does-not-exist`\)',
        ),
    ]
)
def test_validate(package_sample_source, data, error):
    with pytest.raises(trampolim.ConfigurationError, match=error):
        trampolim._build.Project(_toml=data)
