import pandas as pd
import openai
import ast
import json
import requests
import os
from dotenv import load_dotenv

import bina_scraping, tapaz_scraping
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

load_dotenv()
app = FastAPI()

openai.api_key = os.getenv('openai_key')

class SearchRequest(BaseModel):
    user_input: str

class ScrapingResult(BaseModel):
    source: str
    data: list

with open('instructions.txt', 'r') as file:
    instruction = file.read()

@app.post('/search', response_model=ScrapingResult)
def search(request: SearchRequest):
    user_input = request.user_input

    try:
        response = openai.ChatCompletion.create(
              model="gpt-4o-mini",
              messages=[{"role": "system", "content": instruction},
                        {"role": "user", "content": user_input}])
        features_dict = ast.literal_eval(response['choices'][0]['message']['content'])

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API Error: {str(e)}")

    if features_dict['category'] == 'house':
        return handle_house_search(features_dict)
    elif features_dict['category'] == 'other':
        return handle_other_search(features_dict)
    else:
        raise HTTPException(status_code=400, detail="Invalid category")

def handle_house_search(features_dict):
    category_parser = {"Menzil": "menziller", "Yeni Tikili": "menziller/yeni-tikili", "Kohne Tikili": "menziller/kohne-tikili", "Heyet Evi": "heyet-evleri", "Ofis": "ofisler", "Qaraj": "qarajlar", "Torpaq": "torpaqlar", "Obyekt": "obyektler"}

    cat = features_dict['type']
    price_min = features_dict['price_min']
    price_max = features_dict['price_max']

    url_bina =  f"https://bina.az/baki/alqi-satqi/{category_parser[cat]}?page&price_from={price_min}"
    if price_max > 0:
        url_bina += f"&price_to={price_max}"

    if os.path.exists('final_df.csv'):
        os.remove('final_df.csv')

    try:
        final_list = []
        bina_scraping.parse(url_bina)
        results_list = pd.read_csv('final_df.csv', header=None).to_dict(orient = "records")
        if os.path.exists('final_df.csv'):
            os.remove('final_df.csv')

        for i in range(len(results_list)):
            final_list.append({"Satan:": f"{results_list[i][3]} ({results_list[i][4]})",
                               "Qiymət:": f"{results_list[i][5]} {results_list[i][7]}",
                               "Elan Linki:": results_list[i][1], "Əlaqə Nömrəsi:": results_list[i][2],
                               "Detallar:": results_list[i][10]})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping Error: {str(e)}")
    
    return {"source": "Bina.az", "data": final_list}

def handle_other_search(features_dict):
    search = features_dict['item']
    price_min = features_dict['price_min']
    price_max = features_dict['price_max']

    url_tapaz = f"https://tap.az/elanlar?q%5Bprice%5D%5B%5D={price_min}&q%5Bprice%5D%5B%5D={price_max}&q%5Bkeywords%5D=" + str(r"%20".join(search.split(" ")))
    if price_max == 0:
        url_tapaz = f"https://tap.az/elanlar?q%5Bprice%5D%5B%5D={price_min}&q%5Bkeywords%5D=" + str(r"%20".join(search.split(" ")))

    if(os.path.exists('tapaz.csv') and os.path.isfile('tapaz.csv')): 
        os.remove('tapaz.csv') 

    try:
        final_list = []
        tapaz_scraping.scrape(url_tapaz)
        results_list = pd.read_csv('tapaz.csv', header=None).to_dict(orient = "records")
        if os.path.exists('tapaz.csv'):
            os.remove('tapaz.csv')

        for i in range(len(results_list)):
            final_list.append({"Elan Başlığı:": results_list[i][1],
                               "Elan Linki:": results_list[i][2],
                               "Əlaqə Nömrəsi:": results_list[i][3],
                               "Qiymət:": f"{results_list[i][5]} {results_list[i][6]}",
                               "Ünvan": ast.literal_eval(results_list[i][7])["Şəhər"],
                               "Tarix": results_list[i][10],
                               "Detallar": results_list[i][8]})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tap.az Scraping Error: {str(e)}")

    url = "https://google.serper.dev/search"

    payload = json.dumps({
    "q": "site:instagram.com " + search,
    "gl": "az",
    "hl": "az"
    })
    headers = {
    'X-API-KEY': os.getenv('x_key'),
    'Content-Type': 'application/json'
    }

    try:
        instagram_list = []
        response = requests.request("POST", url, headers=headers, data=payload)
        response_json = ast.literal_eval(response.text)
        instagram_data = response_json['organic']
        for item in response_json['organic']:
            try:
                date = item['date']
            except:
                date = "Bilinmir"

            instagram_list.append({"Elan Başlığı:": item["title"], "Link:": item['link'], "Tarix": date})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Instagram Search Error: {str(e)}")
    
    combined_results = {
        "source": "Tap.az + Instagram",
        "data": final_list + instagram_list}

    return combined_results