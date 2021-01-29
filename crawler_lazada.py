import os
import sys
import time

import csv
import json

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
page_url = 'https://www.lazada.vn'
data_source = 'lazada'
positive_star = np.array(
    Image.open(os.path.join(working_dir, 'ratings', data_source, 'positive.png')))
negative_star = np.array(
    Image.open(os.path.join(working_dir, 'ratings', data_source, 'negative.png')))


def crawl_all_categories(driver):
    driver.get(page_url)

    # Scroll down to load all page
    simulate_scroll(driver, 5, 1)

    # Crawl
    categories_raw = driver.find_element_by_id("hp-categories")\
                        .find_elements_by_css_selector("[class='card-categories-li-content']")
    categories = []
    for cat_raw in categories_raw:
        category_info = [
            cat_raw.get_attribute('title'), 
            cat_raw.get_attribute('href')[::-1].split('/', 1)[-1][::-1],
            data_source
        ]
        insert_new_category(category_info)
        categories.append(category_info)
    return categories


def crawl_single_product(driver, product_url: str, product_id: int):
    print(f"\n\n\nLoading\n\t{product_url}")
    driver.get(product_url)

    # Scroll down to load all page
    simulate_scroll(driver)

    page_id, max_pages = 1, 19
    while page_id <= max_pages:
        try:
            print(f"\n\t\tCrawling page {page_id} ...")
            # Get the review details
            WebDriverWait(driver, timeout=random.randint(6,9)).until(
                method=expected_conditions.visibility_of_all_elements_located(
                    locator=(By.CSS_SELECTOR, "div.item")
                )
            )
        except Exception:
            print("Can't find any review!")
            break

        # Get product reviews
        all_reviews = driver.find_elements_by_css_selector("[class='item']")
        for raw_review in all_reviews:
            # Read review content
            content = raw_review.find_element_by_css_selector("[class='item-content']")
            # print(BS(content.get_attribute('innerHTML'), features="html5lib").prettify())
            review = content.find_element_by_css_selector("[class='content']").text
            
            # Filter-out non-text reviews
            if not (review != '' or review.strip()):
                continue

            # Read number of likes for this review
            n_likes = content.find_element_by_css_selector("[class='left']")\
                                .find_element_by_css_selector("[class='']").text
            # n_likes = content.find_element_by_xpath('//span[@class="left"]/span/span[@class=""]').text

            # Read rating
            rating = 0
            stars = raw_review.find_element_by_css_selector("[class='top']")\
                                .find_elements_by_css_selector("[class='star']")
            # stars = raw_review.find_elements_by_xpath('//div[@class="top"]/div/img[@class="star"]')
            for star in stars:
                star_url = star.get_attribute('src')
                star_image = Image.open(BytesIO(requests.get(url=star_url).content))
                rating += numberize_visual_star(star_image, positive_star, negative_star)

            # Read verification
            is_verified = 'chưa xác thực'
            try:
                is_verified = raw_review.find_element_by_css_selector("[class='middle']")\
                                        .find_element_by_css_selector("span.verify").text
            except Exception:
                pass

            insert_new_review([review, is_verified, n_likes, rating, product_id])
            print('\t\t\t', review, is_verified, n_likes, rating, product_id)

        try:
            # Check out-of-page
            button_next_css = "button.next-pagination-item.next"
            check_disabled_next_page = driver.find_elements_by_css_selector(button_next_css+"[disabled]")
            if len(check_disabled_next_page) > 0:
                break
            button_next = WebDriverWait(driver, timeout=random.randint(6,9)).until(
                method=expected_conditions.visibility_of_element_located(
                    locator=(By.CSS_SELECTOR, button_next_css)
                )
            )
            driver.execute_script("arguments[0].click();", button_next)
            random_sleep()
            page_id += 1
        except TimeoutException:
            break


def crawl_single_category(driver, category_url: str, category_id: int):
    
    print(f"\n\n\nLoading\n\t{category_url}")
    driver.get(category_url)

    # Scroll down to load all page
    simulate_scroll(driver)

    category_url += '/?page={}'
    all_products = []
    page_id, max_pages = 1, 69
    while page_id <= max_pages:
        try:
            print(f"\n\n\nCrawling page {page_id} ...")
            # Get the review details
            WebDriverWait(driver, timeout=random.randint(6,9)).until(
                method=expected_conditions.visibility_of_all_elements_located(
                    locator=(By.CSS_SELECTOR, '[data-qa-locator="product-item"]')
                )
            )
        except Exception:
            print("Can't find any review!")
            break

        # Get product info
        products_raw = driver.find_elements_by_css_selector('[data-qa-locator="product-item"]')
        for product_raw in products_raw:
            product_data = product_raw.find_element_by_css_selector('div.c16H9d')\
                                        .find_element_by_tag_name('a')
            product_info = [
                product_data.get_attribute('title'), 
                product_data.get_attribute('href').split('?', 1)[0],
                category_id
            ]
            insert_new_product(product_info)
            all_products.append(product_info)

            # open new tab
            current_tab = driver.current_window_handle
            driver.execute_script("window.open('');") 
            driver.switch_to.window(driver.window_handles[-1])

            # crawl products' reviews per category
            query = f'SELECT id FROM products WHERE title = "{product_info[0]}" AND category_id = "{category_id}"'
            execute_sql(query)
            product_id = db_cursor.fetchone()[0]
            crawl_single_product(driver, product_info[1], product_id)

            # close tab
            driver.close() 
            driver.switch_to.window(current_tab)

        try:
            random_sleep()
            page_id += 1
            driver.get(category_url.format(page_id))

            # Check out-of-page
            content = driver.find_element_by_tag_name('html')
            html_content = BS(content.get_attribute('innerHTML'), features="html5lib").get_text()
            if any(ss in html_content.lower() for ss in ['sorry', 'cannot find', 'any matches', 'no result']):
                break
        except Exception as e:
            print(e)
            break


if __name__ == "__main__":

    # Step 0: Initialize
    initialize_db()
    driver = initialize_driver()

    # Step 1: Get all categories in main page
    all_categories = crawl_all_categories(driver)

    # Step 2: Get products per categories page-by-page, then crawl their info & reviews
    main_page = driver.current_window_handle
    random.shuffle(all_categories)
    for category_info in all_categories:
        # open new tab
        driver.execute_script("window.open('');") 
        driver.switch_to.window(driver.window_handles[-1])
        random_sleep()

        # crawl products' reviews per category
        query = f'SELECT id FROM categories WHERE title = "{category_info[0]}" AND source = "{data_source}"'
        execute_sql(query)
        category_id = db_cursor.fetchone()[0]

        crawl_single_category(driver, category_info[1], category_id)
        random_sleep()

        # close current tab
        driver.close() 
        driver.switch_to.window(main_page)

    driver.close()
    db_connector.close()



