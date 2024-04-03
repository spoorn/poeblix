# Notice: This repo is not currently actively updated to keep up with poetry releases any longer. Feel free to fork the repo or submit PRs, I'll continue to merge if so

# poeblix
Poetry Plugin that adds various features that extend the `poetry` command such as building wheel files with locked dependencies, and validations of wheel/docker containers.

Supports poetry versions `1.2+` (Note: if you are not using the latest version of poetry, you will need to check the Releases page to see which version of poeblix supports your version of poetry)

# Overview
These contain custom poetry plugins that enable functionality not available in the official distribution of poetry.  These include:

1. Using the Lock file to build a wheel file with pinned dependencies
2. Support for data_files (like with setup.py) such as jupyter extensions or font files
3. Validating a wheel file is consistent with dependencies specified in pyproject.toml/poetry.lock
4. Validating a docker container's `pip freeze` contains dependencies as specified in pyproject.toml/poetry.lock

These are not supported in Poetry due to debate in the community: https://github.com/python-poetry/poetry/issues/890, https://github.com/python-poetry/poetry/issues/4013, https://github.com/python-poetry/poetry/issues/2778

## Deterministic builds and environments

Poetry guarantees deterministic installations and environments thanks
to the `poetry.lock` file, which is where it stores the exact versions
of all the dependencies needed to install a package. However, this doesn't
occurs when wheel or package artifacts are build using `poetry build`
command.

To build a package, poetry uses the direct dependencies set in the
`pyproject.toml` and not all the other dependencies required to install
a package. For example, if `pyproject.toml` defines `pandas = "1.4.2"`
as dependency but `poetry.lock` also says that `pandas` requires of
`numpy-1.22.4`, poetry will build a package with `pandas` as dependency
but not with `numpy`.

Another problem that exists is that `pyproject.toml` can contain dependencies
with ranges of versions while `poetry.lock` has pinned versions. For instance,
if `pyproject.toml` has as dependency `pandas = ">=1.3"` but `poetry.lock`
sets `pandas-1.4.2`, poetry will build a package with the dependency
`Requires-Dist: pandas (>=0.1.3,<0.2.0)`. When the package is installed,
the resolver will install the newest package of `pandas` which its version
number is greater than or equal to `0.1.3` and lower than `0.2.0`.

Summing this up, the same python package created with `poetry build` and
installed several times won't install the same dependencies, making impossible
to have deterministic installations.

This plugin solves these problems building python packages that use the
dependencies defined in the `poetry.lock`.


# How to Use

### Prerequisite

Poetry Plugins are only supported in 1.2.0+ which, at the moment (5/29/22), can only be installed when using the [new poetry installer](https://python-poetry.org/docs/#installation)

```commandline
# You can update poetry using
poetry self update
```

## Installation

You can add the plugin via poetry's CLI:

```commandline
poetry self add poeblix
```

_For <= 1.2_:

```commandline
poetry plugin add poeblix
```

Or install directly from source/wheel, then add with the same above command using the absolute path to the built dist

To update the plugin:

```commandline
# Update to latest
poetry self add poeblix@latest

# Update to specific version
poetry self add poeblix==<version>
```

You should now see the blix* commands if you run `poetry list`

## Usage

1. To build a wheel from your package (pyproject.toml dependencies have precedence over poetry.lock ones, by default)

```commandline
poetry blixbuild

# Note: Options below are also available as part of the `blixvalidatewheel` and `blixvalidatedocker` commands

# To disable using lock file for building wheel and only use pyproject.toml
poetry blixbuild --no-lock

# Uses lock dependencies only which are pinned to exact versions, instead of pyproject.toml
poetry blixbuild --only-lock

# Specify additional dependency groups to include as Requires-Dist in the wheel
poetry blixbuild --with-groups=dev,integ,etc.
```


2. Validate a wheel file has consistent dependencies and data_files as specified in pyproject.toml/poetry.lock

```commandline
poetry blixvalidatewheel <path-to-wheel>

# Disable using lock file for validation
poetry blixvalidatewheel --no-lock <path-to-wheel>
```

_Note: this validates consistency in both directions_

3. Validate a docker container contains dependencies in a `pip freeze` as specified in pyproject.toml/poetry.lock

```commandline
poetry blixvalidatedocker <docker-container-ID>

# Disable using lock file for validation
poetry blixvalidatedocker --no-lock <docker-container-ID>
```

_Note: this only validates the docker container contains dependencies in the project, but not the other direction_

Here's an example series of commands to start up a temporary docker container using its tag, validate it, then stop the temporary container

```
# This will output the newly running container id
docker run --entrypoint=bash -it -d <docker-image-tag>

# Then validate the running docker container, and stop it when done
poetry blixvalidatedocker <container-id>
docker stop <container-id>
```

4. Adding data_files to pyproject.toml to mimic data_files in setup.py:

```yaml
...

[tool.blix.data]
data_files = [
    { destination = "share/data/", from = [ "data_files/test.txt", "data_files/anotherfile" ] },
    { destination = "share/data/threes", from = [ "data_files/athirdfile" ] }
]

...
```

data_files should be under the `[tool.blix.data]` category and is a list of objects, each containing the `destination` data folder, and a `from` list of files to add to the destination data folder.

_Note: the destination is a relative path that installs data to relative to the [installation prefix](https://docs.python.org/3/distutils/setupscript.html#installing-additional-files)_

Example: https://github.com/spoorn/poeblix/blob/main/test/positive_cases/happy_case_example/pyproject.toml

5. For more help on each command, use the --help argument

```commandline
poetry blixbuild --help
poetry blixvalidatewheel --help
poetry blixvalidatedocker --help
```

# Development

```bash
# Make a virtual environment on Python 3.9
# If using virtualenvwrapper, run `mkvirtualenv -p python3.9 venv`
virtualenv -p python3.9 venv

# Or activate existing virtualenv
# If using virtualenvwrapper, run `workon venv`
source venv/bin/activate

# installs the plugin in editable mode for easier testing via `poetry install`
./devtool bootstrap

# Lint checks
./devtool lint

# Tests
./devtool test

# Run all checks and tests
./devtool all
```

**plugins.py** : contains our plugin that adds the `poetry blixbuild` command for building our wheel file

**validatewheel.py**: adds a `poetry blixvalidatewheel` command that validates a wheel file contains the Required Dist as specified in pyproject.toml/poetry.lock

**validatedocker.py** : adds a command that validates a docker file contains dependencies as specified in pyproject.toml and poetry.lock.  This does *NOT* validate that they are exactly matching, but rather that all dependencies in pyproject.toml/poetry.lock exist in the docker container on the correct versions.  The docker image may contain more extra dependencies
