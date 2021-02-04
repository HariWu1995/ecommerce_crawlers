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
from selenium.webdriver import ActionChains
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
page_url = 'https://www.sendo.vn/sitemap'
data_source = 'sendo'


def detect_popup_window(driver):
    buttons = driver.find_elements_by_tag_name('button')
    if len(buttons) > 0:
        for button in buttons:
            button_name = button.get_attribute('class').lower()
            if button_name in ['closeBtn_2C0k', 'acceptBtn_gJkT']:
                return button
    return None


def crawl_all_categories(driver):
    driver.get(page_url)

    # Scroll down to load all page
    simulate_scroll(driver, 5, 1)

    # Crawl
    categories = []
    categories_groups = driver.find_elements_by_css_selector('[class="title_140g"]')
    for cat_group in categories_groups:
        cat_raw = cat_group.find_element_by_tag_name('a')
        category_info = [
            cat_raw.text.lower(), 
            cat_raw.get_attribute('href'),
            data_source
        ]
        insert_new_category(category_info)
        categories.append(category_info)
    return categories


def crawl_single_category(driver, category_url: str, category_id: int):

    category_url += '?page={}&sortType=norder_30_desc'
    all_products = []
    page_id, max_pages = 1, 69
    while page_id <= max_pages:
        
        # Go to next page
        print(f"\n\n\nLoading\n\t{category_url.format(page_id)}")
        driver.get(category_url.format(page_id))
        simulate_scroll(driver, 19, 0, 0.69, 0.96)
        page_id += 1

        # Check
        product_css = '[class="item_3x07"]'
        products_raw = driver.find_elements_by_css_selector(product_css)
        if len(products_raw) < 1:
            print("Can't find any item!")
            break

        # Get product info
        for product_raw in products_raw:
            try:
                product_url = product_raw.get_attribute('href').split('?', 1)[0]
                product_title = product_raw.find_element_by_css_selector('[class="productName_u171"]')\
                                            .find_element_by_tag_name('span')
                product_title = clean_html(product_title.get_attribute('innerHTML'))
                if not (product_title != '' or product_title.strip()):
                    continue
                product_info = [product_title, product_url, category_id]
                insert_new_product(product_info)
                all_products.append(product_info)
            except Exception:
                print("Cannot crawl product")
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
            # try:
            crawl_single_product(driver, product_info[1], product_id)
            # except Exception as e:
            #     print("Error while crawl\n\t"+product_info[1]+'\n'+str(e))

            # close tab
            driver.close() 
            driver.switch_to.window(current_tab)


def crawl_single_product(driver, product_url: str, product_id: int):
    print(f"\n\n\nLoading\n\t{product_url}")
    driver.get(product_url)

    # Scroll down to load all page
    simulate_scroll(driver, 3, 0, 0.69, 0.96)
    
    # Change tab to review
    tabs = driver.find_element_by_id('productTab').find_elements_by_tag_name('li')
    for tab in tabs:
        try:
            tab_type = tab.find_element_by_tag_name('a')
        except Exception:
            continue
        tab_active = True if 'active' in tab_type.get_attribute('class') else False
        tab_name = tab_type.get_attribute('innerHTML')
        if tab_name.lower() == 'đánh giá' and not tab_active:
            driver.execute_script("arguments[0].click();", tab_type)

    page_id, max_pages = 1, 69
    while page_id <= max_pages:
        simulate_scroll(driver, 5, 3, 0.69, 0.96)
        print(f"\n\t\tCrawling page {page_id} ...")
        reviews = driver.find_elements_by_css_selector('[class="feedback_1zvX"]')
        if len(reviews) < 1:
            print("Can't find any review!")
            break
    
        # Get product reviews
        all_reviews = driver.find_elements_by_css_selector('[class="commentItem_1CVD"]')
        for raw_review in all_reviews:
            try:
                crawl_single_review(raw_review, product_id)
            except Exception as e:
                print("Error while crawling comment\n\t"+str(e))

        try:
            page_buttons = driver.find_elements_by_tag_name('button')
            for page_button in page_buttons:
                page_button_id = page_button.get_attribute("innerHTML")
                page_button_id = re.sub('[^0-9]', '', page_button_id)
                if page_button_id == '':
                    continue
                if int(page_button_id) > page_id:
                    page_button.click()
                    random_sleep()
                    page_id = int(page_button_id)
                    break
        except Exception as e:
            print("\n\t\tOut-of-page Error: "+str(e))
            break


def crawl_single_review(raw_review, product_id):

    content = raw_review.find_element_by_xpath('..')

    # Read review content
    review = raw_review.find_element_by_css_selector('[class="feedback_1zvX"]')\
                        .find_element_by_tag_name('p')\
                        .get_attribute("innerHTML")
    
    # Filter-out non-text reviews
    if not (review != '' or review.strip()):
        print('\t\t\tReview is empty')
        return None
    review = review.replace('\n', ' . ').replace('\t', ' . ')

    # Read number of likes for this review
    try:
        n_likes = content.find_element_by_css_selector('[class="groupAction_3bpK"]')\
                            .find_elements_by_tag_name('button')[1]\
                            .find_element_by_tag_name('span')\
                            .get_attribute("innerHTML")
        n_likes = re.sub('[^0-9]', '', n_likes)
        if n_likes == '':
            n_likes = 0
        else:
            n_likes = int(n_likes)
    except Exception:
        n_likes = -1

    # Read rating
    try:
        rating = 5
        stars = content.find_element_by_xpath('//*[@class="cardHeader_RuvN"]/div[2]/div')\
                        .get_attribute("class")
        stars = stars.split(' ')[1].split('_')[0].replace('star', '')
        if stars == '':
            rating = 0
        else:
            rating = int(int(stars)/4)
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
    print(f"Categories crawled: {crawled_category_ids}")
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
        query = f'SELECT id FROM categories WHERE url = "{category_info[1]}" AND source = "{data_source}"'
        execute_sql(query)
        category_id = db_cursor.fetchone()[0]
        crawl_single_category(driver, category_info[1], category_id)
        random_sleep()
        print(f'Finish crawling {category_info[1]} at {data_source}')

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
            print("\n\n\nCrash ... Please wait a few seconds!!!")
            for t in print_progress(range(69)):
                time.sleep(1)
        
        driver.quit()
    db_connector.close()



