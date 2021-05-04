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
