"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.

Adapted for the proposed source-bound capture API (not yet implemented).

Select the XShmGetImage backend explicitly.
"""

from mss import MSS

with MSS() as sct:
    # No performance_status diagnostics: an explicit backend cannot fall back.
    # If MIT-SHM cannot be used, capture creation or acquisition raises an error.
    with sct.create_capture(sct.list_monitors()[0], backend="xshmgetimage") as capture:
        screenshot = capture.grab()
        print(f"Captured screenshot dimensions: {screenshot.size.width}x{screenshot.size.height}")
        print(f"Selected backend: {capture.backend}")
