import os.path
import re
import subprocess

import pkginfo


def test_positive_happy_case_example():
    cwd = "py37/positive_cases/happy_case_example"
    # Build
    subprocess.check_call(["poetry", "blixbuild"], cwd=cwd)

    # Validate wheel
    subprocess.check_call(["poetry", "blixvalidatewheel", "dist/blixexample-0.1.0-py3-none-any.whl"], cwd=cwd)


def test_positive_with_groups():
    cwd = "py37/positive_cases/happy_case_example"
    # Build
    subprocess.check_call(["poetry", "blixbuild", "--with-groups=integ,dev", "-vvv"], cwd=cwd)

    # Validate wheel
    subprocess.check_call(
        ["poetry", "blixvalidatewheel", "--with-groups=integ,dev", "dist/blixexample-0.1.0-py3-none-any.whl"], cwd=cwd
    )


def test_positive_no_lock():
    cwd = "py37/positive_cases/no_lock"
    # Build
    subprocess.check_call(["poetry", "blixbuild", "--no-lock"], cwd=cwd)

    # Validate wheel
    subprocess.check_call(
        ["poetry", "blixvalidatewheel", "--no-lock", "dist/blixexample-0.1.0-py3-none-any.whl"], cwd=cwd
    )

    # Sanity check: Validate locked dependencies are not present
    proc = subprocess.Popen(
        ["poetry", "blixvalidatewheel", "dist/blixexample-0.1.0-py3-none-any.whl"], cwd=cwd, stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate()
    assert stdout is None
    stderr = stderr.decode()
    # From poetry 1.2.0b2, stderr only includes the error message unless "-v" is included in the command
    # assert "RuntimeError" in stderr, "Expected error to be RuntimeError"
    assert (
        "Packages in poetry.lock are not present in the Wheel file: ['numpy', 'python-dateutil', 'pytz', 'six']"
        in stderr
    ), "Did not get expected error message!"


def test_positive_only_lock():
    cwd = "py37/positive_cases/only_lock"
    # Build
    subprocess.check_call(["poetry", "blixbuild", "--only-lock"], cwd=cwd)

    # Validate wheel
    subprocess.check_call(["poetry", "blixvalidatewheel", "dist/blixexample-0.1.0-py3-none-any.whl"], cwd=cwd)

    # Check if only fixed versions from lock file are set as dependencies
    # e.g "pandas (==0.1.0,<0.2.0)"
    package_regex = r".* \(\=\=.*\)"

    path = os.path.join(cwd, "dist/blixexample-0.1.0-py3-none-any.whl")
    metadata = pkginfo.get_metadata(path)

    for package in metadata.requires_dist:
        parsed = re.search(package_regex, package)
        assert parsed, f"Dependency {package} doesn't have fixed versions"


def test_negative_incompatible_lock_options():
    cwd = "py37/negative_cases/incompatible_lock_options"

    # Validate command fails when both 'no-lock' and '--only-lock'
    # are given at the same time
    proc = subprocess.Popen(["poetry", "blixbuild", "--no-lock", "--only-lock"], cwd=cwd, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    assert stdout is None
    stderr = stderr.decode()
    assert "'no-lock' and 'only-lock' options are incompatible" in stderr, "Did not get expected error message!"
