# SPDX-License-Identifier: MIT

import os
import os.path
import re
import textwrap

import packaging.version
import pytest

import trampolim
import trampolim._build


def test_unsupported_dynamic():
    with pytest.raises(
        trampolim.ConfigurationError,
        match=re.escape('Unsupported field `readme` in `project.dynamic`'),
    ):
        trampolim._build.Project(_toml='''
            [project]
            name = 'test'
            dynamic = [
                'readme',
            ]
        ''')


def test_no_version():
    with pytest.raises(
        trampolim.ConfigurationError,
        match=re.escape(
            'Missing required field `project.version` (if you want to infer the '
            'project version automatically, `version` needs to be added to the '
            '`project.dynamic` list field'
        ),
    ):
        trampolim._build.Project(_toml='''
            [project]
            name = 'test'
        ''')


def test_full_metadata(package_full_metadata):
    p = trampolim._build.Project()
    m = p.meta
    assert m.name == 'full-metadata'
    assert str(m.version) == '3.2.1'
    assert m.description == 'A package with all the metadata :)'
    assert m.license.text == 'some license text'
    assert m.keywords == ['trampolim', 'is', 'interesting']
    assert m.authors == [
        ('Unknown', 'example@example.com'),
        ('Example!', None),
    ]
    assert m.maintainers == [
        ('Other Example', 'other@example.com'),
    ]
    assert m.classifiers == [
        'Development Status :: 4 - Beta',
        'Programming Language :: Python'
    ]
    assert m.urls['homepage'] == 'example.com'
    assert m.urls['documentation'] == 'readthedocs.org'
    assert m.urls['repository'] == 'github.com/some/repo'
    assert m.urls['changelog'] == 'github.com/some/repo/blob/master/CHANGELOG.rst'
    assert m.scripts == {
        'full-metadata': 'full_metadata:main_cli',
    }
    assert m.gui_scripts == {
        'full-metadata-gui': 'full_metadata:main_gui',
    }
    assert m.entrypoints == {
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
    assert str(trampolim._build.Project()._meta.as_rfc822()) == textwrap.dedent('''
        Metadata-Version: 2.1
        Name: full-metadata
        Version: 3.2.1
        Summary: A package with all the metadata :)
        Keywords: trampolim is interesting
        Home-page: example.com
        Author: Example!
        Author-Email: Unknown <example@example.com>
        Maintainer-Email: Other Example <other@example.com>
        Classifier: Development Status :: 4 - Beta
        Classifier: Programming Language :: Python
        Project-URL: Homepage, example.com
        Project-URL: Documentation, readthedocs.org
        Project-URL: Repository, github.com/some/repo
        Project-URL: Changelog, github.com/some/repo/blob/master/CHANGELOG.rst
        Requires-Python: >=3.8
        Requires-Dist: dependency1
        Requires-Dist: dependency2>1.0.0
        Requires-Dist: dependency3[extra]
        Requires-Dist: dependency4; os_name != "nt"
        Requires-Dist: dependency5[other-extra]>1.0; os_name == "nt"
        Requires-Dist: test_dependency; extra == "test"
        Requires-Dist: test_dependency[test_extra]; extra == "test"
        Requires-Dist: test_dependency[test_extra2]>3.0; os_name == "nt" and extra == "test"
        Provides-Extra: test
        Description-Content-Type: text/markdown

        some readme
    ''').lstrip()


def test_rfc822_metadata_bytes(package_sample_source):
    assert bytes(trampolim._build.Project()._meta.as_rfc822()) == textwrap.dedent('''
        Metadata-Version: 2.1
        Name: sample-source
        Version: 0.0.0
    ''').lstrip().encode()


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
    assert trampolim._build.Project().version == packaging.version.Version('0.0.0')


def test_vcs_version_envvar(package_vcs_version1):
    os.environ['TRAMPOLIM_VCS_VERSION'] = '1.2.3'
    assert str(trampolim._build.Project().version) == '1.2.3'
    os.environ.pop('TRAMPOLIM_VCS_VERSION')


def test_vcs_version_git_archive_tag_alone(package_vcs_version1):
    assert str(trampolim._build.Project().version) == '0.0.1'


def test_vcs_version_git_archive_many_refs_tag(package_vcs_version2):
    assert str(trampolim._build.Project().version) == '0.0.2'


def test_vcs_version_git_archive_commit(package_vcs_version3):
    assert str(trampolim._build.Project().version) == '0.dev0+this.is.a.commit'


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
    assert str(trampolim._build.Project().version) == '1.0.0.23+gea1f213'


def test_vcs_no_version(mocker, package_no_version):
    mocker.patch('subprocess.check_output', side_effect=FileNotFoundError)
    with pytest.raises(trampolim.TrampolimError, match=re.escape(
        'Could not find the project version from VCS (you can set the '
        'TRAMPOLIM_VCS_VERSION environment variable to manually override the version)'
    )):
        trampolim._build.Project()


def test_vcs_custom_top_modules(mocker, package_custom_top_modules):
    assert trampolim._build.Project().root_modules == [
        'module1',
        'module2',
        'module3',
    ]


def test_vcs_test_top_module(mocker, package_test_top_level_module):
    with pytest.warns(trampolim.TrampolimWarning, match=re.escape(
        'Top-level module `test` selected, are you sure you want to install it??'
    )):
        trampolim._build.Project()


def tests_source_include(package_source_include):
    assert sorted(
        '/'.join(path.split(os.path.sep))
        for path in trampolim._build.Project().distribution_source
    ) == [
        'helper-data/a',
        'helper-data/b',
        'helper-data/c',
        'some-config.txt',
        'source_include.py',
    ]


def tests_task_extra_source(package_full_tasks):
    project = trampolim._build.Project()
    project.run_tasks()

    assert sorted(
        '/'.join(path.split(os.path.sep))
        for path in project.binary_source
    ) == [
        'example_source.py',
        'full_tasks.py',
    ]


def tests_task_extra_source_epoch(source_date_epoch, package_full_tasks):
    project = trampolim._build.Project()
    project.run_tasks()

    with project.cd_binary_source():
        st = os.stat('example_source.py')

    assert st.st_atime == st.st_mtime == 0
