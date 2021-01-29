import os

from selenium import webdriver
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import *
from selenium.common.exceptions import *

from proxy_rotator import *


working_dir = os.path.dirname(__file__)
path2drivers = os.path.join(working_dir, 'drivers')


def initialize_driver(browser_choice: str='firefox', use_proxy: bool=False):

    if use_proxy:
        # Generate proxy IP address
        random_proxy = proxy_generator()
        print(f'Use proxy: {random_proxy}')
        proxy_info = Proxy()
        proxy_info.proxy_type = ProxyType.MANUAL
        proxy_info.http_proxy = random_proxy
        # proxy_info.socks_proxy = random_proxy
        proxy_info.ssl_proxy = random_proxy

    driver_args = dict()
    if browser_choice == 'chrome':
        # Download ChromeDriver on 
        #     https://sites.google.com/a/chromium.org/chromedriver/downloads
        from selenium.webdriver import Chrome as WebDriver

        if use_proxy:
            options = webdriver.chrome.options.Options()
            options.Proxy = proxy_info
            options.add_argument("ignore-certificate-errors")
            options.add_argument("window-size=690,690")
            driver_args['chrome_options'] = options
        driver_args['executable_path'] = os.path.join(path2drivers, 'chromedriver.exe')
        driver_args['desired_capabilities'] = webdriver.DesiredCapabilities.CHROME

    elif browser_choice in ['firefox', 'gecko']:
        # Download GeckoDriver on
        #     https://github.com/mozilla/geckodriver/releases
        from selenium.webdriver import Firefox as WebDriver

        driver_args['executable_path'] = os.path.join(path2drivers, 'geckodriver.exe')
        driver_args['desired_capabilities'] = webdriver.DesiredCapabilities.FIREFOX

    else:
        # Download MSEdgeDriver on
        #     https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
        from selenium.webdriver import Edge as WebDriver

        driver_args['executable_path'] = os.path.join(path2drivers, 'msedgedriver.exe')
        # driver_args['desired_capabilities'] = webdriver.DesiredCapabilities.EDGE

    if not use_proxy:
        driver = WebDriver(executable_path=driver_args['executable_path'])
        driver.set_window_size(690, 960)
        return driver

    if browser_choice in ['chrome', 'firefox', 'gecko']:
        proxy_info.add_to_capabilities(driver_args['desired_capabilities'])
    driver = WebDriver(**driver_args)
    driver.set_window_size(690, 960)
    return driver









