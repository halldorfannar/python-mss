"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.

Adapted for the proposed source-bound capture API (not yet implemented).

Example to capture part of the screen of the monitor 2.
"""

import mss
import mss.tools

with mss.MSS() as sct:
    # Get information of monitor 2 (index 1 in the list of monitors)
    monitor_number = 2
    mon = sct.list_monitors()[monitor_number - 1]

    # The screen part to capture
    region = mss.Region(top=100, left=100, width=160, height=135)
    output = (
        f"sct-mon{monitor_number}_{mon.bounds.top + region.top}x{mon.bounds.left + region.left}_"
        f"{region.width}x{region.height}.png"
    )

    # Grab the data
    with sct.create_capture(mon) as capture:
        sct_img = capture.grab(region=region)

    # Save to the picture file
    mss.tools.to_png(sct_img.rgb, sct_img.size, output=output)
    print(output)
