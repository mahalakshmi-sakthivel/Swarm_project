"""
Agent Tools - Sandboxed Execution Primitives.
Agents interact with project files exclusively through these validated tools.
"""

import hashlib
from typing import Any, Dict, List
from runtime.sandbox import Sandbox


def write_file(sandbox: Sandbox, rel_path: str, content: str) -> Dict[str, Any]:
    """Write text file inside sandbox, computing SHA-256 content hash."""
    abs_path = sandbox.write_file(rel_path, content)
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return {
        "path": rel_path,
        "content_hash": content_hash,
        "bytes": len(content.encode("utf-8")),
        "absolute_path": abs_path
    }


def read_file(sandbox: Sandbox, rel_path: str) -> str:
    """Read file content from sandbox."""
    return sandbox.read_file(rel_path)


def list_files(sandbox: Sandbox) -> List[str]:
    """List all project files inside the sandbox."""
    return sandbox.list_files()


def verify_web_assets(sandbox: Sandbox) -> Dict[str, Any]:
    """
    Basic verification check for a web project:
    Confirms presence of index.html and basic structure.
    """
    files = sandbox.list_files()
    has_html = "index.html" in files
    issues = []

    if not has_html:
        issues.append("Missing index.html entry point.")
    else:
        content = sandbox.read_file("index.html")
        if "<html" not in content.lower() or "</html>" not in content.lower():
            issues.append("index.html is missing valid <html> closure tags.")

    return {
        "valid": len(issues) == 0,
        "files_count": len(files),
        "files": files,
        "issues": issues
    }

