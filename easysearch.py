import re
import os, json, csv
from dotenv import load_dotenv
import shopify
import time

load_dotenv(dotenv_path='.env')

SHOP_NAME = os.getenv('SHOP_NAME')
ADMIN_API_ACCESS_TOKEN = os.getenv('ADMIN_API_ACCESS_TOKEN')
NEW_CHECKED_PRODUCT = os.getenv('NEW_CHECKED_PRODUCT')
DUPLICATION_NEW_PRODCUT = os.getenv('DUPLICATION_NEW_PRODCUT')
DUPLICATION_EXIST_PRODUCT = os.getenv('DUPLICATION_EXIST_PRODUCT')
SCRAP_PRODUCTS = os.getenv("SCRAP_PRODUCTS")

headers = {
    'Content-Type': 'application/json',
    'X-Shopify-Access-Token': ADMIN_API_ACCESS_TOKEN
}

session = shopify.Session(
            f'{SHOP_NAME}.myshopify.com',
            "2023-04",
            ADMIN_API_ACCESS_TOKEN
        )

shopify.ShopifyResource.activate_session(session)

# Get datailed product's data
def get_data_of_products(prod):
    prod_dict = prod.to_dict()
    main_keys = ["id", "title", "handle"]
    product = dict((y, prod_dict[y]) for y in main_keys)

    metafields = prod.metafields()
    if metafields is None or len(metafields) == 0:
        return None
    
    metafields_value = {}
    for i in metafields:
        metafield = i.to_dict()
        if metafield["key"] == "year_":
            metafields_value[metafield['key']] = get_years(metafield["value"])
        else:
            metafields_value[metafield['key']] = metafield["value"]
    product["metafields"] = metafields_value
    return product

# Get all products form shopify
def get_all_resources(resource):
    resources = []
    if resource.has_next_page():
        new_page = resource.next_page()
        resources.extend(get_all_resources(new_page))
    for i, prod in enumerate(resource):
        if i%4 == 0:
            time.sleep(1)
        resources.append(get_data_of_products(prod))
    print(len(resources))
    time.sleep(3)
    return resources

# Clean part_number of products
def get_years(car_year):
    years = [int(i) for i in re.findall(r'\b\d{4}\b|\b\d{2}\b', car_year)]
    return years

def replace_specific(string_s):
    s = string_s.strip().upper()
    k = s.replace("-", " ")
    l = k.replace("_", " ")
    m = l.replace("/", " ")
    n = m.replace("\\", " ")
    return n

def car_model_choose(candidate, model):
    lk = candidate
    for i in candidate:
        if model in candidate[i]:
            lk[i] = model
            return lk, i
        elif candidate[i] in model:
            return lk, i
    
    lk[str(len(candidate))] = model
    return lk, str(len(candidate))

def car_brand_choose(candidate, brand):
    lk = candidate
    for i in candidate:
        if brand in candidate[i]:
            return lk, i
        elif candidate[i] in brand:
            lk[i] = brand
            return lk, i
    
    lk[str(len(candidate))] = brand
    return lk, str(len(candidate))

def make_brand_model_set(brand, model):

    keys = []
    brands = brand.split(",")
    if len(brands) == 1:
        if brands[0].upper() == "MERCEDES":
            car_b = "Mercedes Benz"
        else:
            car_b = brands[0].replace("-", " ")
        models = model.split(",")
        for i in models:
            keys.append(f'{car_b.upper()},{i.strip().split(" ")[0].upper()}')
    else:
        models = model.split(",")
        for i in models:
            car_brand = re.findall(r'\((.*?)\)', i)[0]
            if car_brand.upper() == "MERCEDES":
                car_b = "Mercedes Benz"
            else:
                car_b = car_brand.replace("-", " ")
            mk = i.replace(f'({car_brand})', "")
            keys.append(f'{car_b.upper()},{mk.strip().split(" ")[0].upper()}')
    return keys


def make_database_for_easysearch(products):
    print("here")
    database = {}
    for product in products:
        try:
            keys = make_brand_model_set(product["metafields"]["car_brand"], product["metafields"]["car_model"])
            print(keys)
            for key in keys:
                for y in range(product["metafields"]["year_"][0], product["metafields"]["year_"][-1] + 1):                       
                    car_year = y
                    database_key = f"{key},{car_year}"
                    print(database_key, product["handle"])
                    if database.get(database_key):
                        database[database_key].append(product["handle"])
                    else:
                        database[database_key] = [product["handle"]]
        except Exception as e:
            pass
    return database

def output_database(database_file_path, database):
    with open(database_file_path, "w", encoding="utf-8") as f:
        for i in database.keys():
            row = f'{i},\"{",".join(database[i])}\"\n'
            f.write(row)

if __name__ == "__main__":
    print("Extracting exist porducts from shopify ...")
    products = get_all_resources(shopify.Product.find())
    # # with open("project_database.json", "w") as f:
    # #     json.dump(products, f, indent=2)
    # with open("project_database.json") as f:
    #     products = json.load(f)
    database = make_database_for_easysearch(products=products)
    with open("database.json", "w") as f:
        json.dump(database, f, indent=2)
    output_database(database_file_path="easysearch.csv", database=database)