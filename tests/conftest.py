# SPDX-License-Identifier: MIT

import contextlib
import os
import pathlib

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


@pytest.fixture
def source_date_epoch():
    old_val = os.environ.get('SOURCE_DATE_EPOCH')
    os.environ['SOURCE_DATE_EPOCH'] = '0'
    try:
        yield
    finally:  # pragma: no cover
        if old_val is not None:
            os.environ['SOURCE_DATE_EPOCH'] = old_val
        else:
            del os.environ['SOURCE_DATE_EPOCH']


def generate_package_fixture(package):
    @pytest.fixture
    def fixture():
        with cd_package(package) as new_path:
            yield new_path
    return fixture


def generate_sdist_fixture(package):
    @pytest.fixture(scope='session')
    def fixture(tmp_path_factory):
        tmp_path_sdist = tmp_path_factory.mktemp('sdist_package')
        with cd_package(package):
            return tmp_path_sdist / trampolim.build_sdist(tmp_path_sdist)
    return fixture


def generate_wheel_fixture(package):
    @pytest.fixture(scope='session')
    def fixture(tmp_path_factory):
        tmp_path_wheel = tmp_path_factory.mktemp('wheel_package')
        with cd_package(package):
            return tmp_path_wheel / trampolim.build_wheel(tmp_path_wheel)
    return fixture


# inject {package,sdist,wheel}_* fixtures (https://github.com/pytest-dev/pytest/issues/2424)
for package in os.listdir(package_dir):
    normalized = package.replace('-', '_')
    globals()[f'package_{normalized}'] = generate_package_fixture(package)
    globals()[f'sdist_{normalized}'] = generate_sdist_fixture(package)
    globals()[f'wheel_{normalized}'] = generate_wheel_fixture(package)
