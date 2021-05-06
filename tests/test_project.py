# SPDX-License-Identifier: MIT

import os
import re
import textwrap

import pytest

import trampolim
import trampolim._build


@pytest.mark.parametrize(
    ('data', 'error'),
    [
        ('', 'Missing section `project` in pyproject.toml'),
        # name
        ('[project]', 'Field `project.name` missing pyproject.toml'),
        (
            textwrap.dedent('''
                [project]
                name = true
            '''),
            re.escape('Field `project.name` has an invalid type, expecting a string (got `True`)'),
        ),
        # license
        (
            textwrap.dedent('''
                [project]
                name = 'test'
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
                license = { file = '...', text = '...' }
            '''),
            re.escape(
                'Invalid `project.license` value in pyproject.toml, '
                "expecting either `file` or `text` (got `{'file': '...', 'text': '...'}`)"
            ),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                license = { made-up = ':(' }
            '''),
            re.escape(
                'Unexpected field `project.license.made-up`'
            ),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                license = { file = true }
            '''),
            re.escape('Field `project.license.file` has an invalid type, expecting a string (got `True`)'),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                license = { text = true }
            '''),
            re.escape('Field `project.license.text` has an invalid type, expecting a string (got `True`)'),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                license = { file = 'this-file-does-not-exist' }
            '''),
            re.escape('License file not found (`this-file-does-not-exist`)'),
        ),
        # readme
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                readme = {}
            '''),
            re.escape(
                'Invalid `project.readme` value in pyproject.toml, '
                'expecting either `file` or `text` (got `{}`)'
            ),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                readme = { file = '...', text = '...' }
            '''),
            re.escape(
                'Invalid `project.readme` value in pyproject.toml, '
                "expecting either `file` or `text` (got `{'file': '...', 'text': '...'}`)"
            ),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                readme = { made-up = ':(' }
            '''),
            re.escape(
                'Unexpected field `project.readme.made-up`'
            ),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                readme = { file = true }
            '''),
            re.escape('Field `project.readme.file` has an invalid type, expecting a string (got `True`)'),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                readme = { text = true }
            '''),
            re.escape('Field `project.readme.text` has an invalid type, expecting a string (got `True`)'),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                readme = { file = 'this-file-does-not-exist' }
            '''),
            re.escape('Readme file not found (`this-file-does-not-exist`)'),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                readme = { file = 'README.md' }
            '''),
            re.escape('Missing field `project.readme.content-type`'),
        ),
        # description
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                description = true
            '''),
            re.escape('Field `project.description` has an invalid type, expecting a string (got `True`)'),
        ),
        # dependencies
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                dependencies = 'some string!'
            '''),
            re.escape('Field `project.dependencies` has an invalid type, expecting a list of strings (got `some string!`)'),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                dependencies = [
                    99,
                ]
            '''),
            re.escape('Field `project.dependencies` contains item with invalid type, expecting a string (got `99`)'),
        ),
        # keywords
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                keywords = 'some string!'
            '''),
            re.escape('Field `project.keywords` has an invalid type, expecting a list of strings (got `some string!`)'),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                keywords = [
                    true,
                ]
            '''),
            re.escape('Field `project.keywords` contains item with invalid type, expecting a string (got `True`)'),
        ),
        # authors
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                authors = {}
            '''),
            re.escape(
                'Field `project.authors` has an invalid type, expecting a list of '
                'dictionaries containing the `name` and/or `email` keys (got `{}`)'
            ),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                authors = [
                    true,
                ]
            '''),
            re.escape(
                'Field `project.authors` has an invalid type, expecting a list of '
                'dictionaries containing the `name` and/or `email` keys (got `[True]`)'
            ),
        ),
        # maintainers
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                maintainers = {}
            '''),
            re.escape(
                'Field `project.maintainers` has an invalid type, expecting a list of '
                'dictionaries containing the `name` and/or `email` keys (got `{}`)'
            ),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                maintainers = [
                    10
                ]
            '''),
            re.escape(
                'Field `project.maintainers` has an invalid type, expecting a list of '
                'dictionaries containing the `name` and/or `email` keys (got `[10]`)'
            ),
        ),
        # classifiers
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                classifiers = 'some string!'
            '''),
            re.escape('Field `project.classifiers` has an invalid type, expecting a list of strings (got `some string!`)'),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                classifiers = [
                    true,
                ]
            '''),
            re.escape('Field `project.classifiers` contains item with invalid type, expecting a string (got `True`)'),
        ),
        # homepage
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                [project.urls]
                homepage = true
            '''),
            re.escape('Field `project.urls.homepage` has an invalid type, expecting a string (got `True`)'),
        ),
        # documentation
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                [project.urls]
                documentation = true
            '''),
            re.escape('Field `project.urls.documentation` has an invalid type, expecting a string (got `True`)'),
        ),
        # repository
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                [project.urls]
                repository = true
            '''),
            re.escape('Field `project.urls.repository` has an invalid type, expecting a string (got `True`)'),
        ),
        # changelog
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                [project.urls]
                changelog = true
            '''),
            re.escape('Field `project.urls.changelog` has an invalid type, expecting a string (got `True`)'),
        ),
        # scripts
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                scripts = []
            '''),
            re.escape('Field `project.scripts` has an invalid type, expecting a dictionary of strings (got `[]`)'),
        ),
        # gui-scripts
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                gui-scripts = []
            '''),
            re.escape('Field `project.gui-scripts` has an invalid type, expecting a dictionary of strings (got `[]`)'),
        ),
        # entry-points
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                entry-points = []
            '''),
            re.escape(
                'Field `project.entry-points` has an invalid type, '
                'expecting a dictionary of entrypoint sections (got `[]`)'
            ),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                entry-points = { section = 'something' }
            '''),
            re.escape(
                'Field `project.entry-points.section` has an invalid type, '
                'expecting a dictionary of entrypoints (got `something`)'
            ),
        ),
        (
            textwrap.dedent('''
                [project]
                name = 'test'
                [project.entry-points.section]
                entrypoint = []
            '''),
            re.escape('Field `project.entry-points.section.entrypoint` has an invalid type, expecting a string (got `[]`)'),
        ),
    ]
)
def test_validate(package_full_metadata, data, error):
    with pytest.raises(trampolim.ConfigurationError, match=error):
        trampolim._build.Project(_toml=data)


