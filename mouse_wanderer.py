import os
import sys

import time
import random
import pyautogui as GUI


def main(W: int=1920, H: int=1080, offset: int=69):
    x = random.randint(offset, W-offset)
    y = random.randint(offset, H-offset)
    print(f"Move to {x}, {y}")
    GUI.moveTo(x, y, 3)


if __name__ == '__main__':
    GUI.FAILSAFE = False
    while True:
        try:
            main()
            time.sleep(69)
        except Exception:
            pass

