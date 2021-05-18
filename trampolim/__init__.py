# SPDX-License-Identifier: MIT

from typing import Any, Dict, List, Optional

import trampolim._build

from trampolim._build import ConfigurationError, TrampolimError, TrampolimWarning  # noqa: F401


__version__ = '0.0.2'

# get_requires


def get_requires_for_build_sdist(
    config_settings: Optional[Dict[str, Any]] = None,
) -> List[str]:
    return []


def get_requires_for_build_wheel(
    config_settings: Optional[Dict[str, Any]] = None,
) -> List[str]:
    return ['wheel']


# prepare_metadata

# def prepare_metadata_for_build_wheel(
#     metadata_directory: trampolim._build.Path,
#     config_settings: Optional[Dict[str, Any]] = None,
# ) -> str:
#     raise NotImplementedError


# build


def build_sdist(
    sdist_directory: trampolim._build.Path,
    config_settings: Optional[Dict[str, Any]] = None,
) -> str:
    project = trampolim._build.Project()
    builder = trampolim._build.SdistBuilder(project)

    builder.build(sdist_directory)
    return builder.file


def build_wheel(
    wheel_directory: trampolim._build.Path,
    config_settings: Optional[Dict[str, Any]] = None,
    metadata_directory: Optional[trampolim._build.Path] = None,
) -> str:
    import trampolim._wheel

    project = trampolim._build.Project()
    builder = trampolim._wheel.WheelBuilder(project)

    builder.build(wheel_directory)
    return builder.file
