# SPDX-License-Identifier: MIT

import os.path
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
