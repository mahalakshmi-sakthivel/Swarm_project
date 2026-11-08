"""
Execution Sandbox - Confined Project Environment for Generated Code.
Enforces Non-Negotiable Rule 5: Generated code is written and run only
inside a temporary project folder with no access to personal files.
"""

import os
from pathlib import Path
import re
from typing import List, Optional


class SandboxSecurityViolation(Exception):
    """Raised when an agent attempts to access files outside the sandbox."""
    pass


def sanitize_and_heal_artifact(filename: str, content: str) -> str:
    """
    Deterministically fixes minor LLM truncation and syntax issues before saving.
    Guarantees:
    - Stripped markdown code fences (```css ... ```)
    - Auto-balanced curly braces for CSS
    - Removal of accidental HTML tags inside CSS
    - Relative asset links (no leading /) and auto-injected <link rel="stylesheet">
    - Auto-closed </body> and </html>
    """
    # 1. Strip markdown code fences if LLM included them
    content = re.sub(r"^```[a-zA-Z]*\r?\n", "", content.strip())
    content = re.sub(r"\r?\n```$", "", content.strip())

    if filename.endswith(".css"):
        # Remove accidental HTML tags inside CSS (<!DOCTYPE>, <html>, <head>, <style>)
        content = re.sub(r"</?(?:html|head|body|style|!DOCTYPE)[^>]*>", "", content, flags=re.IGNORECASE)
        # Auto-balance unclosed curly braces at the end of truncated CSS
        open_braces = content.count("{")
        close_braces = content.count("}")
        if open_braces > close_braces:
            content += "\n" + ("}\n" * (open_braces - close_braces))

    elif filename.endswith(".html"):
        # Ensure stylesheet and script links are relative (no leading slash)
        content = content.replace('href="/styles.css"', 'href="styles.css"')
        content = content.replace('src="/script.js"', 'src="script.js"')

        # Inject <link rel="stylesheet" href="styles.css"> if Structure Specialist forgot it
        if "styles.css" not in content and "</head>" in content:
            content = content.replace("</head>", '  <link rel="stylesheet" href="styles.css">\n</head>')

        # Auto-close truncated HTML tags if document started <html> or <body>
        if ("<html" in content.lower() or "<body" in content.lower()) and "</body>" not in content.lower():
            content += "\n</body>"
        if "<html" in content.lower() and "</html>" not in content.lower():
            content += "\n</html>"

    elif filename.endswith(".js"):
        # Strip accidental script tags if LLM wrapped in <script>
        content = re.sub(r"</?script[^>]*>", "", content, flags=re.IGNORECASE)

    return content


class Sandbox:
    def __init__(self, run_id: str, base_dir: str = ".sandbox"):
        self.run_id = run_id
        self.base_dir = Path(base_dir).resolve()
        self.sandbox_dir = (self.base_dir / run_id).resolve()
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self.sandbox_dir

    def resolve_path(self, rel_path: str) -> Path:
        """
        Safely resolve a relative path inside the sandbox directory.
        Raises SandboxSecurityViolation if path escapes the sandbox root.
        """
        # Strip leading slashes to prevent root-relative overrides
        clean_path = rel_path.lstrip("/\\")
        target_path = (self.sandbox_dir / clean_path).resolve()

        # Strict containment check
        try:
            target_path.relative_to(self.sandbox_dir)
        except ValueError:
            raise SandboxSecurityViolation(
                f"Security violation: path '{rel_path}' attempts to escape sandbox '{self.sandbox_dir}'"
            )

        return target_path

    def write_file(self, rel_path: str, content: str) -> str:
        """Write sanitized, auto-healed text content to a sandboxed file."""
        sanitized_content = sanitize_and_heal_artifact(rel_path, content)
        target_path = self.resolve_path(rel_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(sanitized_content, encoding="utf-8")
        return str(target_path)

    def read_file(self, rel_path: str) -> str:
        """Read text content from a sandboxed file."""
        target_path = self.resolve_path(rel_path)
        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError(f"File not found inside sandbox: '{rel_path}'")
        return target_path.read_text(encoding="utf-8")

    def file_exists(self, rel_path: str) -> bool:
        """Check if a file exists inside the sandbox."""
        try:
            target_path = self.resolve_path(rel_path)
            return target_path.exists() and target_path.is_file()
        except SandboxSecurityViolation:
            return False

    def list_files(self) -> List[str]:
        """List all files in the sandbox relative to the sandbox root."""
        files = []
        for p in self.sandbox_dir.rglob("*"):
            if p.is_file():
                rel = p.relative_to(self.sandbox_dir).as_posix()
                files.append(rel)
        return sorted(files)

    def clean(self):
        """Remove all files and the sandbox directory."""
        if self.sandbox_dir.exists():
            import shutil
            shutil.rmtree(self.sandbox_dir, ignore_errors=True)

