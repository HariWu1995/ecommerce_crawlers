import os
import sys
import time
from tqdm import tqdm as print_progress

import csv
import json
import logging

import numpy as np
import pandas as pd
import random

import cv2
from PIL import Image
from matplotlib import pyplot as plt

import re
import requests
from io import BytesIO
from bs4 import BeautifulSoup as BS
from urllib import request, response

from selenium import webdriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import *
from selenium.common.exceptions import *

import sqlite3 as sqllib

from sql_commands import *
from driver_utils import *
from utils import *


working_dir = os.path.dirname(__file__)


# Define global variables
page_url = 'https://www.tiki.vn/'
data_source = 'tiki'

# Logging
filename = f'{data_source}_{time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())}.txt'
logger = logging.getLogger(filename)
logger.setLevel(logging.DEBUG)
# logger.propagate = False
logger.addHandler(logging.StreamHandler())
logger.addHandler(logging.FileHandler(filename, 'a', encoding='utf8'))


def crawl_all_categories(driver):
    driver.get(page_url)

    # Scroll down to load all page
    simulate_scroll(driver, 5, 1)

    # Crawl
    categories_raw = driver.find_elements_by_css_selector('[data-view-id="home_top.category_product_item"]')
    categories = []
    for cat_raw in categories_raw:
        category_info = [
            cat_raw.find_element_by_tag_name('span').text, 
            cat_raw.get_attribute('href'),
            data_source
        ]
        # insert_new_category(category_info)
        categories.append(category_info)
    return categories


def crawl_single_category(driver, category_url: str, category_id: int):
    
    logger.info(f"\n\n\nLoading\n\t{category_url}")
    driver.get(category_url)

    # Scroll down to load all page
    simulate_scroll(driver)

    category_url += '/?page={}'
    all_products = []
    page_id, max_pages = 1, 69
    out_of_pages = False
    while page_id <= max_pages and not out_of_pages:
        logger.info(f"\n\n\nCrawling page {page_id} ...")
        product_css = '[class="product-item"]'
        products_raw = driver.find_elements_by_css_selector(product_css)
        if len(products_raw) < 1:
            logger.info("Can't find any item!")
            break

        # Get product info
        for product_raw in products_raw:
            product_title = product_raw.find_element_by_css_selector('[class="info"]')\
                                        .find_element_by_css_selector('[class="name"]')\
                                        .find_element_by_tag_name('span').text
            if not (product_title != '' or product_title.strip()):
                continue

            product_info = [
                product_title, 
                product_raw.get_attribute('href').split('?', 1)[0],
                category_id
            ]
            insert_new_product(product_info)
            all_products.append(product_info)

            # open new tab
            current_tab = driver.current_window_handle
            driver.execute_script("window.open('');") 
            driver.switch_to.window(driver.window_handles[-1])

            # crawl products' reviews per category
            product_title = product_info[0].replace('"', "'")
            query = f'SELECT id FROM products WHERE title = "{product_title}" AND category_id = "{category_id}"'
            execute_sql(query)
            product_id = db_cursor.fetchone()[0]
            try:
                crawl_single_product(driver, product_info[1], product_id)
            except Exception as e:
                logger.info("Error while crawl\n\t"+product_info[1]+'\n'+str(e))

            # close tab
            driver.close() 
            driver.switch_to.window(current_tab)

        try:
            page_id += 1
            driver.get(category_url.format(page_id))
            random_sleep()

            # Check out-of-page
            content = driver.find_element_by_tag_name('html')
            html_content = BS(content.get_attribute('innerHTML'), features="html5lib").get_text()
            # if any(ss in html_content.lower() for ss in ['rất tiếc', 'không tìm thấy']):
            #     break
        except Exception as e:
            logger.info('\n\n\nOut-of-page Error: '+str(e))
            out_of_pages = True


