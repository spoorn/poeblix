import subprocess


def test_positive_happy_case_example():
    cwd = "py38/positive_cases/happy_case_example"
    # Build
    subprocess.check_call(["poetry", "blixbuild"], cwd=cwd)

    # Validate wheel
    subprocess.check_call(["poetry", "blixvalidatewheel", "dist/blixexample-0.1.0-py3-none-any.whl"], cwd=cwd)


def test_positive_no_lock():
    cwd = "py38/positive_cases/no_lock"
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
