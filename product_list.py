from selenium import webdriver
from selenium.webdriver.common.by import By
import os, re, openai, time, csv
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import requests

load_dotenv('search.config')
openai_key = os.getenv('OPNEAI_KEY')
condition = os.getenv('CONDITION_NEW')
part_name = os.getenv('PART_COLLECTION')

cars = os.getenv('CAR')

from_easyesarch = os.getenv('GET_CARS_FROM_EASYSEARCH_DB')
easyesarch_file = os.getenv('EASYSEARCH_DB')

xlsx_file_path = os.getenv('SEARCH_RESULT')

openai.api_key = openai_key

async def fetch(url):
    # Create HTTP session
    async with aiohttp.ClientSession() as session:
        # Make GET request using session
        async with session.get(url) as response:
            # Return text content
            return await response.text()

# Get each part numbers from part number string
def get_part_number(part_number_string):
    if part_number_string.strip().lower() == "Does not apply" or part_number_string.strip().lower() == 'N/A' or part_number_string.strip().lower() == 'N / A':
        return None
    elif " , " in part_number_string:
        numbers = part_number_string.split(" , ")
    elif ", " in part_number_string:
        numbers = part_number_string.split(", ")
    elif "," in part_number_string:
        numbers = part_number_string.split(",")
    elif " / " in part_number_string:
        numbers = part_number_string.split(" / ")
    elif "/ " in part_number_string:
        numbers = part_number_string.split("/ ")
    elif "/" in part_number_string:
        numbers = part_number_string.split("/")
    else:
        numbers = [part_number_string]
    
    return_numbers =[i.strip() for i in numbers]
    return return_numbers

# Check Part Number and OEM Part Number with URL 
async def check_part_number_and_oem_number(url):
    content = await fetch(url)
    soup = BeautifulSoup(content, 'html.parser')

    # GET Title of product
    # Extract deatiled infos
    info  = soup.select("div#viTabs_0_is.vim.x-about-this-item div.ux-layout-section-module-evo div.ux-layout-section-evo.ux-layout-section--features")
    product_info = {}
    for i in info:
        details = i.select("div.ux-layout-section-evo__col")
        for y in details:
            label = y.select("div.ux-labels-values__labels-content span")
            value = y.select("div.ux-labels-values__values-content span")
            if len(label):
                product_info[label[0].text] = value[0].text
    # Part Number and OEM Part Number
    OEM_part_number = get_part_number(product_info.pop("OE/OEM Part Number")) if "OE/OEM Part Number" in product_info else None
    # Manufacturer Part Number

    return OEM_part_number

async def get_search_result_on_ebay(condition, part_name, car_maker, car_model, car_year):
    url = f'https://www.ebay.com/sch/i.html?_nkw={"+".join(part_name.split(" "))}+{"+".join(car_maker.split(" "))}+{"+".join(car_model.split(" "))}+{car_year}{ "&LH_ItemCondition=3" if condition.lower()=="true" else "&LH_ItemCondition=4"}&_ipg=240'
    print(f'[Info] Search URL: {url}')
    content = await fetch(url)
    soup = BeautifulSoup(content, 'html.parser')
    info  = soup.select("div.s-item__info.clearfix")
    result= []

    for i in info:
        product_item = {}
        title = i.select("div.s-item__title")[0]
        product_item["title"] = title.select("span")[0].text
        product_item["url"] = i.select('a')[0].get_attribute_list('href')[0]
        result.append(product_item)

    print(f'[Info] Candidate Products: {len(result)}')
    return result

def check_years_from_title(title, require_year):
    years = []
    year = datetime.now().year
    for i in re.findall(r'\b\d{4}\b|\b\d{2}\b', title):
        if len(i)==2:
            if int("20"+ i) > year:
                can_year = "19" + i
            else:
                can_year = "20" + i
            try:
                if int(can_year) > max(years):
                    years.append(int(can_year))
            except:
                years.append(int(can_year))
        else:
            if int(i) < year:
                try:
                    if int(i) > max(years):
                        years.append(int(i))
                except:
                    years.append(int(i))

    car_years = []
    if not years:
        return True
    elif len(years) ==  1:
        if years[0] == require_year:
            return True
        else:
            return False
    else:
        if min(years) <= int(require_year) and int(require_year) <= max(years):
            return True
        else:
            return False

def check_model_from_title(title, car_model):
    models = re.split(r'(\d+)', car_model)
    if car_model.lower() in title.lower():
        return True
    else:
        if len(models) == 1:
            return False
        else:
            new_model = f'{models[0]} {"".join(models[1::])}'
            if new_model.lower() in title.lower():
                return True
            else:
                return False  

def compare_collection_title(title, collection):
    num = 0
    for i in collection.split(" "):
        if i.lower() in title.lower():
            num = num + 1
    # if collection.lower() in title.lower():
    #     return True
    # else:
    #     return False
    return num/len(collection.split(" "))

async def main(require_cars):
    result = {}
    for car in require_cars:
        print(f'------------Start searching production for {" ".join(car)} -----------------')
        car_self = {}
        search_result = await get_search_result_on_ebay(condition=condition, part_name=part_name, car_maker=car[0], car_model=car[1], car_year=car[2])
        select = False
        print(f'[Info] Check search result')
        for i in search_result:
            title = i["title"]
            url = i["url"]
            maker = True if car[0].split(" ")[0].lower() in title.lower() else False
            model = check_model_from_title(title=title, car_model=car[1])
            year = check_years_from_title(title=title, require_year=car[2])
            pro = compare_collection_title(title=title, collection=part_name)
            if maker and model and year and pro > 0.9:
                oem_part_numer = await check_part_number_and_oem_number(url)
                if oem_part_numer:
                    if url in result:
                        car_self[url] = oem_part_numer
                    else:
                        new = True
                        for i in result:
                            if i in result[i][0]:
                                new = False
                                car_self[i] = result[i][0]
                                break
                        if new:
                            result[url] = [oem_part_numer, ["_".join(car)]]
                            select = True
                            print(f'[Info] Successfully find')
                            break
                else:
                    pass
            else:
                pass
        
        if select == False:
            if car_self:
                result[list(car_self.keys())[0]][1].append("_".join(car))
                print(f'[Info] Successfully find')
            else:
                print(f'[Info] There are no products we find')
    print(f'[Info] Save checked products as xlsx')
    columns =  ['Collection','Car','Link']
    coll = []
    car = []
    link = []
    for i in result:
        coll.append(part_name)
        car.append(",".join(result[i][1]))
        link.append(i)
    df = pd.DataFrame(list(zip(coll,car, link)), columns=columns)
    # df.to_excel("list1.xlsx", index = False)
    # print(search_result)
    try:
        df.to_excel(xlsx_file_path, index = False)
        print("-------------------- Saved successfully --------------------")
    except:
        print("-------------------- Failed in saving --------------------")

        
        
    
def get_cars_easysearch(file_path):
    cars = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        files = csv.reader(f, delimiter=',', quotechar='"')
        for i in files:
            key = f'{i[0]},{i[1]},{i[2]}'
            if key in cars:
                pass
            else:
                cars[key]= i[0:3]
    require_cars = list(cars.values())
    return require_cars

def get_car(cars):
    c_car = re.findall(r'\[(.*?)\]', cars)
    require_car = []
    for i in c_car:
        lk = i.split(",")
        require_car.append(lk)
    return require_car

if __name__ == "__main__":
    if from_easyesarch.lower()=="true":
        require_cars=get_cars_easysearch("easysearch.csv")
    else:
        require_cars = get_car(cars=cars)
    
    asyncio.run(main(require_cars=require_cars))   