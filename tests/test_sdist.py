# SPDX-License-Identifier: MIT

import tarfile

import trampolim._build


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


def test_source(package_sample_source, sdist_sample_source):
    t = tarfile.open(sdist_sample_source, 'r')

    expected_source = [
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
    ]

    for file in expected_source:
        assert file in t.getnames()


def test_pkginfo(package_license_text, sdist_license_text):
    p = trampolim._build.Project()
    t = tarfile.open(sdist_license_text, 'r')

    assert t.extractfile('license-text-0.0.0/PKG-INFO').read() == p.metadata.as_bytes()
