"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.

Adapted for the proposed source-bound capture API (not yet implemented).

Usage example with a specific X11 display.
"""

import mss
import mss.tools

with mss.MSS(xdisplay=":0.0") as sct:
    for num, monitor in enumerate(sct.list_monitors(), 1):
        with sct.create_capture(monitor) as capture:
            image = capture.grab()
        filename = f"monitor-{num}.png"
        mss.tools.to_png(image.rgb, image.size, output=filename)
        print(filename)
