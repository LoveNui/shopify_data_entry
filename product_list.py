from selenium import webdriver
from selenium.webdriver.common.by import By
import os, re, openai
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

load_dotenv('search.config')
openai_key = os.getenv('OPNEAI_KEY')
condition = os.getenv('CONDITION_NEW')
part_name = os.getenv('PART_COLLECTION')
car_maker = os.getenv('CAR_MAKER')
car_model = os.getenv('CAR_MODEL')
year = os.getenv('YEAR')

search_result = os.getenv('SEARCH_RESULT')

openai.api_key = openai_key

def get_candidate_list(condition, part_name, car_maker, car_model, car_year):

    print("--------------- Scraping Products: Candidate_Products ---------------")
    driver = webdriver.Chrome()
    url = f'https://www.ebay.com/sch/i.html?_nkw={"+".join(part_name.split(" "))}+{"+".join(car_maker.split(" "))}+{"+".join(car_model.split(" "))}+{car_year}{ "&LH_ItemCondition=3" if condition==True else ""}'
    print(f'[Info] URL: {url}')
    driver.get(url)
    search_result = driver.find_elements(by=By.CLASS_NAME, value='s-item__info.clearfix')
    result= []

    for i in search_result:
        product_item = {}
        title = i.find_element(by=By.CLASS_NAME, value="s-item__title")
        product_item["title"] = title.find_element(by=By.TAG_NAME, value="span").text
        product_item["url"] = i.find_element(by=By.TAG_NAME, value='a').get_attribute('href')
        result.append(product_item)

    print(f'[Info] Candidate Products: {len(result)}')
    return result

def get_check_candidat_products(candidate_products, collection, car_maker, car_model, car_year):
    products = []
    print("-------------------- Checking candidate_Products --------------------")
    for i, item in enumerate(candidate_products):
        title = item["title"]
        print(f'{i+1}: {title}')
        maker = True if car_maker.split(" ")[0].lower() in title.lower() else False
        model = True if car_model.split(" ")[0].lower() in title.lower() else False
        year = check_years_from_title(title=title, require_year=car_year)
        pro = compare_collection_title(title=title, collection=collection)
        print(pro)
        if maker and pro > 0.3:
            collectin_check = get_part_name_using_openai(title=title, collection=collection, car_maker=car_maker, car_model=car_model)
            print(f'Possibility: {"Yes" if collectin_check else "No"}')
            print(f'-------------------------------------------------')
            if collectin_check:
                products.append(item)
            products.append(item)
        else:
            print(f'Possibility: No')
            print(f'-------------------------------------------------')
    return products 

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

def get_part_name_using_openai(title, collection, car_maker, car_model):
    prompt = f'Please answer whether following car part could be in this collection  of {collection} for {car_maker} {car_model}". You must answer "yes" or"No", Your answer must not include another words.'
    message_box = [{"role": "system", "content": prompt}, {"role": "user", "content": f'{title}'}]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=message_box
    )
    openai_answer = response.choices[0]["message"]["content"]
    if 'yes' in openai_answer.lower():
        return True
    else:
        return False

def compare_collection_title(title, collection):
    num = 0
    for i in collection.split(" "):
        if i.lower() in title.lower():
            num = num + 1
    
    return num/len(collection.split(" "))

def write_result(products, collection, car_maker, car_model, car_year, file_path):
    print("-------------------- Save checked products as xlsx --------------------")
    print(f'[Info] Saving {len(products)} Products')
    columns =  ['Collection','Car Maker','Car Model', 'Car Year','Link']
    coll = []
    maker = []
    model = []
    year = []
    link = []
    for i in products:
        coll.append(collection)
        maker.append(car_maker)
        model.append(car_model)
        year.append(car_year)
        link.append(i["url"])
    
    df = pd.DataFrame(list(zip(coll,maker,model,year, link)), columns=columns)
    try:
        df.to_excel(file_path, index = False)
        print("-------------------- Saved successfully --------------------")
    except:
        print("-------------------- Failed in saving --------------------")

if __name__ == "__main__":
    candidate_list = get_candidate_list(condition=condition, part_name=part_name, car_maker=car_maker, car_model=car_model, car_year=year)
    products = get_check_candidat_products(candidate_products=candidate_list, collection=part_name, car_maker=car_maker, car_model=car_model, car_year=year)
    write_result(products=products, collection=part_name, car_maker=car_maker, car_model=car_model, car_year=year, file_path=search_result)
