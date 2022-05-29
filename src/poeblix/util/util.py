from typing import Sequence

from cleo.io.null_io import NullIO

# For fixing https://github.com/python-poetry/poetry/issues/5216
from packaging.tags import sys_tags  # noqa
from poetry.core.poetry import Poetry
from poetry.installation.operations.operation import Operation
from poetry.puzzle import Solver
from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils.env import Env


def resolve_dependencies(poetry: "Poetry", env: Env, locked_repository: Repository) -> Sequence[Operation]:
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

    pool = Pool(ignore_repository_names=True)
    pool.add_repository(repo)

    # Run through poetry's dependency resolver.  Only uses the default/main `dependencies` in pyproject.toml, not
    # dev dependencies or other groups.  If we want to support more groups in the wheel file, we can expand on the
    # CLI with more options.
    # See https://github.com/python-poetry/poetry/blob/master/src/poetry/installation/installer.py#L34 for poetry's
    # usage of this
    # TODO: Add support for adding more groups
    groups = ["default", "main"]

    solver = Solver(
        poetry.package.with_dependency_groups(groups=groups, only=True),
        pool,
        InstalledRepository.load(env),
        locked_repository,
        NullIO(),
    )

    # Everything is resolved at this point, so we no longer need
    # to load deferred dependencies (i.e. VCS, URL and path dependencies)
    solver.provider.load_deferred(False)

    with solver.use_environment(env):
        ops = solver.solve(use_latest=[]).calculate_operations(
            with_uninstalls=False,
            synchronize=False,
        )
    return ops
