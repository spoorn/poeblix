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

    def __init__(
        self,
        poetry: "Poetry",
        env: Env,
        locker: Locker,
        executable: Optional[str] = None,
        data_files: Optional[List[Dict]] = None,
    ) -> None:
        super().__init__(poetry, executable=executable)
        self._env = env
        self._locker = locker
        self._data_files = data_files

    def _get_abs_path(self, rel_path: str) -> Path:
        """Transform a relative path to absolute path"""
        abs_path = Path.joinpath(self._path, rel_path)

        if not abs_path.exists():
            raise RuntimeError(f"{abs_path} in data_files is not found.")

        if not abs_path.is_file():
            raise RuntimeError(f"{abs_path} in data_files is not a file.")

        return abs_path

    def resolve_dependencies(self, locked_repository: Repository) -> Sequence[Operation]:
        """
        This uses poetry's solver to resolve dependencies and filters out packages from the lock file which are not
        needed, such as packages that are not for our OS environment using markers (e.g. pywin32 is for Windows).
        """
        # Making a new repo containing the packages
        # newly resolved and the ones from the current lock file
        repo = Repository()
        for package in locked_repository.packages:
            if not repo.has_package(package):
                repo.add_package(package)

        from poetry.repositories import Pool

        pool = Pool(ignore_repository_names=True)
        pool.add_repository(repo)

        from poetry.puzzle import Solver
        from cleo.io.null_io import NullIO

        # Run through poetry's dependency resolver.  Only uses the default `dependencies` in pyproject.toml, not
        # dev dependencies or other groups.  If we want to support more groups in the wheel file, we can expand on the
        # CLI with more options.
        # See https://github.com/python-poetry/poetry/blob/master/src/poetry/installation/installer.py#L34 for poetry's
        # usage of this
        from poetry.repositories.installed_repository import InstalledRepository

        solver = Solver(
            self._poetry.package.with_dependency_groups(groups=["default"], only=True),
            pool,
            InstalledRepository.load(self._env),
            locked_repository,
            NullIO(),
        )

        # Everything is resolved at this point, so we no longer need
        # to load deferred dependencies (i.e. VCS, URL and path dependencies)
        solver.provider.load_deferred(False)

        with solver.use_environment(self._env):
            ops = solver.solve(use_latest=[]).calculate_operations(
                with_uninstalls=False,
                synchronize=False,
            )
        return ops

    def _write_metadata(self, wheel: zipfile.ZipFile) -> None:
        """
        The below code before super()._write_metadata() takes locked dependencies from poetry.lock to add as
        requirements in the wheel file we will build.

        This can be removed if poetry supports https://github.com/python-poetry/poetry/issues/2778.
        """
        from poetry.core.masonry.builders.wheel import logger
        from poetry.core.packages.dependency import Dependency

        # TODO: Make using lock file configurable
        logger.info("Adding dependencies from lock file to wheel build")
        locked_repository = self._locker.locked_repository()
        logger.info("Resolving dependencies using poetry's solver to get rid of unneeded packages")
        ops = self.resolve_dependencies(locked_repository)

        logger.info("Adding resolved dependencies to wheel METADATA")
        required_packages_names = [p.pretty_name for p in self._poetry.package.requires]
        requires_dist = self._meta.requires_dist
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

                if destination[0] != "/":
                    raise ValueError(
                        f"Destination path in data_files [{destination}] should be prefixed with a directory separator "
                        f"'/'"
                    )

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

    name = "blix"
    description = (
        "Builds a wheel package with custom data files mimicking data_files in setup.py, and uses the lock file"
    )

    options = []

    # Pick up Poetry's WheelBuilder logger
    loggers = ["poetry.core.masonry.builders.wheel"]

    def handle(self) -> None:
        package = self.poetry.package
        self.line(f"Building <c1>{package.pretty_name}</c1> (<c2>{package.version}</c2>)")

        # Parse data_files
        from tomlkit.exceptions import NonExistentKey

        try:
            data_files_config = self.poetry.pyproject.data["tool"]["blix"]["data"]
        except NonExistentKey as e:
            from poetry.core.pyproject.exceptions import PyProjectException

            raise PyProjectException(f"[tool.blix.data] section not found in {self.poetry.file}") from e

        data_files = None
        if "data_files" in data_files_config:
            data_files = data_files_config["data_files"]
        self.line(f"Adding data_files={data_files}")

        # Create our custom wheel builder
        builder = BlixWheelBuilder(
            self.poetry, env=self.env, locker=self.poetry.locker, executable=self.env.python, data_files=data_files
        )
        builder.build()


class BlixPlugin(ApplicationPlugin):
    def activate(self, application: Application) -> None:
        # Custom build command via `poetry blix`
        application.command_loader.register_factory(BlixBuildCommand.name, lambda: BlixBuildCommand())

        # TODO: Add validateplugin
