# SPDX-License-Identifier: MIT

import contextlib
import os
import pathlib
import shutil
import tempfile

import pytest

import trampolim


package_dir = pathlib.Path(__file__).parent / 'packages'


@contextlib.contextmanager
def cd_package(package):
    cur_dir = os.getcwd()
    package_path = package_dir / package
    os.chdir(package_path)
    try:
        yield package_path
    finally:
        os.chdir(cur_dir)


'''
@pytest.fixture
def tmp_dir():
    path = tempfile.mkdtemp(prefix='python-build-test-')

    try:
        yield pathlib.Path(path)
    finally:
        shutil.rmtree(path)
'''


@pytest.fixture(scope='session')
def tmp_dir_session():
    path = tempfile.mkdtemp(prefix='python-build-test-')

    try:
        yield pathlib.Path(path)
    finally:
        try:
            shutil.rmtree(path)
        except PermissionError:  # pragma: no cover
            pass  # this sometimes fails on windows :/


def generate_package_fixture(package):
    @pytest.fixture
    def fixture():
        with cd_package(package) as new_path:
            yield new_path
    return fixture


def generate_sdist_fixture(package, package_fixture):
    @pytest.fixture(scope='session')
    def fixture(tmp_dir_session):
        with cd_package(package):
            return tmp_dir_session / trampolim.build_sdist(tmp_dir_session)
    return fixture


'''
def generate_wheel_fixture(package, package_fixture):
    @pytest.fixture(scope='session')
    def fixture(tmp_dir_session):
        with cd_package(package):
            return tmp_dir_session / trampolim.build_sdist(tmp_dir_session)
    return fixture
'''


# inject {package,sdist,wheel}_* fixtures (https://github.com/pytest-dev/pytest/issues/2424)
for package in os.listdir(package_dir):
    normalized = package.replace('-', '_')
    fixture = f'package_{normalized}'
    globals()[fixture] = generate_package_fixture(package)
    globals()[f'sdist_{normalized}'] = generate_sdist_fixture(package, fixture)
    # globals()[f'wheel_{normalized}'] = generate_wheel_fixture(package, fixture)
