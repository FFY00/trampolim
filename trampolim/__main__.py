# SPDX-License-Identifier: MIT

import argparse
import os
import os.path
import sys
import warnings

from typing import Iterable, List, Optional, TextIO, Type, Union

import rich
import rich.traceback

import trampolim


def _showwarning(
    message: Union[Warning, str],
    category: Type[Warning],
    filename: str,
    lineno: int,
    file: Optional[TextIO] = None,
    line: Optional[str] = None,
) -> None:  # pragma: no cover
    rich.print(f'[bold orange]WARNING[/bold orange] {str(message)}')


warnings.showwarning = _showwarning


def _error(msg: str, code: int = 1) -> None:  # pragma: no cover
    '''Print an error message and exit.'''
    rich.print(f'[bold red]ERROR[/bold red] {msg}', file=sys.stderr)
    exit(code)


def main_parser(prog: str) -> argparse.ArgumentParser:
    '''Construct the main parser.'''
    # mypy does not recognize module.__path__
    # https://github.com/python/mypy/issues/1422
    paths: Iterable[Optional[str]] = trampolim.__path__  # type: ignore
    parser = argparse.ArgumentParser()
    parser.prog = prog
    parser.add_argument(
        '--version',
        '-V',
        action='version',
        version='trampolim {} ({})'.format(
            trampolim.__version__,
            ', '.join(path for path in paths if path)
        ),
    )
    subparsers = parser.add_subparsers(
        dest='command',
        title='subcommands',
        required=True,
    )

    # build subcommand
    build_parser = subparsers.add_parser(
        'build',
        description='build package distributions',
    )
    build_parser.prog = prog
    build_parser.add_argument(
        'outdir',
        type=str,
        nargs='?',
        default='dist',
        help='output directory (defaults to `dist`)',
    )
    build_parser.add_argument(
        '--sdist',
        '-s',
        action='store_true',
        help='build a source distribution (enabled by default if no target is specified)',
    )
    build_parser.add_argument(
        '--wheel',
        '-w',
        action='store_true',
        help='build a wheel (enabled by default if no target is specified)',
    )

    '''
    # publish subcommand
    publish_parser = subparsers.add_parser(
        'publish',
        description='publish package distributions',
    )
    publish_parser.prog = prog

    # check subcommand
    check_parser = subparsers.add_parser(
        'check',
        description='check the project for issues',
    )
    check_parser.prog = prog
    '''

    return parser


def main_task(cli_args: List[str], prog: str) -> None:
    '''Parse the CLI arguments and invoke the build process.'''
    parser = main_parser(prog)
    args = parser.parse_args(cli_args)

    if args.command == 'build':
        if not args.sdist and not args.wheel:
            args.sdist = True
            args.wheel = True

        if os.path.exists(args.outdir):
            if not os.path.isdir(args.outdir):
                _error(f'Output path `{args.outdir}` exists and is not a directory!')
        else:
            os.makedirs(args.outdir)

        if args.sdist:
            trampolim.build_sdist(args.outdir)
        if args.wheel:
            trampolim.build_wheel(args.outdir)


def main(cli_args: List[str], prog: str) -> None:
    try:
        main_task(cli_args, prog)
    except Exception:  # pragma: no cover
        exc_type, exc_value, tb = sys.exc_info()
        assert exc_type and exc_value
        rich.print(rich.traceback.Traceback.from_exception(
            exc_type,
            exc_value,
            tb.tb_next if tb else tb,
        ))


def entrypoint() -> None:
    main(sys.argv[1:], sys.argv[0])


if __name__ == '__main__':  # pragma: no cover
    try:
        main(sys.argv[1:], 'python -m trampolim')
    except KeyboardInterrupt:
        rich.print('Exiting...')
