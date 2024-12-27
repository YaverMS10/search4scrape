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
import gc
import json
import psutil


def parse(filtered_url):

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


    def extract_owner_category(link_soup):
        try:
            owner_category_div = link_soup.find('div', class_='product-owner__info-region')
            if owner_category_div:
                owner_category = owner_category_div.text.strip()
                return owner_category
        except Exception:
            pass
        return None


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
            print(f"An error occurred: {e}")
            pass
            return None


    def extract_owner_name(link_soup):
        try:
            owner_name_div = link_soup.find('div', class_='product-owner__info-name')
            if owner_name_div:
                owner_name = owner_name_div.text.strip()
                return owner_name
        except Exception:
            pass
        return None


    def extract_phone_number(link_soup):
        try:
            phone_number_div = link_soup.find('div', class_='product-phones__list-i')
            phone_number_a = phone_number_div.find('a') if phone_number_div else None
            phone_number = phone_number_a['href'].replace('tel:', '').replace('-', '').replace(' ',
                                                                                            '') if phone_number_a else None
            return phone_number
        except Exception:
            pass
        return None


    def extract_location(link_soup):
        try:
            latitude = link_soup.find('div', {'id': 'item_map'})['data-lat']
            longitude = link_soup.find('div', {'id': 'item_map'})['data-lng']
            return latitude, longitude
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
            statistics = link_soup.findAll('span', class_='product-statistics__i-text')
            updated_date = statistics[0].text.strip() if statistics[0] else None
            views = statistics[1].text.strip() if statistics[1] else None
            return updated_date, views
        except Exception:
            pass
        return None, None


    def extract_property_info(url, item_id):
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-dev-shm-usage')
            # service = ChromeService(ChromeDriverManager().install(), log_path=os.devnull)
            driver = webdriver.Chrome(options=chrome_options)

            driver.get(url)
            time.sleep(2)

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'product-phones__btn-value')))

            element = driver.find_element(By.CLASS_NAME, 'product-phones__btn-value')
            element.click()

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'product-phones__list-i')))

            updated_html = driver.page_source

            link_soup = BeautifulSoup(updated_html, 'html.parser')

            phone_number_a = link_soup.find('div', class_='product-phones__list-i').find('a')
            phone_number = phone_number_a['href'].replace('tel:', '').replace('-', '').replace(' ',
                                                                                            '') if phone_number_a else None
            owner_name = extract_owner_name(link_soup)

            owner_category = extract_owner_category(link_soup)

            information = extract_information(link_soup)
            price, currency = extract_price(link_soup)
            latitude, longitude = extract_location(link_soup)
            content = extract_content(link_soup)
            updated_date, views = extract_statistics(link_soup)
            driver.quit()
            df = {
                'item_id': item_id,
                'url': url,
                'phone_number': phone_number,
                'owner_name': owner_name,
                'owner_category': owner_category,
                'price': price,
                'information': information,
                'currency': currency,
                'latitude': latitude,
                'longitude': longitude,
                'content': content,
                'updated_date': updated_date,
                'views': views
            }
            del item_id, price, currency, latitude, longitude, content, updated_date, views, information, phone_number, url, driver, link_soup
            return df

        except Exception as e:
            print(f"An error occurred: {e}")
            return None


    def cleanup_chrome_processes():
        """Kill all remaining chrome.exe and chromedriver processes."""
        # os.system('taskkill /F /IM chrome.exe')  # Kill chrome.exe
        # os.system('taskkill /F /IM chromedriver.exe')
        for proc in psutil.process_iter():
            try:
                if proc.name() in ["chrome.exe", "chromedriver.exe"]:
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                print(e)
                pass


    async def main():
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-dev-shm-usage')

        if not os.path.exists("final_df.csv"):
            pd.DataFrame().to_csv("final_df.csv", sep=',', encoding='utf-8', mode='w', index=False)

        semaphore = asyncio.Semaphore(30)

        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()

            async def process_item(item, page):
                async with semaphore:
                    link = 'https://bina.az' + item.a['href']
                    item_id = item.a['href'].split('/')[-1]
                    data = await loop.run_in_executor(executor, extract_property_info, link, item_id)
                    if data:
                        data['page'] = page
                        df = pd.DataFrame([data])
                        df.to_csv("final_df.csv", sep=',', encoding='utf-8', mode='a', header=False, index=False)
                        del df, data

            count_item = 0
            for page in range(1, 3):
                if count_item > 10:
                    break

                print(f"Scraping page {page}...")
                print(filtered_url)
                url = filtered_url.split("page")[0] + f"page={page}" + filtered_url.split("page")[1]
                print(url)
                service = ChromeService(ChromeDriverManager().install(), log_path=os.devnull)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                driver.get(url)
                time.sleep(2)

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                content = soup.find_all('div', class_='items-i')
                count_item += len(content)

                driver.quit()

                if len(content) > 11:
                    content = content[:11]

                tasks = [process_item(item, page) for item in content]
                await asyncio.gather(*tasks)
                del content, soup, tasks, driver
                gc.collect()

                # if page % 10 == 0:
                #     print("Completed 100 pages. Taking a 1-minute break...")
                #     time.sleep(60)
                #     cleanup_chrome_processes()
                #     time.sleep(60)

    asyncio.run(main())