def test_full_metadata(package_full_metadata):
    p = trampolim._build.Project()
    assert p.name == 'full-metadata'
    assert p.version == '3.2.1'
    assert p.description == 'A package with all the metadata :)'
    assert p.license_text == 'some license text'
    assert p.keywords == ['trampolim', 'is', 'interesting']
    assert p.authors == [
        ('Unknown', 'example@example.com'),
        ('Example!', None),
    ]
    assert p.maintainers == [
        ('Other Example', 'other@example.com'),
    ]
    assert p.classifiers == [
        'Development Status :: 4 - Beta',
        'Programming Language :: Python'
    ]
    assert p.homepage == 'example.com'
    assert p.documentation == 'readthedocs.org'
    assert p.repository == 'github.com/some/repo'
    assert p.changelog == 'github.com/some/repo/blob/master/CHANGELOG.rst'
    assert p.scripts == {
        'full-metadata': 'full_metadata:main_cli',
    }
    assert p.gui_scripts == {
        'full-metadata-gui': 'full_metadata:main_gui',
    }
    assert p.entrypoints == {
        'custom': {
            'full-metadata': 'full_metadata:main_custom',
        }
    }
    assert p.python_tags == ['py3']
    assert p.python_tag == 'py3'
    assert p.abi_tag == 'none'
    assert p.platform_tag == 'any'
    # TODO: requires-python, dependencies, optional-dependencies


