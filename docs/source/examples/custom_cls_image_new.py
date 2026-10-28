"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.

Adapted for the proposed source-bound capture API (not yet implemented).

Screenshot of the monitor 1, using a custom class to handle the data.
"""

import mss
from mss.screenshot import ScreenShot


class SimpleScreenShot:
    """Wrap a returned screenshot; the proposed API drops cls_image."""

    def __init__(self, screenshot: ScreenShot) -> None:
        self.data = screenshot.bgra
        self.bounds = screenshot.bounds


with mss.MSS() as sct:
    with sct.create_capture(sct.list_monitors()[0]) as capture:
        image = SimpleScreenShot(capture.grab())
    # ...
