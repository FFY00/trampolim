# SPDX-License-Identifier: MIT

import re
import textwrap

import pep621
import pytest
import tomli

import trampolim
import trampolim._metadata


@pytest.mark.parametrize(
    ('data', 'error'),
    [
        (
            textwrap.dedent('''
                [tool.trampolim]
                top-level-modules = true
            '''),
            ('Field `tool.trampolim.top-level-modules` has an invalid type, expecting a list of strings (got `True`)'),
        ),
        (
            textwrap.dedent('''
                [tool.trampolim]
                source-include = 0
            '''),
            ('Field `tool.trampolim.source-include` has an invalid type, expecting a list of strings (got `0`)'),
        ),
    ],
)
def test_trampolim_metadata(package_full_metadata, data, error):
    with pytest.raises(pep621.ConfigurationError, match=re.escape(error)):
        trampolim._metadata.TrampolimMetadata.from_pyproject(tomli.loads(data))
