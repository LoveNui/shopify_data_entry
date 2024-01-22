import requests
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
    main_keys = ["id", "title", "body_html", "vendor", "product_type", "published_scope", "tags", "status", "options"]
    product = dict((y, prod_dict[y]) for y in main_keys)
    
    variant_keys = ["id", "title","price","sku", "grams","weight","weight_unit","inventory_quantity","old_inventory_quantity"]
    product["variants"] = [dict((y, i[y]) for y in variant_keys) for i in prod_dict["variants"]]

    metafields = prod.metafields()
    if metafields is None or len(metafields) == 0:
        return None
    
    metafields_value = {}
    for i in metafields:
        metafield = i.to_dict()
        if metafield["key"] == "part_number":
            metafields_value[metafield['key']] = format_exist_product_part_number(metafield["value"])
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
def get_part_number(part_number_string):
    if part_number_string == "Does not apply" and part_number_string == 'N/A':
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
    return numbers

def format_exist_product_part_number(part_number):
    k = re.findall(r'\[\"(.*?)\"\]', part_number)[0]
    numbers =[i.strip() for i in get_part_number(k)]
    return numbers

# Load new products for uploading
def get_new_products(new_product_file):
    with open(new_product_file) as f:
        new_products = json.load(f)
    return new_products

def find_duplication_product(product_exist, product_new):
    part_numbers = {}
    duplication_products = {}
    duplication_new = []
    for i, exist_product in enumerate(product_exist):
        if exist_product["metafields"].get("part_number"):
            for y in exist_product["metafields"].get("part_number"):
                if y in part_numbers.keys():
                    try:
                        duplication_products[y] = duplication_products[y].append((i, exist_product["id"], exist_product["title"], exist_product["title"]))
                    except:
                        duplication_products[y] = [(part_numbers[y], product_exist[part_numbers[y]]["id"], product_exist[part_numbers[y]]["title"]),(i, exist_product["id"], exist_product["title"])]
                else:
                    part_numbers[y] = i
    new_upload_product = []
    for i, new_product in enumerate(product_new):
        if new_product["Part Number"]:
            if new_product["Part Number"][0] in part_numbers:
                duplication_new.append([new_product["url"], product_exist[part_numbers[new_product["Part Number"][0]]]["title"], product_exist[part_numbers[new_product["Part Number"][0]]]["id"]])
        elif new_product["OEM Part Number"]:
            for y in new_product["OEM Part Number"]:
                if y in part_numbers:
                    duplication_new.append([new_product["url"], product_exist[part_numbers[y]]["title"], product_exist[part_numbers[y]]["id"]])
                    break
        elif new_product["Manufacturer Part Number"]:
            for y in new_product["Manufacturer Part Number"]:
                if y in part_numbers:
                    duplication_new.append([new_product["url"], product_exist[part_numbers[y]]["title"], product_exist[part_numbers[y]]["id"]])
                    break
        elif new_product["Interchange Part Number"]:
            for y in new_product["Interchange Part Number"]:
                if y in part_numbers:
                    duplication_new.append([new_product["url"], product_exist[part_numbers[y]]["title"], product_exist[part_numbers[y]]["id"]])
                    break
        else:
            if new_product["Part Number"]:
                new_upload_product.append(new_product)
    return duplication_products, duplication_new, new_upload_product

if __name__ == "__main__":
    print("Extracting exist porducts from shopify ...")
    # products = get_all_resources(shopify.Product.find())

    with open("product1.json") as f:
        products = json.load(f)
    print("Loading new porducts from json ...")
    new_products = get_new_products('data.json')
    print("Checking the duplication products")
    duplication_products, duplication_new, new_upload_product = find_duplication_product(product_exist=products, product_new=new_products)
    print("---------------------------------------")
    print("Duplication Items on shopify: ", len(duplication_products))
    with open(DUPLICATION_EXIST_PRODUCT, "w") as f:
        json.dump(duplication_products, f)
    print("---------------------------------------")
    print("Duplication on New Products: ", len(duplication_new))
    with open(DUPLICATION_NEW_PRODCUT, "w") as f:
        w = csv.writer(f)
        for i in duplication_new:
            w.writerow(i)
    print("---------------------------------------")
    print("New Upload Product: ",len(new_upload_product))
    with open(NEW_CHECKED_PRODUCT, "w") as f:
        json.dump(new_upload_product, f)