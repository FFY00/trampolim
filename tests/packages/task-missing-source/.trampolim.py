# SPDX-License-Identifier: MIT

import shutil

import trampolim


@trampolim.task
def inject_some_file(session):
    shutil.copy2(
        session.source_path / 'example_source.py',
        'example_source.py',
    )

    # session.extra_source += [
    #     'example_source.py',
    # ]
