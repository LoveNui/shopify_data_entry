import aiohttp
import asyncio
from bs4 import BeautifulSoup
import requests
import os, re, openai, json
import pandas as pd

from dotenv import load_dotenv

load_dotenv(dotenv_path='.env')

openai_key = os.getenv('OPNEAI_KEY')
file_name = os.getenv('XLSX_FILE')

openai.api_key = openai_key

def load_xlsx(xlsx_file):
    df = pd.read_excel(xlsx_file)
    return df["Link"].to_list()

def get_brand_model_part_name_using_openai(title):
    prompt = "Based on the given string, you must briefly answer the following questions: Your answer must contain only the substance of the question. Your answer must not contain any other words.\n1. What is car brand in given string?\n2. What is car model in given string?\n3. what is detailed product name in given string?"
    message_box = [{"role": "system", "content": prompt}, {"role": "user", "content": f'String: {title}'}]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=message_box
    )
    openai_answer = response.choices[0]["message"]["content"]
    values = re.findall(r'\d+\.\s(.+)', openai_answer)
    return values

def download_image(url, file_name):
    response = requests.get(url)
    if response.status_code == 200:
        with open(file_name, 'wb') as file:
            file.write(response.content)
        print("Image downloaded successfully as:", file_name)
    else:
        print("Failed to download image")

def get_part_number(part_number_string):
    if " , " in part_number_string:
        part_number = part_number_string.split(" , ")
    elif ", " in part_number_string:
        part_number = part_number_string.split(", ")
    elif "," in part_number_string:
        part_number = part_number_string.split(",")
    elif " / " in part_number_string:
        part_number = part_number_string.split(" / ")
    elif "/ " in part_number_string:
        part_number = part_number_string.split("/ ")
    elif "/" in part_number_string:
        part_number = part_number_string.split("/")
    else:
        if part_number_string != "Does not apply":
            return part_number_string, [part_number_string]
        print("Failed to extract part number")
    
    print(part_number)
    if len(part_number) == 1:
        return part_number[0], part_number
    else:
        return part_number.pop(0), part_number

async def fetch(url):
    # Create HTTP session
    async with aiohttp.ClientSession() as session:
        # Make GET request using session
        async with session.get(url) as response:
            # Return text content
            return await response.text()

async def scraping(url):
    print("--------------------------------------------------------------------")
    print("Url: ", url)

    content = await fetch(url)
    soup = BeautifulSoup(content, 'html.parser')

    # GET Title of product
    title = soup.select('h1.x-item-title__mainTitle span')[0].text
    print("Title: ", title)

    # image download
    images = soup.select('div.ux-image-carousel.img-transition-medium img')
    image_urls=[]
    os.makedirs(title, exist_ok=True)
    for image in images:
        # try:
        #     urls = re.findall(r'(https?://\S+)', image['data-srcset'])
        #     print(urls)
        #     download_image(url=urls[-1], file_name=f"{str(i+1)}.jpg")
        # except:
        if not image['data-zoom-src'] in image_urls and not 'Video' in image['alt']:
            try:
                download_image(url=image['data-zoom-src'], file_name=f"{title}/{str(len(image_urls)+1)}.jpg")
                image_urls.append(image['data-zoom-src'])
            except:
                pass
    
    # Extract years of products
    car_years = re.findall(r'\b\d{4}\b', title)
    
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
    
    # Get Car Brand, Car Model, Part Name of product using GPT
    gpt_value = get_brand_model_part_name_using_openai(title=title)
    print(gpt_value)    
    car_brand = gpt_value[0]
    car_model = gpt_value[1]
    part_name = gpt_value[2]

    # Get condition
    condition_string = product_info.pop("Condition") if "Condition" in product_info else None
    if condition_string:
        condition = "Used" if condition_string.lower().startswith('used') else ("New" if condition_string.lower().startswith('new') else None)
    
    # Replacement On Vehicle
    replacement_on_vehicle = product_info.pop("Placement on Vehicle") if "Placement on Vehicle" in product_info else None

    # Type
    type = product_info.pop("Type") if "Type" in product_info else None
    
    # Part Number and OEM Part Number
    part_number_string = product_info.pop("OE/OEM Part Number") if "OE/OEM Part Number" in product_info else (product_info.pop('Manufacturer Part Number') if 'Manufacturer Part Number' in product_info else None)
    if part_number_string:
        part_number, OEM_part_number = get_part_number(part_number_string)
    else:
        part_number, OEM_part_number = None, None
    
    # Totals
    info_product = {}
    info_product['title'] = title
    info_product['url'] = url
    info_product['Part Name'] = part_name
    info_product['Part Number'] = part_number
    info_product['Condition (New\\Used)'] = condition
    info_product['Car Brand'] = car_brand
    info_product['Car Model'] = car_model
    info_product['Car Years range'] = car_years
    info_product['Replacement on vehicle'] = replacement_on_vehicle
    info_product['Type'] = type
    info_product['OEM part number'] = OEM_part_number
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
            with open('log.txt', 'a+') as f:
                f.write(f'{i}\n{e}\n\n')
            print(e)
            pass
    with open('data.json', 'w') as f:
        json.dump(products, f)

if __name__ == "__main__":
    
    asyncio.run(main(file_name))