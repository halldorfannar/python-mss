"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.

Adapted for the proposed source-bound capture API (not yet implemented).

Simple naive benchmark to compare with:
    https://pythonprogramming.net/game-frames-open-cv-python-plays-gta-v/
"""

import time

import cv2
import numpy as np
from PIL import ImageGrab

import mss


def screen_record() -> int:
    # 800x600 windowed mode
    mon = (0, 40, 800, 640)

    title = "[PIL.ImageGrab] FPS benchmark"
    fps = 0
    last_time = time.time()

    while time.time() - last_time < 1:
        img = np.asarray(ImageGrab.grab(bbox=mon))
        fps += 1

        cv2.imshow(title, cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if cv2.waitKey(25) & 0xFF == ord("q"):
            cv2.destroyAllWindows()
            break

    return fps


def screen_record_efficient() -> int:
    # 800x600 windowed mode
    mon = mss.Region(top=40, left=0, width=800, height=640)

    title = "[MSS] FPS benchmark"
    fps = 0
    with mss.MSS() as sct:
        with sct.create_capture(sct.desktop) as capture:
            last_time = time.time()

            while time.time() - last_time < 1:
                img = np.asarray(capture.grab(region=mon))
                fps += 1

                cv2.imshow(title, img)
                if cv2.waitKey(25) & 0xFF == ord("q"):
                    cv2.destroyAllWindows()
                    break

    return fps


print("PIL:", screen_record())
print("MSS:", screen_record_efficient())
