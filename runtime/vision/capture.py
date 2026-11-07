"""
Headless Browser Screenshot Engine (Stage 5).
Captures pixel-accurate viewport screenshots of local or remote HTML documents
using native Headless Chromium (Chrome/Edge) with graceful fallback to PIL.
"""

import logging
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("runtime.vision.capture")

# Standard Windows browser installation locations
COMMON_BROWSER_PATHS = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
]


class ScreenshotCapture:
    """Headless browser screenshot manager with multi-browser detection and PIL fallback."""

    def __init__(self, browser_path: Optional[str] = None):
        self.browser_path = self._resolve_browser_path(browser_path)
        if self.browser_path:
            logger.info(f"ScreenshotCapture initialized with browser: {self.browser_path}")
        else:
            logger.warning("No headless Chromium binary detected; using PIL synthetic fallback.")

    @staticmethod
    def _resolve_browser_path(explicit_path: Optional[str] = None) -> Optional[Path]:
        """Locate an available Chromium-compatible browser binary."""
        if explicit_path and Path(explicit_path).exists():
            return Path(explicit_path)

        env_path = os.environ.get("CHROME_PATH") or os.environ.get("BROWSER_PATH")
        if env_path and Path(env_path).exists():
            return Path(env_path)

        for candidate in COMMON_BROWSER_PATHS:
            if candidate.exists():
                return candidate

        # Check system PATH via shutil.which
        for name in ("chrome", "chrome.exe", "msedge", "msedge.exe", "chromium"):
            found = shutil.which(name)
            if found:
                return Path(found)

        return None

    def capture(
        self,
        target: str | Path,
        output_path: str | Path,
        width: int = 1280,
        height: int = 800,
        timeout_seconds: int = 20,
    ) -> Path:
        """
        Capture a viewport screenshot of an HTML file or URL.
        Returns the Path to the written PNG image.
        """
        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        target_str = str(target)
        if not (target_str.startswith("http://") or target_str.startswith("https://") or target_str.startswith("file://")):
            # Convert local file path to valid file URI
            abs_target = Path(target_str).resolve()
            if not abs_target.exists():
                raise FileNotFoundError(f"Target file for screenshot does not exist: {abs_target}")
            # Format Windows path as file:///D:/path/...
            target_str = abs_target.as_uri()

        if self.browser_path:
            try:
                self._capture_via_headless_browser(
                    target_url=target_str,
                    output_path=out_path,
                    width=width,
                    height=height,
                    timeout=timeout_seconds,
                )
                if out_path.exists() and out_path.stat().st_size > 0:
                    return out_path
            except Exception as e:
                logger.warning(f"Headless browser capture failed: {e}; falling back to synthetic capture.")

        # Fallback to PIL canvas generation
        self._capture_fallback_pil(target, out_path, width, height)
        return out_path

    def _capture_via_headless_browser(
        self,
        target_url: str,
        output_path: Path,
        width: int,
        height: int,
        timeout: int,
    ) -> None:
        """Execute headless Chromium CLI with temporary isolated profile."""
        with tempfile.TemporaryDirectory() as tmp_user_data_dir:
            cmd = [
                str(self.browser_path),
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--hide-scrollbars",
                "--force-device-scale-factor=1",
                f"--window-size={width},{height}",
                f"--user-data-dir={tmp_user_data_dir}",
                f"--screenshot={output_path}",
                target_url,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                logger.debug(f"Chromium returned {result.returncode}: {result.stderr}")

    def _capture_fallback_pil(
        self,
        source: str | Path,
        output_path: Path,
        width: int,
        height: int,
    ) -> None:
        """Generate a deterministic synthetic screenshot rendering for test/CI fallback."""
        img = Image.new("RGB", (width, height), color="#090d16")
        draw = ImageDraw.Draw(img)

        # Header bar
        draw.rectangle([(0, 0), (width, 60)], fill="#111827")
        draw.text((30, 20), "Swarm Website Builder - Synthetic Preview", fill="#60a5fa")

        # Content box
        draw.rectangle([(40, 90), (width - 40, height - 90)], outline="#374151", width=2)
        draw.text((60, 120), f"Render Source: {source}", fill="#f9fafb")
        draw.text((60, 160), "Status: Rendered via PIL Fallback Engine", fill="#4ade80")

        # Visual accent blocks
        draw.rectangle([(60, 210), (300, 320)], fill="#1f2937", outline="#60a5fa")
        draw.rectangle([(330, 210), (570, 320)], fill="#1f2937", outline="#e879f9")
        draw.rectangle([(600, 210), (840, 320)], fill="#1f2937", outline="#4ade80")

        img.save(str(output_path), "PNG")
        logger.info(f"Synthetic fallback screenshot saved to {output_path}")
