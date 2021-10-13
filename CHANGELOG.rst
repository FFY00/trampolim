+++++++++
Changelog
+++++++++


0.1.0 (13-10-2021)
==================

- Fix dynamic version when building from sdist (`PR #20`_, Fixes ` #4`_)
- Add ``module-location`` option, allowing ``src``-layout (`PR #15`_, Fixes ` #3`_)

.. _PR #15: https://github.com/FFY00/trampolim/pull/15
.. _PR #15: https://github.com/FFY00/trampolim/pull/20
.. _#3: https://github.com/FFY00/trampolim/issues/3
.. _#3: https://github.com/FFY00/trampolim/issues/4


0.0.4 (30-09-2021)
==================

- Use TOML 1.0 compliant parser (`PR #11`_)
- Fix incorrect files being included in wheels

.. _PR #11: https://github.com/FFY00/trampolim/pull/11



0.0.3 (06-06-2021)
==================

- Add task system (`PR #1`_, `PR #2`_)
- Add ``source-include`` setting

.. _PR #1: https://github.com/FFY00/trampolim/pull/1
.. _PR #2: https://github.com/FFY00/trampolim/pull/2



0.0.2 (18-05-2021)
==================

- Add cli with a build command
- Add ``top-level-modules`` setting


0.0.1 (06-05-2021)
==================

Initial release

- Implemented PEP 517 hooks
- Implemented PEP 621 pyproject.toml metadata parsing
- Implemented automated version from git repos and archives
