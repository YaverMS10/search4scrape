import gc
import os
import time
import pandas as pd
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import re
from selenium.webdriver.chrome.service import Service as ChromeService
from concurrent.futures import ThreadPoolExecutor
from webdriver_manager.chrome import ChromeDriverManager
import json
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.common.keys import Keys

def scrape(filtered_url):

    def extract_price(link_soup):
        try:
            price_div = link_soup.find('div', class_='product-price__i product-price__i--bold')
            if price_div:
                price_val = price_div.find('span', class_='price-val')
                price_cur = price_div.find('span', class_='price-cur')
                if price_val and price_cur:
                    price = re.sub(r'\s+', '', price_val.text.strip())  # Remove whitespace from the price value
                    currency = price_cur.text.strip()
                    return price, currency
        except Exception:
            pass
        return None, None


    def extract_information(link_soup):
        try:
            informations = link_soup.findAll('div', class_='product-properties__i')
            information = {}
            for info in informations:
                label_element = info.find('label', class_='product-properties__i-name')
                value_element = info.find('span', class_='product-properties__i-value')
                if label_element and value_element:
                    label = label_element.text.strip() if label_element is not None else "Unknown Label"
                    value = value_element.text.strip() if value_element is not None else "No Value"
                    information[label] = value
            return json.dumps(information, ensure_ascii=False)
        except Exception as e:
            # print(f"An error occurred: {e}")
            pass
            return None


    def extract_owner_name(link_soup):
        try:
            owner_name_div = link_soup.find('span', class_='product-shop__owner-name')
            if owner_name_div:
                owner_name = owner_name_div.text.strip()
                return owner_name
        except Exception:
            pass
        return None


    def extract_content(link_soup):
        try:
            # Find the specific div containing the content
            content_div = link_soup.find('div', class_='product-description__content')
            if content_div:
                # Extract text from all <p> tags and join them
                paragraphs = content_div.find_all('p')
                content = "\n".join(p.get_text(strip=True) for p in paragraphs)
                return content
        except Exception as e:
            print(f"An error occurred: {e}")
        return None


    def extract_statistics(link_soup):
        try:
            statistics = link_soup.find_all('span', class_='product-info__statistics__i-text')
            created_date = statistics[1].text.strip() if statistics else None
            views = statistics[2].text.strip() if statistics else None
            return created_date, views
        except Exception:
            pass
        return None, None


    def extract_owner_number(link_soup):
        try:
            phone_item_div = link_soup.find('li', class_='phone-numbers__i')
            phone_item = phone_item_div.find('a') if phone_item_div else None
            if phone_item and 'href' in phone_item.attrs:
                phone_number = phone_item['href'].replace('tel:', '').strip()
            else:
                phone_number = None
            return phone_number
        except Exception as e:
            print(f"An error occurred: {e}")  # Xətanın mesajını çap edin
            return None



    def extract_date_information(link_soup):
        try:
            date_div = link_soup.find_all('div', class_='about-ad-info__date')
            date1 = date_div[0].find_all('span')[1].text.strip()
            date2 = date_div[1].find_all('span')[1].text.strip()
            return date1, date2
        except Exception:
            pass
        return None, None


    def extract_product_title(link_soup):
        try:
            title_div = link_soup.find('h1', class_='product-title')
            if title_div:
                title = title_div.text.strip()
                return title
        except Exception:
            pass
        return None


    def extract_location(link_soup):
        try:
            location_div = link_soup.find('a', class_='shop--location')['href']
            query = urlparse(location_div).query
            params = parse_qs(query)
            if 'q' in params:
                lat, lng = params['q'][0].split(',')
                return float(lat), float(lng)
            else:
                return None
        except Exception as e:
            # print(f"An error occurred: {e}")
            pass
        return None, None


    def extract_property_info(url, item_id):
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--remote-debugging-pipe')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('no-sandbox')

            # service = ChromeService(ChromeDriverManager().install(), log_path=os.devnull)
            driver = webdriver.Chrome(service = ChromeService(ChromeDriverManager().install()), options=chrome_options)

            # Saytı açın və səhifənin tam yüklənməsini gözləyin
            driver.get(url)
            time.sleep(2)

            # 'show-phones' düyməsini gözləyin və klikləyin
            try:
                driver.execute_script("document.querySelector('.show-phones').click();")
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'phone-numbers__i')))

                # print("Waiting for the show button to be clickable.")
                # WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'js-show-phones')))
                # elements = driver.find_element(By.CLASS_NAME, 'js-show-phones')
                #
                # if elements:
                #     elements.click()
                #     print("Div clicked successfully.")
                # else:
                #     print("Show button not found for this listing.")
            except Exception as e:
                print(f"Error interacting with the element: {e}")
                return None

            # Sayfanın HTML kodunu BeautifulSoup ilə oxuyun
            updated_html = driver.page_source
            link_soup = BeautifulSoup(updated_html, 'html.parser')

            # # Məlumatları çıxarın
            phone_number = extract_owner_number(link_soup)
            owner_name = extract_owner_name(link_soup)
            information = extract_information(link_soup)
            price, cur = extract_price(link_soup)
            content = extract_content(link_soup)
            created_date, views = extract_statistics(link_soup)
            title = extract_product_title(link_soup)
            lat, lng = extract_location(link_soup)
            driver.quit()

            df1 = {
                'item_id': item_id,
                'title': title,
                'url': url,
                'phone_number': phone_number,
                'owner_name': owner_name,
                'price': price,
                'currency': cur,
                'information': information,
                'content': content,
                'views': views,
                'created_date': created_date,
                'latitude': lat,
                'longitude': lng
            }
            del item_id,title,url,phone_number,owner_name,price,cur,information,content,views,created_date,lat,lng,driver,link_soup
            return df1

        except Exception as e:
            print(f"An error occurred: {e}")
            return None


    async def main():
        chrome_options = Options()
        chrome_options.add_argument('--headless')

        # Initialize CSV file if it doesn't exist
        if not os.path.exists("tapaz.csv"):
            pd.DataFrame().to_csv("tapaz.csv", sep=',', encoding='utf-8', mode='w', index=False)

        semaphore = asyncio.Semaphore(5)  # Limit concurrent connections

        # Function to process individual items
        async def process_item(item):
            async with semaphore:
                link = 'https://tap.az' + item['href']
                item_id = item['href'].split('/')[-1]
                data = await loop.run_in_executor(executor, extract_property_info, link, item_id)
                if data:
                    df = pd.DataFrame([data])
                    df.to_csv("tapaz.csv", sep=',', encoding='utf-8', mode='a', header=False, index=False)

        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()

            service = ChromeService(ChromeDriverManager().install(), log_path=os.devnull)
            driver = webdriver.Chrome(service=service, options=chrome_options)
    
            driver.get(filtered_url)

            # try:
            #     WebDriverWait(driver, 10).until(
            #         EC.presence_of_element_located((By.CLASS_NAME, 'products-i'))
            #     )
            # except Exception as e:
            #     print(f"Error waiting for page load: {e}")
            #     driver.quit()
            #     return
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            content = soup.find_all('a', class_='products-link')
            element = driver.find_element(By.TAG_NAME,"html")
            # scroll_attempts = 0
            # max_attempts = 7
            # last_height = driver.execute_script("return document.body.scrollHeight")
            while len(content)<10:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "html")))
                element.send_keys(Keys.END)
                time.sleep(3)  # Wait for content to load
                element.send_keys(Keys.HOME)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                content = soup.find_all('a', class_='products-link')
            # last_height = driver.execute_script("return document.body.scrollHeight")
            # scroll_attempts = 0
            # max_attempts = 5  # Limit scrolling attempts to detect the end of content
            #
            # while True:
            #     driver.execute_script("window.scrollBy(0, 50);")
            #     time.sleep(3)  # Longer delay to allow full content to load
            #
            #     new_height = driver.execute_script("return document.body.scrollHeight")
            #
            #     # Stop scrolling when no new content appears after several attempts
            #     if new_height == last_height:
            #         scroll_attempts += 1
            #         if scroll_attempts >= max_attempts:
            #             break
            #     else:
            #         scroll_attempts = 0  # Reset if new content loads
            #
            #     last_height = new_height

            # Parse page source after scrolling
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            content = soup.find_all('a', class_='products-link')

            if len(content) > 11:
                content = content[:11]

            # Schedule tasks for each product link
            tasks = [process_item(item) for item in content]
            await asyncio.gather(*tasks)

            # Clean up
            driver.quit()
            del tasks, soup, driver, service
            gc.collect()

    asyncio.run(main())