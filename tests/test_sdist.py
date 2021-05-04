# SPDX-License-Identifier: MIT

import tarfile


def test_pyproject(package_license_file, sdist_license_file):
    t = tarfile.open(sdist_license_file, 'r')

    data = t.extractfile('pyproject.toml')

    with open(package_license_file / 'pyproject.toml', 'rb') as f:
        assert f.read() == data.read()


def test_license_file(package_license_file, sdist_license_file):
    t = tarfile.open(sdist_license_file, 'r')

    assert 'LICENSE' in t.getnames()

    data = t.extractfile('LICENSE')

    with open(package_license_file / 'LICENSE', 'rb') as f:
        assert f.read() == data.read()


def test_license_text(package_license_text, sdist_license_text):
    t = tarfile.open(sdist_license_text, 'r')

    assert t.extractfile('LICENSE').read() == 'inline license!'.encode()


def test_source(package_sample_source, sdist_sample_source):
    t = tarfile.open(sdist_sample_source, 'r')

    expected_source = [
        'sample_source/e/eb.py',
        'sample_source/e/ea.py',
        'sample_source/e/ec/ecc.py',
        'sample_source/e/ec/eca.py',
        'sample_source/e/ec/ecb.py',
        'sample_source/a.py',
        'sample_source/c.py',
        'sample_source/d/db.py',
        'sample_source/d/da.py',
        'sample_source/b.py',
        'sample_source/f/fc/fcb.py',
        'sample_source/f/fc/fca.py',
        'sample_source/f/fc/fcc.py',
        'sample_source/f/fc/fcc/fcca.py',
        'sample_source/f/fc/fcd/fcda.py',
        'sample_source/f/fc/fcd/fcdb.py',
        'sample_source/f/fb.py',
        'sample_source/f/fa.py',
    ]

    for file in expected_source:
        assert file in t.getnames()
