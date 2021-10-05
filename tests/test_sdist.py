# SPDX-License-Identifier: MIT

import pathlib
import tarfile
import textwrap

import trampolim._build


def assert_contents(archive, name, expected_source):
    for file in expected_source:
        f = pathlib.Path(*file[len(name):].split('/'))
        assert f.read_bytes() == archive.extractfile(file).read()


def test_pyproject(package_license_file, sdist_license_file):
    t = tarfile.open(sdist_license_file, 'r')

    data = t.extractfile('license-file-0.0.0/pyproject.toml')

    with open(package_license_file / 'pyproject.toml', 'rb') as f:
        assert f.read() == data.read()


def test_license_file(package_license_file, sdist_license_file):
    t = tarfile.open(sdist_license_file, 'r')

    assert 'license-file-0.0.0/some-license-file' in t.getnames()

    data = t.extractfile('license-file-0.0.0/some-license-file')

    with open(package_license_file / 'some-license-file', 'rb') as f:
        assert f.read() == data.read()


def test_license_text(package_license_text, sdist_license_text):
    t = tarfile.open(sdist_license_text, 'r')

    assert t.extractfile('license-text-0.0.0/LICENSE').read() == 'inline license!'.encode()


def test_readme_file(package_readme_md, sdist_readme_md):
    t = tarfile.open(sdist_readme_md, 'r')

    data = t.extractfile('readme-md-1.0.0/README.md')

    with open(package_readme_md / 'README.md', 'rb') as f:
        assert f.read() == data.read()


def test_source(package_sample_source, sdist_sample_source):
    t = tarfile.open(sdist_sample_source, 'r')

    assert_contents(
        t,
        'sample-source-0.0.0',
        [
            'sample-source-0.0.0/pyproject.toml',
            'sample-source-0.0.0/sample_source/e/eb.py',
            'sample-source-0.0.0/sample_source/e/ea.py',
            'sample-source-0.0.0/sample_source/e/ec/ecc.py',
            'sample-source-0.0.0/sample_source/e/ec/eca.py',
            'sample-source-0.0.0/sample_source/e/ec/ecb.py',
            'sample-source-0.0.0/sample_source/a.py',
            'sample-source-0.0.0/sample_source/c.py',
            'sample-source-0.0.0/sample_source/d/db.py',
            'sample-source-0.0.0/sample_source/d/da.py',
            'sample-source-0.0.0/sample_source/b.py',
            'sample-source-0.0.0/sample_source/f/fc/fcb.py',
            'sample-source-0.0.0/sample_source/f/fc/fca.py',
            'sample-source-0.0.0/sample_source/f/fc/fcc.py',
            'sample-source-0.0.0/sample_source/f/fc/fcc/fcca.py',
            'sample-source-0.0.0/sample_source/f/fc/fcd/fcda.py',
            'sample-source-0.0.0/sample_source/f/fc/fcd/fcdb.py',
            'sample-source-0.0.0/sample_source/f/fb.py',
            'sample-source-0.0.0/sample_source/f/fa.py',
        ],
    )


def test_pkginfo(package_license_text, sdist_license_text):
    p = trampolim._build.Project()
    t = tarfile.open(sdist_license_text, 'r')

    assert t.extractfile('license-text-0.0.0/PKG-INFO').read() == bytes(p._meta.as_rfc822())


def tests_source_include(package_source_include, sdist_source_include):
    t = tarfile.open(sdist_source_include, 'r')

    assert_contents(
        t,
        'source-include-0.0.0',
        [
            'source-include-0.0.0/pyproject.toml',
            'source-include-0.0.0/helper-data/a',
            'source-include-0.0.0/helper-data/b',
            'source-include-0.0.0/helper-data/c',
            'source-include-0.0.0/some-config.txt',
            'source-include-0.0.0/source_include.py',
        ],
    )


def tests_src_layout(package_src_layout, sdist_src_layout):
    t = tarfile.open(sdist_src_layout, 'r')

    assert_contents(
        t,
        'src-layout-0.0.0',
        [
            'src-layout-0.0.0/src/src_layout/d/__init__.py',
            'src-layout-0.0.0/src/src_layout/b.py',
            'src-layout-0.0.0/src/src_layout/__init__.py',
            'src-layout-0.0.0/pyproject.toml',
            'src-layout-0.0.0/src/src_layout/c.py',
            'src-layout-0.0.0/src/src_layout/a.py',
        ],
    )


def test_overwrite_version(monkeypatch, package_no_version, tmp_dir):
    monkeypatch.setenv('TRAMPOLIM_VCS_VERSION', '1.0.0+custom')

    t = tarfile.open(tmp_dir / trampolim.build_sdist(tmp_dir), 'r')
    pkginfo = t.extractfile('no-version-1.0.0+custom/PKG-INFO').read().decode()
    assert pkginfo == textwrap.dedent('''
        Metadata-Version: 2.1
        Name: no-version
        Version: 1.0.0+custom
    ''').lstrip()
