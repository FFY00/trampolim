# SPDX-License-Identifier: MIT

from __future__ import annotations

import inspect
import pathlib

from typing import Callable, List

import trampolim._build


class Session():
    '''Task running session.

    Provices access to information about the project and allows changing some
    aspects of it.
    '''
    def __init__(self, project: trampolim._build.Project) -> None:
        self._project = project

        self.extra_source: List[str] = []

    @property
    def source_path(self) -> pathlib.Path:
        return pathlib.Path(self._project._dist_srcpath)


class Task():
    _SUPPORTED_PARAMS = (
        'session',
    )

    def __init__(self, name: str, call: Callable[..., None]) -> None:
        self._name = name
        self._set_callable(call)

    def _set_callable(self, call: Callable[..., None]) -> None:
        '''Set and validate the task callable.'''
        self._callable = call
        self._params = inspect.signature(self._callable).parameters

        for param in self._params:
            if param not in self._SUPPORTED_PARAMS:
                raise trampolim._build.TrampolimError(
                    f'Task `{self.name}` has unknown parameter `{param}`'
                )

    def run(self, session: Session) -> None:
        '''Run the task in a given session.'''
        kwargs = {
            'session': session,
        }
        self._callable(**{
            arg: val for arg, val in kwargs.items()
            if arg in self._params
        })

    @property
    def name(self) -> str:
        '''Task name.'''
        return self._name


def task(func: Callable[..., None]) -> Task:
    '''Decorator that marks a function as a task.'''
    return Task(func.__name__, func)
