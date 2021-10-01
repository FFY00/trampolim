from __future__ import annotations

import os

import nox


nox.options.sessions = ['lint', 'type', 'tests']


@nox.session(reuse_venv=True)
def lint(session):
    """
    Run the linter.
    """
    session.install('pre-commit')
    session.run('pre-commit', 'run', '--all-files', *session.posargs)


@nox.session(python=['3.7', '3.8', '3.9'], reuse_venv=True)
def test(session):
    """
    Run the unit and regular tests.
    """

    htmlcov_output = os.path.join(session.virtualenv.location, 'htmlcov')
    xmlcov_output = os.path.join(session.virtualenv.location, f'coverage-{session.python}.xml')

    session.install(
        'tomli',
        'packaging',
        'rich',
        'wheel',
        'pytest',
        'pytest-cov',
        'pytest-mock',
        'backports.cached-property',
        'pep621',
    )

    session.run(
        'pytest', '--cov', '--cov-config', 'setup.cfg',
        f'--cov-report=html:{htmlcov_output}',
        f'--cov-report=xml:{xmlcov_output}',
        '--showlocals',
        '-vv',
        '--durations=1',
        'tests/', *session.posargs
    )


@nox.session(reuse_venv=True)
def type(session):
    session.install('mypy', 'packaging', 'tomli', 'rich', 'backports.cached_property')
    session.run('mypy', '--python-version=3.7', '--package=trampolim', *session.posargs)
    session.run('mypy', '--python-version=3.9', '--package=trampolim', *session.posargs)


@nox.session(reuse_venv=True)
def docs(session):
    """
    Build the docs. Pass "serve" to serve.
    """

    session.install('.[docs]')
    session.chdir('docs')
    session.run('sphinx-build', '-M', 'html', '.', '_build')

    if session.posargs:
        if 'serve' in session.posargs:
            print('Launching docs at http://localhost:8000/ - use Ctrl-C to quit')
            session.run('python', '-m', 'http.server', '8000', '-d', '_build/html')
        else:
            print('Unsupported argument to docs')


@nox.session
def build(session):
    """
    Build an SDist and wheel.
    """

    session.install('build')
    session.run('python', '-m', 'build', *session.posargs)
