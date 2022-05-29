import subprocess
from typing import List

from cleo.helpers import argument
from cleo.io.inputs.option import Option

# For fixing https://github.com/python-poetry/poetry/issues/5216
from packaging.tags import sys_tags  # noqa
from poetry.console.commands.env_command import EnvCommand
from poetry.core.packages.package import Package

from poeblix.util import util


class ValidateDockerPlugin(EnvCommand):
    """
    Validates a docker container contains dependencies defined in the pyproject.toml and poetry.lock in the project
    this command is run.
    """

    name = "blixvalidatedocker"
    description = (
        "Validates a docker container contains dependencies as specified in pyproject.toml and poetry.lock.  "
        "By default, this validates in one direction, where dependencies specified in pyproject.toml/poetry.lock "
        "should be present in the Docker container, but not the other way around."
    )

    arguments = [argument("containerId", "Docker Container ID")]

    options: List[Option] = []

    loggers = ["poetry.core.masonry.builders.wheel"]

    def _validate_pyproject_toml(self, docker_deps: dict):
        cid = self.argument("containerId")
        required_packages = self.poetry.package.requires
        for package in required_packages:
            name = package.pretty_name
            if name in docker_deps:
                if package.accepts(Package(name, docker_deps[name])):
                    docker_deps.pop(name)
                else:
                    raise ValueError(
                        f"Inconsistency found!  pyproject.toml specifies {name}{package.constraint}, "
                        f"but docker container {cid} has {name}=={docker_deps[name]}"
                    )

    def _validate_poetry_lock(self, docker_deps: dict):
        cid = self.argument("containerId")
        locked_repo = self.poetry.locker.locked_repository(True)
        ops = util.resolve_dependencies(self.poetry, self.env, locked_repo)
        for op in ops:
            dependency_package = op.package
            name = dependency_package.pretty_name
            version = dependency_package.version
            if name in docker_deps:
                proc_version = docker_deps[name]
                if proc_version != str(version):
                    raise ValueError(
                        f"Inconsistency found!  poetry.lock specifies {name}=={version}, "
                        f"but docker container {cid} has {name}=={proc_version}"
                    )

    def handle(self) -> None:
        cid = self.argument("containerId")
        self.line(f"Fetching 'pip freeze' from docker image {cid} and validating against pyproject.toml/poetry.lock")

        docker_freeze = subprocess.check_output(f'docker exec {cid} python3 -m pip freeze | grep -v "@"', shell=True)
        docker_deps = {
            dsplit[0]: dsplit[1] for dsplit in (dep.split("==") for dep in docker_freeze.decode("utf-8").splitlines())
        }

        # Validate against pyproject.toml
        self._validate_pyproject_toml(docker_deps)
        # Validate against poetry.lock
        self._validate_poetry_lock(docker_deps)

        self.line(
            f"Validation success!  Docker image {cid} has consistent versions with dependencies specified "
            f"in this project"
        )
