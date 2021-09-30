# SPDX-License-Identifier: MIT

import collections
import dataclasses

import pep621

import trampolim._metadata

from trampolim._tasks import Session


FrozenMetadata = collections.namedtuple('FrozenMetadata', [  # type: ignore[misc]
    field.name
    for cls in (pep621.StandardMetadata, trampolim._metadata.TrampolimMetadata)
    for field in dataclasses.fields(cls)
])


__all__ = [
    'FrozenMetadata',
    'Session',
]
