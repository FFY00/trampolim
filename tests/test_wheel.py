# SPDX-License-Identifier: MIT

import os.path
import tarfile
import textwrap

import wheel.wheelfile

import trampolim
import trampolim._build
import trampolim._wheel


def test_name(package_full_metadata):
    assert (
        trampolim._wheel.WheelBuilder(trampolim._build.Project()).name
        == 'full_metadata-3.2.1-py3-none-any'
    )


def test_wheel_info(wheel_full_metadata):
    with wheel.wheelfile.WheelFile(wheel_full_metadata, 'r') as w:
        data = w.read('full_metadata-3.2.1.dist-info/WHEEL')
        assert data == textwrap.dedent(f'''
            Wheel-Version: 1.0
            Generator: trampolim {trampolim.__version__}
            Root-Is-Purelib: true
            Tag: py3-none-any
        ''').strip().encode()


def test_entrypoints(wheel_full_metadata):
    with wheel.wheelfile.WheelFile(wheel_full_metadata, 'r') as w:
        data = w.read('full_metadata-3.2.1.dist-info/entrypoints.txt')
        assert data == textwrap.dedent('''
            [custom]
            full-metadata = full_metadata:main_custom

            [console_scripts]
            full-metadata = full_metadata:main_cli

            [gui_scripts]
            full-metadata-gui = full_metadata:main_gui

        ''').lstrip().encode()


def test_source(package_sample_source, wheel_sample_source):
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
    with wheel.wheelfile.WheelFile(wheel_sample_source, 'r') as w:
        for file in expected_source:
            with open(os.path.join(*file.split('/')), 'rb') as f:
                assert f.read() == w.read(file)


def test_src_layout(package_src_layout, wheel_src_layout):
    with wheel.wheelfile.WheelFile(wheel_src_layout) as w:
        assert set(w.namelist()) == {
            'src_layout-0.0.0.dist-info/METADATA',
            'src_layout-0.0.0.dist-info/RECORD',
            'src_layout-0.0.0.dist-info/WHEEL',
            'src_layout/__init__.py',
            'src_layout/a.py',
            'src_layout/b.py',
            'src_layout/c.py',
            'src_layout/d/__init__.py',
        }


def test_overwrite_version(monkeypatch, package_no_version, tmp_path):
    monkeypatch.setenv('TRAMPOLIM_VCS_VERSION', '1.0.0+custom')

    with wheel.wheelfile.WheelFile(tmp_path / trampolim.build_wheel(tmp_path), 'r') as w:
        metadata = w.read('no_version-1.0.0+custom.dist-info/METADATA').decode()
    assert metadata == textwrap.dedent('''
        Metadata-Version: 2.1
        Name: no-version
        Version: 1.0.0+custom
    ''').lstrip()


def test_build_via_sdist(monkeypatch, package_no_version, tmp_path):
    monkeypatch.setenv('TRAMPOLIM_VCS_VERSION', '1.0.0+custom')

    sdist_file = tmp_path / trampolim.build_sdist(tmp_path)
    with tarfile.open(sdist_file) as t:
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(t, tmp_path)

    monkeypatch.delenv('TRAMPOLIM_VCS_VERSION')

    monkeypatch.chdir(tmp_path / sdist_file.name[:-len('.tar.gz')])
    wheel_file = tmp_path / trampolim.build_wheel(tmp_path)
    with wheel.wheelfile.WheelFile(wheel_file) as w:
        metadata = w.read('no_version-1.0.0+custom.dist-info/METADATA').decode()

    assert metadata == textwrap.dedent('''
        Metadata-Version: 2.1
        Name: no-version
        Version: 1.0.0+custom
    ''').lstrip()
