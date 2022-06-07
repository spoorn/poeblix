import subprocess


def test_positive_happy_case_example():
    cwd = "positive_cases/happy_case_example"
    # Build
    subprocess.check_call(["poetry", "blixbuild"], cwd=cwd)

    # Validate wheel
    subprocess.check_call(["poetry", "blixvalidatewheel", "dist/blixexample-0.1.0-py3-none-any.whl"], cwd=cwd)


def test_positive_no_lock():
    cwd = "positive_cases/no_lock"
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


def test_negative_missing_from_project():
    cwd = "negative_cases/missing_from_project"
    # Validate wheel fails
    proc = subprocess.Popen(
        ["poetry", "blixvalidatewheel", "dist/blixexample-missing_from_project.whl"], cwd=cwd, stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate()
    assert stdout is None
    stderr = stderr.decode()
    # assert "RuntimeError" in stderr, "Expected error to be RuntimeError"
    assert (
        "Packages in Wheel file are not present in pyproject.toml/poetry.lock: ['nemoize']" in stderr
    ), "Did not get expected error message!"


def test_negative_missing_from_wheel():
    cwd = "negative_cases/missing_from_wheel"
    # Validate wheel fails
    proc = subprocess.Popen(
        ["poetry", "blixvalidatewheel", "dist/blixexample-missing_from_wheel.whl"], cwd=cwd, stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate()
    assert stdout is None
    stderr = stderr.decode()
    # assert "RuntimeError" in stderr, "Expected error to be RuntimeError"
    assert (
        "Packages in pyproject.toml are not present in the Wheel file: ['nemoize']" in stderr
    ), "Did not get expected error message!"


def test_negative_missing_data_files():
    cwd = "negative_cases/missing_data_files_from_wheel"
    # Validate wheel fails
    proc = subprocess.Popen(
        ["poetry", "blixvalidatewheel", "dist/blixexample-missing_data_files_from_wheel.whl"],
        cwd=cwd,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()
    assert stdout is None
    stderr = stderr.decode()
    # assert "RuntimeError" in stderr, "Expected error to be RuntimeError"
    assert (
        "Wheel at [dist/blixexample-missing_data_files_from_wheel.whl] does not contain expected data_file [blixexample-0.1.0.data/data/share/data/test.txt]"
        in stderr
    ), "Did not get expected error message!"


def test_negative_missing_data_files_from_project():
    cwd = "negative_cases/missing_data_files_from_project"
    # Validate wheel fails
    proc = subprocess.Popen(
        ["poetry", "blixvalidatewheel", "dist/blixexample-missing_data_files_from_project.whl"],
        cwd=cwd,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()
    assert stdout is None
    stderr = stderr.decode()
    # assert "RuntimeError" in stderr, "Expected error to be RuntimeError"
    assert (
        "Wheel at [dist/blixexample-missing_data_files_from_project.whl] contains extraneous data_files not specified in pyproject.toml: ['blixexample-0.1.0.data/data/share/data/test.txt', 'blixexample-0.1.0.data/data/share/data/anotherfile', 'blixexample-0.1.0.data/data/share/data/threes/athirdfile']"
        in stderr
    ), "Did not get expected error message!"
