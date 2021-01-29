import os
import sys
import subprocess

import socket
import requests
from bs4 import BeautifulSoup as BS

from random import choice as rand_list


def proxy_generator():
    proxy_page = 'https://sslproxies.org/'
    proxies_soup = BS(requests.get(proxy_page).content, 'html5lib')

    proxies_raw = proxies_soup.findAll('td')[::8]
    ports_raw = proxies_soup.findAll('td')[1::8]
    proxy_port_map = list(zip(map(lambda x: x.text, proxies_raw), map(lambda x: x.text, ports_raw))) 
    proxy_port_map = list(map(lambda x: f'{x[0]}:{x[1]}', proxy_port_map))
    return rand_list(proxy_port_map)


def get_ip_and_hostname():
    hostname =  socket.gethostname()
    ip_addr = socket.gethostbyname(hostname)
    return ip_addr, hostname

if __name__ == "__main__":
    ip_addr, hostname = get_ip_and_hostname()
    print(ip_addr)
    print(hostname)









