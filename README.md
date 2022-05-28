# poeblix
Poetry Plugin that adds various features deemed unfit for the official release, but makes sense to me

# Overview
These contain custom poetry plugins that enable functionality not available in the official distribution of poetry.  These include:

1. Using the Lock file to build a wheel file with pinned dependencies
2. Support for data_files (like with setup.py) such as jupyter extensions or font files

These are not supported in Poetry due to debate in the community: https://github.com/python-poetry/poetry/issues/890, https://github.com/python-poetry/poetry/issues/4013, https://github.com/python-poetry/poetry/issues/2778

# Development

```bash
mkvirtualenv -p python3.9 venv
poetry install  # installs the plugin in editable mode for easier testing
```

**plugins.py** : contains our plugin that adds the `poetry blix` command for building our wheel file

**validateplugin.py** : adds a command that validates a docker file contains dependencies as specified in pyproject.toml and poetry.lock.  This does *NOT* validate that they are exactly matching, but rather that all dependencies in pyproject.toml/poetry.lock exist in the docker container on the correct versions.  The docker image may contain more extra dependencies
