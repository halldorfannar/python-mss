"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.

Adapted for the proposed source-bound capture API (not yet implemented).

Example to capture part of the screen.
"""

import mss
import mss.tools

with mss.MSS() as sct:
    # The screen part to capture
    monitor = mss.Region(top=160, left=160, width=160, height=135)
    output = f"sct-{monitor.top}x{monitor.left}_{monitor.width}x{monitor.height}.png"

    # Grab the data
    with sct.create_capture(sct.desktop) as capture:
        sct_img = capture.grab(region=monitor)

    # Save to the picture file
    mss.tools.to_png(sct_img.rgb, sct_img.size, output=output)
    print(output)
