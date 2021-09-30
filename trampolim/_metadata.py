# SPDX-License-Identifier: MIT

from __future__ import annotations

import dataclasses

from typing import Any, List, Mapping

import pep621


@dataclasses.dataclass
class TrampolimMetadata():
    top_level_modules: List[str]
    source_include: List[str]

    @classmethod
    def from_pyproject(cls, data: Mapping[str, Any]) -> TrampolimMetadata:
        fetcher = pep621.DataFetcher(data)
        return cls(
            fetcher.get_list('tool.trampolim.top-level-modules'),
            fetcher.get_list('tool.trampolim.source-include'),
        )
