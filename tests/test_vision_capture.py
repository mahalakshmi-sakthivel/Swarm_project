"""
Unit Tests for Stage 5 Headless Screenshot Engine (ScreenshotCapture).
Tests:
- ScreenshotCapture initialization and browser detection
- Capturing screenshot of a real HTML document
- Output file generation and validity
- Invalid target file handling
"""

import sys
sys.path.insert(0, ".")

from pathlib import Path
from PIL import Image
import pytest

from runtime.vision.capture import ScreenshotCapture


def test_screenshot_capture_initialization():
    capturer = ScreenshotCapture()
    # capturer may find system chrome or use synthetic fallback
    assert capturer is not None


def test_capture_html_file(tmp_path):
    html_file = tmp_path / "test_page.html"
    html_file.write_text(
        "<!DOCTYPE html><html><body style='background:#111;color:#fff;'><h1>Capture Test</h1></body></html>",
        encoding="utf-8"
    )

    out_png = tmp_path / "output_screenshot.png"
    capturer = ScreenshotCapture()
    result_path = capturer.capture(html_file, out_png, width=800, height=600)

    assert result_path.exists()
    assert result_path == out_png
    assert out_png.stat().st_size > 0

    # Verify output is valid readable PNG
    with Image.open(out_png) as img:
        assert img.format == "PNG"
        assert img.size == (800, 600)


def test_capture_nonexistent_file_raises_error(tmp_path):
    capturer = ScreenshotCapture()
    nonexistent = tmp_path / "does_not_exist.html"
    with pytest.raises(FileNotFoundError):
        capturer.capture(nonexistent, tmp_path / "out.png")
