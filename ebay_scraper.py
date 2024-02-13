import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import os, re, openai, json
import pandas as pd

from dotenv import load_dotenv

load_dotenv(dotenv_path='.env')

openai_key = os.getenv('OPNEAI_KEY')
file_name = os.getenv('XLSX_FILE')
remove_api = os.getenv("REMOVE_API")
SCRAP_PRODUCTS = os.getenv("SCRAP_PRODUCTS")
openai.api_key = openai_key

def load_xlsx(xlsx_file):
    df = pd.read_excel(xlsx_file)
    return df["Link"].to_list()

def get_brand_model_part_name_using_openai(title):
    prompt = """Simply answer the following questions
What cars can this part of the given string support? 
The answer must include both the manufacturer and model name. And the answer must include car brand and model. ANd the answer must not contain any other words.  If there is more than one car model, separate each model with ','."""
    message_box = [
        {"role": "system", "content": prompt}, 
        {"role": "user", "content": "ENGINE MOTOR MOUNT TORQUE STRUT FRONT FOR SANTA FE 2.4L KIA SORENTO 2.4L 3.3L"}, 
        {"role": "assistant", "content": "Hyundai Santa Fe, Kia Sorento"},
        {"role": "user", "content": "KIA 3.3L LOWER INTAKE MANIFOLD FITS SEDONA SORENTO CADENZA OEM 283103CFA0"}, 
        {"role": "assistant", "content": "Kia Sedona, Kia Sorento, Kia Cadenza"},
        {"role": "user", "content": f'String: {title}'}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=message_box
    )
    openai_answer = response.choices[0]["message"]["content"]
    return openai_answer

def get_brand_model_from_openai_answer(answer):
    lk = answer.split(" ")
    
    if lk[0].lower() == "mercedes" and lk[1].lower() == "benz":
        car_brand = f'{lk[0]} {lk[1]}'
    else:
        car_brand = lk[0]
    mk = answer.replace(car_brand, "").strip()
    car_model =  mk.strip()
    return car_brand, car_model

def clean_openai_answer(answers):
    clean_value = answers
    result = re.findall(r'\((.*?)\)', clean_value)
    for i in result:
        clean_value = clean_value.replace(f'({i})', "")
    year_period = re.findall(r'\d{4}-\d{4}', clean_value)
    for i in year_period:
        clean_value = clean_value.replace(i, "")
    years = re.findall(r'\b\d{4}\b', clean_value)
    for i in years:
        clean_value = clean_value.replace(i, "")
    return clean_value

def car_get_model(exist_model, new_model):
    mk = new_model.split(" ")
    if exist_model.get(mk[0]):
        if len(mk) !=1:
            if not mk[1] in exist_model[mk[0]]:
                exist_model[mk[0]].append(mk[1])
    else:
        if len(mk) !=1:
            exist_model[mk[0]] = [mk[1]]
        else:
            exist_model[mk[0]] = []
    return exist_model

def prepar_brand_model(answers):
    value = clean_openai_answer(answers)
    candidate = value.split(",")
    brand_model = []
    for i in candidate:
        brand, model = get_brand_model_from_openai_answer(i.strip())
        brand_model.append([brand, model])
    car = {}
    for i in brand_model:
        if car.get(i[0]):
           car[i[0]] = car_get_model(car[i[0]], i[1])
        else:
           car[i[0]] =  car_get_model({}, i[1])
    return car

def make_string_value(car_brand_model):
    models = []
    keys = list(car_brand_model.keys())
    for br in keys:
        for y in car_brand_model[br]:
            if y != "":
                model = y
                if car_brand_model[br][y] != []:
                    model = model +" "+ "/".join(car_brand_model[br][y])
                if len(keys) != 1:
                    model = model + f'({br})'
                models.append(model)
        
    brand = ", ".join(list(car_brand_model.keys()))
    car_model =", ".join(models)
    return brand, car_model

def get_part_name_using_openai(title):
    prompt = """Based on the given string, you must briefly answer the following questions: Your answer must contain only the substance of the question. Your answer must not contain any other words.
what is detailed product name in given string?
The answer must not include car brand and car name."""
    message_box = [{"role": "system", "content": prompt}, {"role": "user", "content": f'String: {title}'}]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=message_box
    )
    openai_answer = response.choices[0]["message"]["content"]
    return openai_answer

def download_image(url, file_name):
    # url_remove = 'https://api.removal.ai/3.0/remove'
    # headers = {
    #     'accept': 'application/json',
    #     'Rm-Token': remove_api,
    # }
    # files = {
    #     'image_url': ('', url),
    #     'crop': ('', '1'),
    #     'ecom': ('', '1'),
    #     'get_base64': ('', '1'),
    # }
    # url_picture = requests.post(url_remove, headers=headers, files=files).json()["url"]
    response = requests.get(url=url)
    if response.status_code == 200:
        with open(file_name, 'wb') as file:
            file.write(response.content)
        print("Image downloaded successfully as:", file_name)
    else:
        print("Failed to download image")

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

def get_years_from_title(title):
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
        car_years = None
    elif len(years) ==  1:
        car_years = years
    else:
        car_years = [min(years), max(years)]
    
    return car_years

