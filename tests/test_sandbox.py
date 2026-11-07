"""
Unit tests for Execution Sandbox:
- File isolation and path containment
- Rejection of directory traversal attacks
- Safe reading and writing
"""

import pytest
from runtime.sandbox import Sandbox, SandboxSecurityViolation


@pytest.fixture
def sandbox(tmp_path):
    return Sandbox(run_id="test_run", base_dir=str(tmp_path))


def test_sandboxed_file_operations(sandbox):
    sandbox.write_file("src/index.html", "<h1>Hello World</h1>")
    assert sandbox.file_exists("src/index.html") is True
    assert sandbox.read_file("src/index.html") == "<h1>Hello World</h1>"
    assert "src/index.html" in sandbox.list_files()


def test_sandbox_security_traversal_rejection(sandbox):
    # Attempt to write outside sandbox root via relative parent ../
    with pytest.raises(SandboxSecurityViolation):
        sandbox.write_file("../escape.txt", "malicious content")

    # Attempt nested traversal
    with pytest.raises(SandboxSecurityViolation):
        sandbox.resolve_path("sub/../../escape.txt")


def test_sandbox_cleanup(sandbox):
    sandbox.write_file("temp.txt", "temp")
    assert sandbox.file_exists("temp.txt") is True
    sandbox.clean()
    assert sandbox.sandbox_dir.exists() is False

