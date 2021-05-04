# SPDX-License-Identifier: MIT

import re
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


def test_no_module(package_no_module):
    with pytest.raises(
        trampolim.TrampolimError,
        match=re.escape('Could not find the top-level module(s) (looking for `no_module`)'),
    ):
        trampolim._build.Project()


def test_root_modules_dir(package_sample_source):
    project = trampolim._build.Project()

    assert project.root_modules == ['sample_source']


def test_root_modules_file(package_file_module):
    project = trampolim._build.Project()

    assert project.root_modules == ['file_module.py']
