import re
from typing import List

import pkginfo
from cleo.helpers import argument
from cleo.io.inputs.option import Option
from cleo.io.outputs.output import Verbosity
from poetry.console.commands.env_command import EnvCommand
from poetry.core.semver.helpers import parse_constraint

# e.g. "nemoize (>=0.1.0,<0.2.0)"
from poeblix.util import util

package_regex = r"(.*) \((.*)\)"


class ValidateWheelPlugin(EnvCommand):
    """
    Validates a wheel file contains Requires Dist as specified in pyproject.toml and poetry.lock files in the project
    this command is run.
    """

    name = "blixvalidatewheel"
    description = "Validates a wheel file contains Requires Dist as specified in pyproject.toml and poetry.lock files in the project this command is ran."

    arguments = [argument("wheelPath", "Wheel file path")]

    # TODO: Add groups to options
    # TODO: Add toggleable option for using lock
    options: List[Option] = []

    loggers = ["poetry.core.masonry.builders.wheel"]

    def _validate_pyproject_toml(self, requires_dist: dict):
        """Validates that dependencies in pyproject.toml are exactly reflected in the wheel file's requires_dist"""
        # TODO: Only checks main group
        self.line("Validating against pyproject.toml...")
        required_packages = self.poetry.package.requires
        leftover_packages = set([p.pretty_name for p in required_packages])
        for package in required_packages:
            name = package.pretty_name
            if name in requires_dist:
                leftover_packages.remove(name)
                # Parse constraint into an object using poetry's helper
                wheel_version = parse_constraint(requires_dist[name])
                if package.constraint.difference(wheel_version).is_any():
                    raise RuntimeError(f"Wheel file has different version constraints for Package(name={name}, version={wheel_version}) compared to pyproject.toml Package(name={name}, version={package.constraint})")
        if leftover_packages:
            raise RuntimeError(f"Packages in pyproject.toml are not present in the Wheel file: {leftover_packages}")

    def _validate_poetry_lock(self, requires_dist: dict):
        """Validates that dependencies in poetry.lock are exactly reflected in the wheel file's requires_dist"""
        self.line("Validating against poetry.lock...")
        locked_repo = self.poetry.locker.locked_repository(True)
        ops = util.resolve_dependencies(self.poetry, self.env, locked_repo)
        leftover_packages = set([p.package.pretty_name for p in ops])
        for op in ops:
            dependency_package = op.package
            name = dependency_package.pretty_name
            if name in requires_dist:
                leftover_packages.remove(name)
                # Parse constraint into an object using poetry's helper
                wheel_version = parse_constraint(requires_dist[name])
                if dependency_package.version.difference(wheel_version).is_any():
                    raise RuntimeError(
                        f"Wheel file has different version constraints for Package(name={name}, version={wheel_version}) compared to poetry.lock Package(name={name}, version={dependency_package.version})")
        if leftover_packages:
            raise RuntimeError(f"Packages in poetry.lock are not present in the Wheel file: {leftover_packages}")

    def handle(self) -> None:
        path = self.argument("wheelPath")
        self.line(f"Validating Requires Dist for wheel [{path}] against pyproject.toml/poetry.lock")
        metadata = pkginfo.get_metadata(path)
        self.line(f"Wheel Requires Dist: {metadata.requires_dist}")
        packages = {}
        for package in metadata.requires_dist:
            parsed = re.search(package_regex, package)
            packages[parsed.group(1)] = parsed.group(2)
        self.line(f"Parsed Requires Dist: {packages}", verbosity=Verbosity.DEBUG)
        self._validate_pyproject_toml(packages)
        self._validate_poetry_lock(packages)
        self.line("Success!")
