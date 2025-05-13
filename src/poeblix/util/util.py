from typing import Sequence, Callable, List, Optional

from cleo.io.null_io import NullIO

# For fixing https://github.com/python-poetry/poetry/issues/5216
from packaging.tags import sys_tags  # noqa
from poetry.core.poetry import Poetry as CorePoetry
from poetry.installation.operations.operation import Operation
from poetry.poetry import Poetry
from poetry.puzzle import Solver
from poetry.repositories import RepositoryPool
from poetry.repositories import Repository
from poetry.repositories.installed_repository import InstalledRepository
from poetry.utils.env import Env


def resolve_dependencies(
    poetry: "CorePoetry", env: Env, locked_repository: Repository, with_groups: Optional[List[str]] = None
) -> Sequence[Operation]:
    """
    This uses poetry's solver to resolve dependencies and filters out packages from the lock file which are not
    needed, such as packages that are not for our OS environment using markers (e.g. pywin32 is for Windows).
    """
    # Making a new repo containing the packages
    # newly resolved and the ones from the current lock file
    repo = Repository(name="poetry-locked")
    for package in locked_repository.packages:
        if not package.is_direct_origin() and not repo.has_package(package):
            repo.add_package(package)

    base_repositories = None
    if isinstance(poetry, Poetry):
        base_repositories = poetry.pool.all_repositories
    pool = RepositoryPool(repositories=base_repositories)
    pool.add_repository(repo)

    # Run through poetry's dependency resolver.  Only uses the default/main `dependencies` in pyproject.toml, not
    # dev dependencies or other groups.  If we want to support more groups in the wheel file, we can expand on the
    # CLI with more options.
    # See https://github.com/python-poetry/poetry/blob/master/src/poetry/installation/installer.py#L34 for poetry's
    # usage of this
    # TODO: Add support for adding more groups
    groups = set(["default", "main"] + (with_groups if with_groups else []))

    solver = Solver(
        poetry.package.with_dependency_groups(groups=groups, only=True),
        pool,
        InstalledRepository.load(env).packages,
        locked_repository.packages,
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


def validate_options_mutually_exclusive(option_func: Callable, option1: str, option2: str) -> None:
    if option_func(option1) and option_func(option2):
        raise RuntimeError(f"'{option1}' and '{option2}' options are incompatible")
