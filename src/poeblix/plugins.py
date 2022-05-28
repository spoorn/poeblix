from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Optional, List, Dict, Sequence

# For fixing https://github.com/python-poetry/poetry/issues/5216
from packaging.tags import sys_tags  # noqa

from poetry.console.application import Application
from poetry.console.commands.env_command import EnvCommand
from poetry.core.masonry.builders.wheel import WheelBuilder
from poetry.core.poetry import Poetry
from poetry.installation.operations.operation import Operation
from poetry.packages import Locker
from poetry.plugins.application_plugin import ApplicationPlugin
from poetry.repositories import Repository
from poetry.utils.env import Env

"""
This Plugin introduces a new command `poetry blix` that extends upon the regular `poetry build` command, 
but allows for building the wheel file using the poetry.lock file and supports adding data_files just like in setup.py:  
https://docs.python.org/3/distutils/setupscript.html#installing-additional-files
"""

class BlixWheelBuilder(WheelBuilder):
    """
    This extends on Poetry's wheel builder which is invoked via `poetry build -f wheel`.  Adds features such as
    supporting data_files in the wheel archive, and using the lock file to pin dependencies in the wheel.

    These features are not supported in the official Poetry commands as they have either been deemed by the community
    as not commonly necessary, or not yet implemented.

    For example, data_files are deprecated even in setup.py: https://github.com/python-poetry/poetry/issues/890
    Using lock file to build the wheel: https://github.com/python-poetry/poetry/issues/2778
    """

    def __init__(self, poetry: "Poetry", env: Env, locker: Locker, executable: Optional[str] = None, data_files: Optional[List[Dict]] = None) -> None:
        super().__init__(poetry, executable=executable)
        self._env = env
        self._locker = locker
        self._data_files = data_files


class BlixBuildCommand(EnvCommand):
    """
    Our custom build command to use with the poetry CLI via `poetry blix`.
    """

    name = "blix"
    description = (
        "Builds a wheel package with custom data files mimicking data_files in setup.py, and uses the lock file"
    )

    options = []

    # Pick up Poetry's WheelBuilder logger
    loggers = ["poetry.core.masonry.builders.wheel"]

    def handle(self) -> None:
        pass


class BlixPlugin(ApplicationPlugin):
    def activate(self, application: Application) -> None:
        # Custom build command via `poetry blix`
        application.command_loader.register_factory(BlixBuildCommand.name, lambda: BlixBuildCommand())

        # TODO: Add validateplugin
