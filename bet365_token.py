import asyncio
import re
from datetime import datetime
import requests
from time import time,sleep
from pyppeteer import launch
import random
import sys
import traceback
import os


proxies_residential = []
user_agents = []
proxies = []

# with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxies.txt"), "r") as f:
#     proxies = [line.strip() for line in f.readlines()]

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_agents.txt"), "r") as f:
    user_agents = [line.strip() for line in f.readlines()]
        

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxies_residential.txt"), "r") as f:
    proxies_residential = [line.strip() for line in f.readlines()]

# def get_proxy():
#     random_proxy = random.choice(proxies)
#     ip,port,username,password = random_proxy.split(":")
#     url_proxy = "http://{2}:{3}@{0}:{1}".format(ip,port,username,password)
#     return url_proxy

def get_residential_proxy():
    return "http://"+random.choice(proxies_residential)


async def get_token():
    browser = await launch(
        headless=True,
        # args=['--disable-blink-features=AutomationControlled','--no-sandbox','--proxy-server='+get_residential_proxy()],
        args=['--disable-blink-features=AutomationControlled','--no-sandbox'],

    )
    try:
        page = (await browser.pages())[0]
        await page.setUserAgent(
            random.choice(user_agents)
        )
        request = await page.goto("https://www.bet365.it")
        request = await page.waitForRequest(lambda r: 'SportsBook' in r.url)
        
        await browser.close()
        return request.headers["x-net-sync-term"]
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exception(exc_type, exc_obj, exc_tb)
        await browser.close()
        return ""
        
    
while 1:
    try:
        token = asyncio.get_event_loop().run_until_complete(get_token())
        print(token)
        if token:
            with open("./sync_token.txt", "w") as f:
                f.write(token)
            sleep(6*50)
        else:
            sleep(5)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exception(exc_type, exc_obj, exc_tb)
        sleep(5)
        continue
    except KeyboardInterrupt:
        sys.exit()
