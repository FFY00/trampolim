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
            re.escape(
                'Invalid `project.license` value in pyproject.toml, '
                'expecting either `file` or `text` (got `{}`)'
            ),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                version = '1.0.0'
                license = { made-up = ':(' }
            '''),
            re.escape(
                'Invalid `project.license` value in pyproject.toml, '
                "expecting either `file` or `text` (got `{'made-up': ':('}`)"
            ),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                version = '1.0.0'
                license = { file = true }
            '''),
            re.escape('Field `project.license.file` has an invalid type, expecting string (got `True`)'),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                version = '1.0.0'
                license = { text = true }
            '''),
            re.escape('Field `project.license.text` has an invalid type, expecting string (got `True`)'),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                version = '1.0.0'
                license = { file = 'this-file-does-not-exist' }
            '''),
            re.escape('License file not found (`this-file-does-not-exist`)'),
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


@pytest.mark.parametrize(
    ('original', 'normalized'),
    [
        ('simple', 'simple'),
        ('a-b', 'a-b'),
        ('a_b', 'a-b'),
        ('a.b', 'a-b'),
        ('a---b', 'a-b'),
        ('a___b', 'a-b'),
        ('a...b', 'a-b'),
        ('a-_.b', 'a-b'),
        ('a-b_c', 'a-b-c'),
        ('a_b_c', 'a-b-c'),
        ('a.b_c', 'a-b-c'),
    ]
)
def test_name_normalization(package_sample_source, original, normalized):
    class DummyModules(trampolim._build.Project):
        @property
        def root_modules(self):
            return ['dummy']  # remove module dicovery

    assert DummyModules(_toml='''
        [project]
        name = '%NAME%'
        version = '1.0.0'
        license = { text = '...' }
    '''.replace('%NAME%', original)).name == normalized


def test_version(package_sample_source):
    assert trampolim._build.Project().version == '0.0.0'


def test_license_file(package_license_file):
    assert trampolim._build.Project().license_file == 'some-license-file'


def test_license_text_inline(package_license_text):
    assert trampolim._build.Project().license == 'inline license!'


def test_license_text_from_file(package_license_file):
    assert trampolim._build.Project().license == 'blah\n'
