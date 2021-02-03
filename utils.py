import os
import time
import random
import logging

import re
import numpy as np
from PIL import Image
from bs4 import BeautifulSoup as BS

from IPython.display import IFrame, display, HTML

from w3lib.url import url_query_cleaner
from url_normalize import url_normalize


def clean_html(raw_html):
  tags = re.compile('<.*?>')
  clean_text = re.sub(tags, '', raw_html)
  return clean_text


def create_logger(data_source):
    # Logging
    filename = f'{data_source}_{time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())}.txt'
    logger = logging.getLogger(filename)
    logger.setLevel(logging.INFO)
    # logger.propagate = False
    logger.addHandler(logging.StreamHandler())
    logger.addHandler(logging.FileHandler(filename, 'a', encoding='utf8'))
    return logger


def print_html(content, width=600, height=600):
    html_content = BS(content.get_attribute('innerHTML'), features="html5lib").get_text()
    # print(html_content)
    with open('debug.html', "w") as f:
        print(html_content, file=f)


def random_sleep():
    time.sleep(random.randint(6,9))


def debug_html(content):
    html_content = BS(content.get_attribute('innerHTML'), features="html5lib")#.get_text()
    print(html_content.prettify())
    

def numberize_visual_star(star_image: Image, positive_star, negative_star) -> int:
    star_image = np.array(star_image).reshape(64, 64)
    pos_diff = np.sum(np.fabs(np.subtract(star_image, positive_star)))
    neg_diff = np.sum(np.fabs(np.subtract(star_image, negative_star)))
    return 1 if pos_diff<neg_diff else 0


def simulate_scroll(driver, n_downs: int=7, n_ups: int=2, min_secs=0.69, max_secs=1.69):
    for i in range(n_downs): 
        driver.execute_script(f"window.scrollBy(0, {random.randint(690, 960)})")
        time.sleep(random.uniform(min_secs, max_secs))
    for i in range(n_ups): 
        driver.execute_script(f"window.scrollBy(0, -{random.randint(690, 960)})")
        time.sleep(random.uniform(min_secs, max_secs))


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