def test_rfc822_metadata(package_full_metadata):
    assert str(trampolim._build.Project().metadata) == textwrap.dedent('''
        Metadata-Version: 2.1
        Name: full-metadata
        Version: 3.2.1
        Summary: A package with all the metadata :)
        Keywords: trampolim is interesting
        Home-page: example.com
        Author: Unknown <example@example.com>, Example!
        Author-Email: Unknown <example@example.com>, Example!
        Maintainer: Other Example <other@example.com>
        Maintainer-Email: Other Example <other@example.com>
        Classifier: Development Status :: 4 - Beta
        Classifier: Programming Language :: Python
        Project-URL: Documentation, readthedocs.org
        Project-URL: Repository, github.com/some/repo
        Project-URL: Changelog, github.com/some/repo/blob/master/CHANGELOG.rst
        Requires-Dist: dependency1
        Requires-Dist: dependency2>1.0.0
        Requires-Dist: dependency3[extra]
        Requires-Dist: dependency4; os_name != "nt"
        Requires-Dist: dependency5[other-extra]>1.0; os_name == "nt"

        some readme
    ''').lstrip()


def test_rfc822_metadata_bytes(package_sample_source):
    assert trampolim._build.Project().metadata.as_bytes() == textwrap.dedent('''
        Metadata-Version: 2.1
        Name: sample-source
        Version: 0.0.0
    ''').lstrip().encode()


def test_readme_md(package_readme_md):
    assert trampolim._build.Project().readme_content_type == 'text/markdown'


def test_readme_rst(package_readme_rst):
    assert trampolim._build.Project().readme_content_type == 'text/x-rst'


def test_readme_unknown(package_readme_unknown):
    with pytest.raises(
        trampolim.TrampolimError,
        match=re.escape('Could not infer content type for readme file `README.unknown`'),
    ):
        assert trampolim._build.Project().readme_content_type


def test_readme_unknown_with_type(package_readme_unknown_with_type):
    assert trampolim._build.Project().readme_content_type == 'text/some-unknown-type'


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


def test_license_file(package_license_file):
    assert trampolim._build.Project().license_file == 'some-license-file'


def test_license_text_inline(package_license_text):
    assert trampolim._build.Project().license_text == 'inline license!'


def test_license_text_from_file(package_license_file):
    assert trampolim._build.Project().license_text == 'blah\n'


def test_version(package_sample_source):
    assert trampolim._build.Project().version == '0.0.0'


def test_vcs_version_envvar(package_vcs_version1):
    os.environ['TRAMPOLIM_VCS_VERSION'] = '1.2.3'
    assert trampolim._build.Project().version == '1.2.3'
    os.environ.pop('TRAMPOLIM_VCS_VERSION')


def test_vcs_version_git_archive_tag_alone(package_vcs_version1):
    assert trampolim._build.Project().version == '0.0.1'


def test_vcs_version_git_archive_many_refs_tag(package_vcs_version2):
    assert trampolim._build.Project().version == '0.0.2'


def test_vcs_version_git_archive_commit(package_vcs_version3):
    assert trampolim._build.Project().version == 'this-is-a-commit'


def test_vcs_version_git_archive_unpopulated(mocker, package_vcs_version_unpopulated):
    mocker.patch('subprocess.check_output', side_effect=FileNotFoundError)
    with pytest.raises(trampolim.TrampolimError, match=re.escape(
        'Could not find the project version from VCS (you can set the '
        'TRAMPOLIM_VCS_VERSION environment variable to manually override the version)'
    )):
        trampolim._build.Project()


def test_vcs_git_repo(mocker, package_no_version):
    mocker.patch(
        'subprocess.check_output',
        side_effect=[b'1.0.0-23-gea1f213'],
    )
    assert trampolim._build.Project().version == '1.0.0.23.gea1f213'


def test_vcs_no_version(mocker, package_no_version):
    mocker.patch('subprocess.check_output', side_effect=FileNotFoundError)
    with pytest.raises(trampolim.TrampolimError, match=re.escape(
        'Could not find the project version from VCS (you can set the '
        'TRAMPOLIM_VCS_VERSION environment variable to manually override the version)'
    )):
        trampolim._build.Project()
