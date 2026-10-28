"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.

Adapted for the proposed source-bound capture API (not yet implemented).

PIL example using ScreenShot.to_pil().
"""

import mss

with mss.MSS() as sct:
    for num, monitor in enumerate(sct.list_monitors(), 1):
        # Get raw pixels from the screen
        with sct.create_capture(monitor) as capture:
            sct_img = capture.grab()

        # Create the Image
        img = sct_img.to_pil("RGB")

        # And save it!
        output = f"monitor-{num}.png"
        img.save(output)
        print(output)
