# SPDX-License-Identifier: MIT

import re

import pytest

import trampolim._build


def test_invalid_parameter(package_invalid_parameter_task):
    with pytest.raises(trampolim._build.TrampolimError, match=re.escape(
        'Task `invalid_parameters` has unknown parameter `this_is_not_a_valid_parameter`'
    )):
        trampolim._build.Project()
