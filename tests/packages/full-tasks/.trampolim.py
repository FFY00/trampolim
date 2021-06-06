# SPDX-License-Identifier: MIT

import trampolim


@trampolim.task
def no_parameters():
    pass


@trampolim.task
def receives_session(session):
    pass


@trampolim.task
def inject_some_file(session):
    with open('example_source.py', 'w') as f:
        f.write('# Example!')

    session.extra_source += [
        'example_source.py',
    ]
