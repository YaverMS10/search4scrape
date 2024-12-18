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
import psutil
import gc

def scrape(filtered_url):

    def extract_price(link_soup):
        try:
            price_div = link_soup.find('p', class_='LFHeading')
            if price_div:
                price_val = price_div.text.strip()
                if price_val:
                    return price_val
        except Exception:
            pass
        return None


    def extract_information(link_soup):
        try:
            informations = link_soup.find('ul', class_='details-page__params')
            information = {}
            if informations:
                for info in informations.find_all('li'):
                    label_element = info.find('p')
                    value_element = info.find('a')
                    if label_element and value_element:
                        label = label_element.text.strip() if label_element else "Unknown Label"
                        value = value_element.text.strip() if value_element else "No Value"
                        information[label] = value

            return json.dumps(information, ensure_ascii=False)

        except Exception as e:
            print(f"An error occurred: {e}")
            return None


    def extract_owner_name(link_soup):
        try:
            owner_name_div = link_soup.find('span', class_='userName-text')
            if owner_name_div:
                owner_name = owner_name_div.text.strip()
                return owner_name
        except Exception:
            pass
        return None


    def extract_content(link_soup):
        try:
            # Find the specific div containing the content
            content_div = link_soup.find('div', class_='description__wrap')
            if content_div:
                # Extract text from all <p> tags and join them
                paragraphs = content_div.find('span')
                content = "\n".join(p.get_text(strip=True) for p in paragraphs)
                return content
        except Exception as e:
            print(f"An error occurred: {e}")
        return None


    def extract_statistics(link_soup):
        try:
            statistics = link_soup.find('div', class_='impressions').find('span')
            views = statistics.text.strip() if statistics else None
            return views
        except Exception:
            pass
        return None, None


    def extract_owner_number(link_soup):
        try:
            phone_item_div = link_soup.find('div', class_='phone-number__wrap')
            if phone_item_div:
                phone_number_a = phone_item_div.find('a')['href']
                if phone_number_a:
                    phone_number = phone_number_a.replace('tel:', '').strip()
                else:
                    phone_number = None
            else:
                phone_number = None
            return phone_number
        except Exception as e:
            print(f"An error occurred: {e}")
            phone_number = None
            return phone_number


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
            title_div = link_soup.find('h1', class_='ad-detail-title')
            if title_div:
                title = title_div.text.strip()
                return title
        except Exception:
            pass
        return None


    def extract_property_info(url, item_id):
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            # service = ChromeService(ChromeDriverManager().install(), log_path=os.devnull)
            driver = webdriver.Chrome(options=chrome_options)

            driver.get(url)
            time.sleep(2)

            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'show-button')))
            elements = driver.find_elements(By.CLASS_NAME, 'show-button')
            if elements:
                element = elements[0]
                element.click()
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'phone-item')))
            else:
                print("Show button not found for this listing.")
            updated_html = driver.page_source
            link_soup = BeautifulSoup(updated_html, 'html.parser')
            phone_number = extract_owner_number(link_soup)
            owner_name = extract_owner_name(link_soup)
            information = extract_information(link_soup)
            price = extract_price(link_soup)
            content = extract_content(link_soup)
            views = extract_statistics(link_soup)
            created_date, updated_date = extract_date_information(link_soup)
            title = extract_product_title(link_soup)
            driver.quit()
            df1 = {'item_id': item_id, 'title': title, 'url': url,
                'phone_number': phone_number,
                'owner_name': owner_name,
                'price': price,
                'information': information, 'content': content, 'views': views, 'created_date': created_date,
                'updated_date': updated_date}
            del item_id,title,url,phone_number,owner_name,price,information,content,views,created_date,updated_date,driver,link_soup
            return df1

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
        chrome_options.add_argument('--headless')

        if not os.path.exists("lalafo.csv"):
            pd.DataFrame().to_csv("lalafo.csv", sep=',', encoding='utf-8', mode='w', index=False)
        semaphore = asyncio.Semaphore(30)
        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()

            async def process_item(item):
              async with semaphore:
                link = 'https://lalafo.az' + item['href']
                item_id = item['href'].split('-')[-1]
                data = await loop.run_in_executor(executor, extract_property_info, link, item_id)
                if data:
                    data['page'] = page
                    df = pd.DataFrame([data])
                    df.to_csv("lalafo.csv", sep=',', encoding='utf-8', mode='a', header=False, index=False)
                    del df, data


            for page in range(1, 3):
                print(f"Scraping page {page}...")
                url = filtered_url + f'?page={page}'
                service = ChromeService(ChromeDriverManager().install(), log_path=os.devnull)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                driver.get(url)
                time.sleep(5)
                # try:
                #     WebDriverWait(driver, 10).until(
                #         EC.presence_of_element_located((By.CLASS_NAME, 'lf-ad-tile__link'))
                #     )
                # except Exception as e:
                #     print(f"Error waiting for page load: {e}")
                #     driver.quit()
                #     continue
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                content = soup.find_all('a', class_='ad-tile-horizontal')

                tasks = [process_item(item) for item in content]
                await asyncio.gather(*tasks)
                driver.quit()
                del content, soup, tasks , driver
                gc.collect()
                # if page % 10 == 0:
                #     print("Completed 100 pages. Taking a 1-minute break...")
                #     time.sleep(60)
                #     cleanup_chrome_processes()
                #     time.sleep(60)


    start_time = time.time()
    asyncio.run(main())
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time} seconds")