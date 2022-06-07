from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Optional, List, Dict, cast

from cleo.helpers import option
from cleo.io.inputs.option import Option

# For fixing https://github.com/python-poetry/poetry/issues/5216
from packaging.tags import sys_tags  # noqa
from poetry.console.application import Application
from poetry.console.commands.env_command import EnvCommand
from poetry.core.masonry.builders.wheel import WheelBuilder, logger
from poetry.core.poetry import Poetry
from poetry.packages import Locker
from poetry.plugins.application_plugin import ApplicationPlugin
from poetry.utils.env import Env

from poeblix.util import util

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

    def __init__(
        self,
        poetry: "Poetry",
        env: Env,
        locker: Locker,
        executable: str | Path | None = None,
        data_files: Optional[List[Dict]] = None,
        no_lock: bool = False,
    ) -> None:
        super().__init__(poetry, executable=executable)  # type: ignore
        self._env = env
        self._locker = locker
        self._data_files = data_files
        self._no_lock = no_lock

    def _get_abs_path(self, rel_path: str) -> Path:
        """Transform a relative path to absolute path"""
        abs_path = Path.joinpath(self._path, rel_path)

        if not abs_path.exists():
            raise RuntimeError(f"{abs_path} in data_files is not found.")

        if not abs_path.is_file():
            raise RuntimeError(f"{abs_path} in data_files is not a file.")

        return abs_path

    def _write_metadata(self, wheel: zipfile.ZipFile) -> None:
        """
        The below code before super()._write_metadata() takes locked dependencies from poetry.lock to add as
        requirements in the wheel file we will build.

        This can be removed if poetry supports https://github.com/python-poetry/poetry/issues/2778.
        """
        if self._no_lock:
            logger.info("Excluding lock dependencies from wheel as --no-lock was specified")
        else:
            from poetry.core.packages.dependency import Dependency

            logger.info("Adding dependencies from lock file to wheel build")
            # There is currently a bug with poetry 1.2.0b1 where the `category` field in poetry.lock all gets set to
            # "dev" for all packages.  As per https://github.com/python-poetry/poetry/issues/5702 and
            # https://github.com/python-poetry/poetry/issues/2280, the `category` field is not accurate and will be
            # removed.  Instead, we will read ALL packages from the locked repo, then during resolve_dependencies,
            # filter based on dependency group which should be used going forward 1.2.0+
            locked_repository = self._locker.locked_repository()
            # logger.info(f"locked repo {locked_repository.packages}")
            # for package in locked_repository.packages:
            #     logger.info(f"Package {package.__dict__}")
            logger.info("Resolving dependencies using poetry's solver to get rid of unneeded packages")
            ops = util.resolve_dependencies(self._poetry, self._env, locked_repository)

            # logger.info(f"dependency groups: {self._poetry.package._dependency_groups}")

            logger.info("Adding resolved dependencies to wheel METADATA")
            required_packages_names = [p.pretty_name for p in self._poetry.package.requires]
            requires_dist = self._meta.requires_dist
            logger.debug(f"Adding to Wheel Requires Dist: {ops}")
            for op in ops:
                dependency_package = op.package
                name = dependency_package.pretty_name
                version = dependency_package.version
                dep = Dependency(name, version).to_pep_508(False)
                # pyproject.toml always takes priority, then we use the lock file
                # TODO: make this configurable
                if name not in required_packages_names:
                    requires_dist.append(dep)

        super()._write_metadata(wheel)

        # After writing the metadata, also write our custom data files to the wheel data folder
        if self._data_files:
            logger.info("Adding data_files to WHEEL data folder")
            for data_file in self._data_files:
                destination = data_file["destination"]
                sources = data_file["from"]

                if Path(destination).is_absolute():
                    raise ValueError(
                        f"Destination path in data_files [{destination}] is absolute.  "
                        f"Please change it to a relative path"
                    )

                # TODO: Use OS specific separator
                if destination[-1] != "/":
                    destination += "/"

                # Note: this assumes destination is suffixed with the directory separator "/"
                for src in sources:
                    abs_path = self._get_abs_path(src)
                    self._add_file(
                        wheel,
                        abs_path,
                        Path.joinpath(Path(self.wheel_data_folder), "data", destination + abs_path.name),
                    )


class BlixBuildCommand(EnvCommand):
    """
    Our custom build command to use with the poetry CLI via `poetry blix`.
    """

    name = "blixbuild"
    description = (
        "Builds a wheel package with custom data files mimicking data_files in setup.py, and uses the lock file"
    )

    options: List[Option] = [
        option(
            "no-lock",
            None,
            "Disables building wheel file with lock dependencies.",
        )
    ]

    # Pick up Poetry's WheelBuilder logger
    loggers = ["poetry.core.masonry.builders.wheel"]

    def handle(self) -> None:
        package = self.poetry.package
        self.line(f"Building <c1>{package.pretty_name}</c1> (<c2>{package.version}</c2>)")

        # Parse data_files
        from tomlkit.exceptions import NonExistentKey

        data_files = None
        try:
            """
            Cast to dict to avoid these errors after upgrading poetry to 1.2.0b2.  It should be a dict anyways:

            src/poeblix/plugins.py:169:16: error: Unsupported right operand type for in ("Union[Any, Item, Container]")
            src/poeblix/plugins.py:170:30: error: Value of type "Union[Any, Item, Container]" is not indexable
            src/poeblix/plugins.py:181:24: error: Argument "data_files" to "BlixWheelBuilder" has incompatible type
                "Union[Any, Item, Container, None]"; expected "Optional[List[Dict[Any, Any]]]"
            """
            data_files_config = cast(dict, self.poetry.pyproject.data["tool"]["blix"]["data"])  # type: ignore
            if "data_files" in data_files_config:
                data_files = data_files_config["data_files"]
                self.line(f"Adding data_files={data_files}")
        except NonExistentKey:
            self.line(f"[tool.blix.data] section not found in {self.poetry.file}, no data_files to process")

        # Create our custom wheel builder
        builder = BlixWheelBuilder(
            self.poetry,
            env=self.env,
            locker=self.poetry.locker,
            executable=self.env.python,
            data_files=data_files,
            no_lock=self.option("no-lock"),
        )
        builder.build()


class BlixPlugin(ApplicationPlugin):
    def activate(self, application: Application) -> None:
        # Custom build command via `poetry blix`
        application.command_loader.register_factory(BlixBuildCommand.name, lambda: BlixBuildCommand())

        # Validate Wheel plugin
        from .validatewheel import ValidateWheelPlugin

        application.command_loader.register_factory(ValidateWheelPlugin.name, lambda: ValidateWheelPlugin())

        # Validate Docker plugin
        from .validatedocker import ValidateDockerPlugin

        application.command_loader.register_factory(ValidateDockerPlugin.name, lambda: ValidateDockerPlugin())
