import os
import time
import random

import numpy as np
from PIL import Image

from w3lib.url import url_query_cleaner
from url_normalize import url_normalize


def random_sleep():
    time.sleep(random.randint(6,9))


def numberize_visual_star(star_image: Image, positive_star, negative_star) -> int:
    star_image = np.array(star_image).reshape(64, 64)
    pos_diff = np.sum(np.fabs(np.subtract(star_image, positive_star)))
    neg_diff = np.sum(np.fabs(np.subtract(star_image, negative_star)))
    return 1 if pos_diff<neg_diff else 0


def simulate_scroll(driver, n_downs: int=7, n_ups: int=2):
    for i in range(n_downs): 
        driver.execute_script(f"window.scrollBy(0, {random.randint(690, 960)})")
        time.sleep(random.uniform(0.69, 0.96))
    for i in range(n_ups): 
        driver.execute_script(f"window.scrollBy(0, -{random.randint(690, 960)})")
        time.sleep(random.uniform(0.69, 0.96))


def normalize_url(url: str) -> str:
    url = url_normalize(url)
    url = url_query_cleaner(url, 
                            parameterlist=['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'], 
                            remove=True)

    if url.startswith("http://"):
        url = url[7:]
    if url.startswith("https://"):
        url = url[8:]
    if url.startswith("www."):
        url = url[4:]
    if url.endswith("/"):
        url = url[:-1]
    return url