def get_price(price_text):
    price_m = float(re.findall(r'\d+\.\d+', price_text)[0])
    price_unit = price_text.split(" ")[0]
    if price_unit == "US":
        price_m = round(price_m*3.7, 2)
        return price_m
    elif price_unit == "GBP":
        price_m = round(price_m*4.66, 2)
        return price_m
    else:
        return price_m

async def fetch(url):
    # Create HTTP session
    async with aiohttp.ClientSession() as session:
        # Make GET request using session
        async with session.get(url) as response:
            # Return text content
            return await response.text()

def make_folder_name(title):
    t1 = title.replace("\\","")
    t2 = t1.replace("/","")
    t3 = t2.replace("*","")
    t4 = t3.replace("<","")
    t5 = t4.replace(">","")
    t6 = t5.replace("\"","")
    t7 = t6.replace("|","")
    t8 = t7.replace(":","")
    t9 = t8.replace("?","")
    return t9.strip()

async def scraping(url):
    print("--------------------------------------------------------------------")
    print("Url: ", url)

    content = await fetch(url)
    soup = BeautifulSoup(content, 'html.parser')

    # GET Title of product
    title = soup.select('h1.x-item-title__mainTitle span')[0].text
    print("Title: ", title)
    price = get_price(soup.select('div.vim.x-price-section.mar-t-20 div.x-price-primary span')[0].text)
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
    print(product_info)
    # Part Number and OEM Part Number
    OEM_part_number = get_part_number(product_info.pop("OE/OEM Part Number")) if "OE/OEM Part Number" in product_info else None
    # Manufacturer Part Number
    Manufacturer_part_number = get_part_number(product_info.pop("Manufacturer Part Number")) if "Manufacturer Part Number" in product_info else None
    # Interchange Part Number
    Interchange_part_number = get_part_number(product_info.pop("Interchange Part Number")) if "Interchange Part Number" in product_info else ( get_part_number(product_info.pop("Interchange")) if "Interchange" in product_info else None)
    
    # Part Number 
    if OEM_part_number:
        part_number = [OEM_part_number[0]]
    elif Manufacturer_part_number:
        part_number = [Manufacturer_part_number[0]]
    elif Interchange_part_number:
        part_number = [Interchange_part_number[0]]
    else:
        part_number = None

    if part_number == None:
        raise Exception('Sorry, part_number is None')
    
    # Get Car Brand, Car Model, Part Name of product using GPT
    answer = get_brand_model_part_name_using_openai(title=title)
    car_brand, car_model = make_string_value(prepar_brand_model(answers=answer))
    part_name = get_part_name_using_openai(title=title)
    print(car_brand, car_model, part_name)
    # Get condition
    condition_string = product_info.pop("Condition") if "Condition" in product_info else None
    if condition_string:
        condition = "Used" if condition_string.lower().startswith('used') else ("New" if condition_string.lower().startswith('new') else None)
    # Replacement On Vehicle
    replacement_on_vehicle = product_info.pop("Placement on Vehicle") if "Placement on Vehicle" in product_info else None

    # Type
    type = product_info.pop("Type") if "Type" in product_info else None
    # image download
    images = soup.select('div.ux-image-carousel.img-transition-medium img')
    image_urls=[]
    picture_folder = make_folder_name(title=title)
    os.makedirs(f'pictures/{picture_folder}', exist_ok=True)
    for image in images:
        if not 'Video' in image['alt']:
            try:
                urls = re.findall(r'(https?://\S+)', image['data-srcset'])
                if not urls[-1] in image_urls:
                    download_image(url=urls[-1], file_name=f"pictures/{picture_folder}/{str(len(image_urls)+1)}.jpg")
                    image_urls.append(urls[-1])
            except:
                try:
                    if not image['data-zoom-src'] in image_urls:
                        download_image(url=image['data-zoom-src'], file_name=f"pictures/{picture_folder}/{str(len(image_urls)+1)}.jpg")
                        image_urls.append(image['data-zoom-src'])
                except:
                    pass
    
    # Extract years of products

    car_years = get_years_from_title(title=title)

    
    # Totals
    info_product = {}
    info_product['title'] = title
    info_product['picture_folder'] = picture_folder
    info_product['url'] = url
    info_product['price'] = price
    info_product['Part Name'] = part_name
    info_product['Part Number'] = part_number
    info_product['Condition (New\\Used)'] = condition
    info_product['Car Brand'] = car_brand
    info_product['Car Model'] = car_model
    info_product['Car Years range'] = car_years
    info_product['Replacement on vehicle'] = replacement_on_vehicle
    info_product['Type'] = type
    info_product['OEM Part Number'] = OEM_part_number
    info_product['Manufacturer Part Number'] = Manufacturer_part_number
    info_product['Interchange Part Number'] = Interchange_part_number
    info_product['Brand'] = "OEM PART"
    info_product['Stock'] = 'In stock'
    info_product['extra'] = product_info

    print(info_product)
    return info_product

# Run the main function

async def main(list_name):
    urls = load_xlsx(list_name)
    products = []
    for i in urls:
        try:
            info = await scraping(url=i)
            products.append(info)
        except Exception as e:
            with open('log.txt', 'a+', encoding='utf-8') as f:
                f.write(f'{i}\n{e}\n\n')
            print(e)
            pass
    with open(SCRAP_PRODUCTS, 'w') as f:
        json.dump(products, f, indent=2)

if __name__ == "__main__":
    
    asyncio.run(main(file_name))
