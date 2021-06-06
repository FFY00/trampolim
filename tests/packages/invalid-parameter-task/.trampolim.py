# SPDX-License-Identifier: MIT

import trampolim


@trampolim.task
def invalid_parameters(this_is_not_a_valid_parameter):
    pass  # pragma: no cover
