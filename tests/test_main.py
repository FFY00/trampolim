# SPDX-License-Identifier: MIT

import os
import pathlib
import shutil
import sys
import tarfile

import pytest
import wheel.wheelfile

import trampolim.__main__

from .conftest import cd_package, package_dir


@pytest.fixture()
def package(tmpdir):
    if sys.version_info >= (3, 8):
        shutil.copytree(package_dir / 'file-module', tmpdir, dirs_exist_ok=True)
    else:
        import distutils.dir_util

        distutils.dir_util.copy_tree(str(package_dir / 'file-module'), str(tmpdir))
    with cd_package(tmpdir):
        yield


def test_entrypoint(package):
    prev = sys.argv
    sys.argv = ['something', 'build']
    try:
        trampolim.__main__.entrypoint()
    finally:
        sys.argv = prev

    dist = pathlib.Path('dist')
    t = tarfile.open(dist / 'file-module-0.0.0.tar.gz', 'r')

    with open('pyproject.toml', 'rb') as f:
        assert f.read() == t.extractfile('file-module-0.0.0/pyproject.toml').read()

    with wheel.wheelfile.WheelFile(dist / 'file_module-0.0.0-py3-none-any.whl', 'r') as w:
        assert 'file_module-0.0.0.dist-info/WHEEL' in w.namelist()


def test_build_no_args(package):
    trampolim.__main__.main(['build'], 'something')

    dist = pathlib.Path('dist')
    t = tarfile.open(dist / 'file-module-0.0.0.tar.gz', 'r')

    with open('pyproject.toml', 'rb') as f:
        assert f.read() == t.extractfile('file-module-0.0.0/pyproject.toml').read()

    with wheel.wheelfile.WheelFile(dist / 'file_module-0.0.0-py3-none-any.whl', 'r') as w:
        assert 'file_module-0.0.0.dist-info/WHEEL' in w.namelist()


def test_build_custom_outdir(package):
    dist = pathlib.Path('some') / 'place'

    trampolim.__main__.main(['build', str(dist)], 'something')

    t = tarfile.open(dist / 'file-module-0.0.0.tar.gz', 'r')

    with open('pyproject.toml', 'rb') as f:
        assert f.read() == t.extractfile('file-module-0.0.0/pyproject.toml').read()

    with wheel.wheelfile.WheelFile(dist / 'file_module-0.0.0-py3-none-any.whl', 'r') as w:
        assert 'file_module-0.0.0.dist-info/WHEEL' in w.namelist()


def test_build_outdir_notdir(package, capsys):
    pathlib.Path('dist').touch()

    with pytest.raises(SystemExit):
        trampolim.__main__.main(['build'], 'something')

    assert capsys.readouterr().err == 'ERROR Output path `dist` exists and is not a directory!\n'


def test_build_only_sdist(package):
    trampolim.__main__.main(['build', '-s'], 'something')

    assert os.listdir('dist') == ['file-module-0.0.0.tar.gz']


def test_build_only_wheel(package):
    trampolim.__main__.main(['build', '-w'], 'something')

    assert os.listdir('dist') == ['file_module-0.0.0-py3-none-any.whl']
