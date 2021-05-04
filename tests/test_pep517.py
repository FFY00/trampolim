# SPDX-License-Identifier: MIT

import trampolim


def test_get_requires_for_build_sdist(package_sample_source):
    assert trampolim.get_requires_for_build_sdist() == []


def test_get_requires_for_build_wheel(package_sample_source):
    assert trampolim.get_requires_for_build_wheel() == ['wheel']
