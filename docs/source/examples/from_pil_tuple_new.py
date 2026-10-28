"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.

Adapted for the proposed source-bound capture API (not yet implemented).

Use PIL bbox style and percent values.
"""

import mss
import mss.tools

with mss.MSS() as sct:
    # Use the 1st monitor
    monitor = sct.list_monitors()[0]

    # Construct a PIL bbox using global desktop coordinates
    left = monitor.bounds.left + monitor.bounds.width * 5 // 100
    top = monitor.bounds.top + monitor.bounds.height * 5 // 100
    pil_bbox = (left, top, left + 400, top + 400) # 400px width and height

    # Convert PIL's (left, top, right, bottom) to a Region
    left, top, right, bottom = pil_bbox
    region = mss.Region(left, top, right - left, bottom - top)

    # Grab the picture
    with sct.create_capture(sct.desktop) as capture:
        im = capture.grab(region=region)
    # Using PIL instead would be something like:
    # im = ImageGrab(bbox=pil_bbox)

    # Save it!
    mss.tools.to_png(im.rgb, im.size, output="screenshot.png")