def crawl_single_product(driver, product_url: str, product_id: int):
    logger.info(f"\n\n\nLoading\n\t{product_url}")
    driver.get(product_url)

    # Scroll down to load all page
    simulate_scroll(driver)

    page_id, max_pages = 1, 27
    out_of_pages = False
    while page_id <= max_pages and not out_of_pages:
        logger.info(f"\n\t\tCrawling page {page_id} ...")
        review_css = "div.style__StyledComment-sc-103p4dk-5.dDtAUu.review-comment"
        all_reviews = driver.find_elements_by_css_selector(review_css)
        if len(all_reviews) < 1:
            logger.info("Can't find any review!")
            break
        
        # Get product reviews
        for raw_review in all_reviews:
            try:
                crawl_single_review(raw_review, product_id)
            except Exception as e:
                logger.info("Error while crawling comment\n\t"+str(e))

        try:
            # Check out-of-pages
            check_next_page_available = driver.find_elements_by_css_selector('[class="btn next"]')
            if len(check_next_page_available) < 1:
                logger.info('\n\t\tOut of pages')
                out_of_pages = True
            else:
                button_next = driver.find_element_by_css_selector('[class="btn next"]')
                driver.execute_script("arguments[0].click();", button_next)
                random_sleep()
                page_id += 1
        except Exception as e:
            logger.info('\n\t\tOut of pages error: '+str(e))
            out_of_pages = True
            break


def crawl_single_review(raw_review, product_id):

    # Read review content
    review_title = raw_review.find_element_by_css_selector('a.review-comment__title').text
    review_content = raw_review.find_element_by_css_selector('div.review-comment__content').text
    
    # Filter-out non-text reviews
    if not (review_content != '' or review_content.strip()):
        return 'Cannot crawl review'
    review = '<title> ' + review_title + ' </title> ' + review_content
    review = review.replace('\n', ' . ').replace('\t', ' . ')

    # Read number of likes for this review
    try:
        n_likes = raw_review.find_element_by_css_selector("[class='review-comment__thank ']")\
                            .find_element_by_tag_name("span").text
        n_likes = re.sub('[^0-9]', '', n_likes)
        if n_likes == '':
            n_likes = 0
        else:
            n_likes = int(n_likes)
    except Exception:
        n_likes = -1

    # Read rating
    rating = 0
    stars = raw_review.find_element_by_css_selector('div.Stars__StyledStars-sc-15olgyg-0.jucQbJ')\
                        .find_element_by_tag_name('div').get_attribute('style')
    rating = int(re.sub('[^0-9]', '', stars)) * 5 / 100
    rating = int(rating)
        
    # Read verification
    is_verified = 'chưa xác thực'
    try:
        is_verified = raw_review.find_element_by_css_selector("[class='review-comment__avatar-bought']").text
    except Exception:
        pass

    try:
        insert_new_review([review, is_verified, n_likes, rating, product_id])
        print('\t\t\t', review, is_verified, n_likes, rating)
    except Exception:
        logger.info('\n\nCannot insert review\n\t'+review)


def main(driver):

    # Step 1: Get all categories in main page
    all_categories = crawl_all_categories(driver)
    db_cursor.execute("SELECT category_id FROM products;")
    crawled_category_ids = list(set(
        np.array(db_cursor.fetchall()).flatten().tolist()
    ))
    logger.info(f"Categories crawled: {crawled_category_ids}")
    random_sleep()

    # Step 2: Get products per categories page-by-page, then crawl their info & reviews
    main_page = driver.current_window_handle
    random.shuffle(all_categories)
    for category_info in all_categories:
        # open new tab
        driver.execute_script("window.open('');") 
        driver.switch_to.window(driver.window_handles[-1])
        random_sleep()

        # crawl products' reviews per category
        category_title = category_info[0].replace('"', "'")
        query = f'SELECT id FROM categories WHERE title = "{category_title}" AND source = "{data_source}"'
        execute_sql(query)
        category_id = db_cursor.fetchone()[0]
        if category_id not in crawled_category_ids:
            crawl_single_category(driver, category_info[1], category_id)
            random_sleep()
        logger.info(f'Finish crawling {category_title} at {data_source}')

        # close current tab
        driver.close() 
        driver.switch_to.window(main_page)


if __name__ == "__main__":
    initialize_db()
    while True:
        # Step 0: Initialize
        browser = random.choice(['chrome', 'firefox', 'edge'])
        driver = initialize_driver(browser)

        try:
            main(driver)
        except Exception as e:
            logger.info("\n\n\nCrash ... Please wait a few seconds!!!")
            for t in print_progress(range(69)):
                time.sleep(1)
        
        driver.quit()
    db_connector.close()

