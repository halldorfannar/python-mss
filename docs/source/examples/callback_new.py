"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.

Adapted for the proposed source-bound capture API (not yet implemented).

Screenshot of the monitor 1, with callback.
"""

from pathlib import Path

import mss
import mss.tools


def on_exists(fname: str) -> None:
    """Callback example when we try to overwrite an existing screenshot."""
    file = Path(fname)
    if file.is_file():
        newfile = file.with_name(f"{file.name}.old")
        print(f"{fname} → {newfile}")
        file.rename(newfile)


with mss.MSS() as sct:
    filename = "mon-1.png"
    on_exists(filename)
    with sct.create_capture(sct.list_monitors()[0]) as capture:
        image = capture.grab()
    mss.tools.to_png(image.rgb, image.size, output=filename)
    print(filename)
