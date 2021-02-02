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
page_url = 'https://www.shopee.vn'
data_source = 'shopee'

# Logging
filename = f'{data_source}_{time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())}.txt'
logger = logging.getLogger(filename)
logger.setLevel(logging.INFO)
# logger.propagate = False
logger.addHandler(logging.StreamHandler())
logger.addHandler(logging.FileHandler(filename, 'a', encoding='utf8'))


def crawl_all_categories(driver):
    driver.get(page_url)

    # Scroll down to load all page
    simulate_scroll(driver, 5, 1)

    # Crawl
    categories = []
    categories_groups = driver.find_elements_by_css_selector('[class="home-category-list__group"]')
    for cat_group in categories_groups:
        categories_raw = cat_group.find_elements_by_css_selector('[class="home-category-list__category-grid"]')
        for cat_raw in categories_raw:
            cat_title = cat_raw.find_element_by_css_selector('[class="vvKCN3"]')
            category_info = [
                cat_title.get_attribute("innerHTML").replace('&amp;', '&'), 
                cat_raw.get_attribute('href'),
                data_source
            ]
            insert_new_category(category_info)
            categories.append(category_info)
    return categories


def crawl_single_category(driver, category_url: str, category_id: int):
    
    logger.info(f"\n\n\nLoading\n\t{category_url}")
    driver.get(category_url)

    # Scroll down to load all page
    simulate_scroll(driver, 11, 0, 0.69, 1.96)
    random_sleep()

    category_url += '/?page={}'
    all_products = []
    page_id, max_pages = 1, 69
    while page_id <= max_pages:
        product_css = '[class="col-xs-2-4 shopee-search-item-result__item"]'
        try:
            logger.info(f"\n\n\nCrawling page {page_id} ...")
            # Get the review details
            WebDriverWait(driver, timeout=random.randint(6,9)).until(
                method=expected_conditions.visibility_of_all_elements_located(
                    locator=(By.CSS_SELECTOR, product_css)
                )
            )
        except Exception:
            logger.info("Can't find any item!")
            break

        # Get product info
        products_raw = driver.find_elements_by_css_selector(product_css)
        for product_raw in products_raw:
            try:
                product_url = product_raw.find_element_by_css_selector('[data-sqe="link"]').get_attribute('href').split('?', 1)[0]
                product_title = product_raw.find_element_by_css_selector('[data-sqe="name"]').find_element_by_tag_name('div').text
                if not (product_title != '' or product_title.strip()):
                    continue
                product_info = [product_title, product_url, category_id]
                insert_new_product(product_info)
                all_products.append(product_info)
            except Exception:
                logger.info("Cannot crawl product")
                continue

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
                logger.info("Error while crawl\n\t"+product_info[1]+'\n'+e)

            # close tab
            driver.close() 
            driver.switch_to.window(current_tab)
        
        # Go to next page
        driver.get(category_url.format(page_id))
        simulate_scroll(driver, 11, 0, 0.69, 1.96)
        page_id += 1


def crawl_single_product(driver, product_url: str, product_id: int):
    logger.info(f"\n\n\nLoading\n\t{product_url}")
    driver.get(product_url)

    # Scroll down to load all page
    simulate_scroll(driver)

    page_id, max_pages = 1, 69
    while page_id <= max_pages:
        simulate_scroll(driver, 5, 1, 0.69, 0.96)
        review_css = '[class="shopee-product-rating"]'
        try:
            logger.info(f"\n\t\tCrawling page {page_id} ...")
            # Get the review details
            WebDriverWait(driver, timeout=random.randint(6,9)).until(
                method=expected_conditions.visibility_of_all_elements_located(
                    locator=(By.CSS_SELECTOR, review_css)
                )
            )
        except Exception:
            logger.info("Can't find any review!")
            break

        # Get product reviews
        all_reviews = driver.find_elements_by_css_selector(review_css)
        for raw_review in all_reviews:
            try:
                crawl_single_review(raw_review, product_id)
            except Exception as e:
                logger.info("Error while crawling comment\n\t"+e)

        try:
            page_buttons_css = '[class="shopee-button-no-outline"]'
            page_buttons = driver.find_elements_by_css_selector(page_buttons_css)
            if len(page_buttons) < 1:
                logger.info("\n\t\tOnly 1 page")
                break
            for page_button in page_buttons:
                page_button_id = page_button.get_attribute("innerHTML")
                if page_button_id == '':
                    continue
                if int(page_button_id) > page_id:
                    page_button.click()
                    random_sleep()
                    page_id += 1
                    break
        except Exception as e:
            logger.info("\n\t\tOut-of-page Error: "+e)
            break


def crawl_single_review(raw_review, product_id):
    content = raw_review.find_element_by_css_selector("[class='shopee-product-rating__main']")

    # Read review content
    review = content.find_element_by_css_selector("[class='shopee-product-rating__content']").text
    
    # Filter-out non-text reviews
    if not (review != '' or review.strip()):
        return 'Review is empty'
    review = review.replace('\n', ' . ').replace('\t', ' . ')

    # Read number of likes for this review
    n_likes = content.find_element_by_css_selector("[class='shopee-product-rating__like-count']")\
                    .get_attribute("innerHTML")
    n_likes = re.sub('[^0-9]', '', n_likes)
    if n_likes == '':
        n_likes = 0
    else:
        n_likes = int(n_likes)

    # Read rating
    try:
        rating = 5
        stars = content.find_element_by_css_selector('div.shopee-product-rating__rating')\
                        .find_elements_by_tag_name("svg")
        for star in stars:
            star_color = star.find_element_by_tag_name('polygon')
            try:
                star_empty = star_color.get_attribute('fill')
                if star_empty == 'none':
                    rating -= 1
            except Exception:
                pass
    except Exception:
        rating = -1

    # Read verification
    is_verified = 'đã xác thực' if n_likes > 0 else 'chưa xác thực'

    insert_new_review([review, is_verified, n_likes, rating, product_id])
    print('\t\t\t', review, is_verified, n_likes, rating)


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


