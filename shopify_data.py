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
ADMIN_HANDLE_PRODUCT_LIST = os.getenv('ADMIN_HANDLE_PRODUCT_LIST')
REMOVE_PRODUCT_LIST = os.getenv('REMOVE_PRODUCT_LIST')
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
    main_keys = ["id", "title", "body_html", "vendor", "product_type", "published_scope", "tags", "status", "options"]
    product = dict((y, prod_dict[y]) for y in main_keys)
    
    variant_keys = ["id", "title","price","sku", "grams","weight","weight_unit"]
    product["variants"] = [dict((y, i[y]) for y in variant_keys) for i in prod_dict["variants"]]

    metafields = prod.metafields()
    if metafields is None or len(metafields) == 0:
        return None
    
    metafields_value = {}
    for i in metafields:
        metafield = i.to_dict()
        if metafield["key"] == "part_number":
            metafields_value[metafield['key']] = format_exist_product_part_number(metafield["value"])
        elif metafield["key"] == "oem_part_no_":
            metafields_value[metafield['key']] = get_part_number(metafield["value"])
        elif metafield["key"] == "year_" :
            metafields_value[metafield['key']] = [int(i) for i in re.findall(r'\b\d{4}\b|\b\d{2}\b', metafield["value"])]
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
    if part_number_string.strip() == "Does not apply" or part_number_string.strip() == 'N/A' or part_number_string.strip() == 'N / A':
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

def format_exist_product_part_number(part_number):
    k = re.findall(r'\[\"(.*?)\"\]', part_number)[0]
    numbers =get_part_number(k)
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
        numbers = []
        if exist_product["metafields"].get("part_number"):
            numbers.extend(exist_product["metafields"].get("part_number"))
        if exist_product["metafields"].get("oem_part_no_"):
            numbers.extend(exist_product["metafields"].get("oem_part_no_"))
        numbers = list(set(numbers))
        for y in numbers:
            if y in part_numbers.keys():
                try:
                    duplication_products[y] = duplication_products[y].append((i, exist_product["id"], exist_product["title"], exist_product["title"]))
                    break
                except:
                    duplication_products[y] = [(part_numbers[y], product_exist[part_numbers[y]]["id"], product_exist[part_numbers[y]]["title"]),(i, exist_product["id"], exist_product["title"])]
                    break
            else:
                part_numbers[y] = i

    new_upload_product = []
    for i, new_product in enumerate(product_new):
        flag = True
        if new_product["Part Number"]:
            for y in new_product["Part Number"]:
                if y in part_numbers:
                    duplication_new.append([new_product["url"], product_exist[part_numbers[y]]["title"], product_exist[part_numbers[y]]["id"]])
                    flag = False
                    break
            if not flag:
                continue
        if new_product["OEM Part Number"]:
            for y in new_product["OEM Part Number"]:
                if y in part_numbers:
                    duplication_new.append([new_product["url"], product_exist[part_numbers[y]]["title"], product_exist[part_numbers[y]]["id"]])
                    flag = False
                    break
            if not flag:
                continue
        if new_product["Manufacturer Part Number"]:
            for y in new_product["Manufacturer Part Number"]:
                if y in part_numbers:
                    duplication_new.append([new_product["url"], product_exist[part_numbers[y]]["title"], product_exist[part_numbers[y]]["id"]])
                    flag = False
                    break
            if not flag:
                continue
        if new_product["Interchange Part Number"]:
            for y in new_product["Interchange Part Number"]:
                if y in part_numbers:
                    duplication_new.append([new_product["url"], product_exist[part_numbers[y]]["title"], product_exist[part_numbers[y]]["id"]])
                    flag = False
                    break
            if not flag:
                continue
        if new_product["Part Number"]:
            new_upload_product.append(new_product)

    return duplication_products, duplication_new, new_upload_product

def check_same_products(product1, product2):
    mk = -1
    for key in product1.keys():
        if key == "variants":
            for k in product1[key]:
                if not "id" in k:
                    try:
                        if product1[key][k] != product2[key][k]:
                            return False, mk
                    except:
                        return False, mk
        elif key == "metafields":
            if len(product1[key].keys()) > len(product2[key].keys()):
                return False, 1
            elif len(product1[key].keys()) < len(product2[key].keys()):
                return False, 0
        
            for k in product1[key]:
                try:
                    if product1[key][k].strip() != product2[key][k].strip():
                        return False, mk
                except:
                    if product1[key][k]!= product2[key][k]:
                        return False, mk
                    return False, mk
        elif not key in ["id", "body_html", "title", "tags", "published_scope", "tags", "status", "options"] :
            try:
                if product1[key] != product2[key]:
                    return False, mk
            except:
                return False, mk
        else:
            pass
    
    return True, mk

def check_duplication_products_for_delete(duplication_products, exist_products):
    remove_list = []
    admin_list = {}
    for key in duplication_products.keys():
        products = duplication_products[key]
        if products:
            same_product = []
            incorrect_prodcuts = []
            for y in products:
                product = exist_products[y[0]]
                if product["metafields"].get("part_number") and product["metafields"].get("oem_part_no_"):
                    if set(product["metafields"].get("part_number")).issubset(set(product["metafields"].get("oem_part_no_"))):
                        same_product.append(product)
                    else:
                        incorrect_prodcuts.append(product)
                else:
                    incorrect_prodcuts.append(product)
            if incorrect_prodcuts == []:
                flag = True
                for i in range(0, len(same_product)-1):
                    result, mk = check_same_products(same_product[i], same_product[i+1])
                    if result == False:
                        if mk != -1:
                            remove_list.append(same_product[i + mk])
                        else:
                            admin_list[key] = [pro["title"] for pro in same_product]
                            flag = False
                            break
                if flag:
                    remove_list.extend(same_product[1::])
            elif same_product == []:
                flag = True
                for i in range(0, len(incorrect_prodcuts)-1):
                    result, mk = check_same_products(incorrect_prodcuts[i], incorrect_prodcuts[i+1])
                    if result == False:
                        if mk != -1:
                            remove_list.append(incorrect_prodcuts[i + mk])
                        else:
                            admin_list[key] = [pro["title"] for pro in incorrect_prodcuts]
                            flag = False
                            break
                if flag:
                    remove_list.extend(incorrect_prodcuts[1::])
            else:
                remove_list.extend(incorrect_prodcuts)
        
    return remove_list, admin_list


if __name__ == "__main__":
    print("Extracting exist porducts from shopify ...")
    products = get_all_resources(shopify.Product.find())
    # with open("project1.json", "w") as f:
    #     json.dump(products, f, indent=2)
    # with open("project1.json") as f:
    #     products = json.load(f)
    print("Loading new porducts from json ...")
    new_products = get_new_products(SCRAP_PRODUCTS)
    print("Checking the duplication products")
    duplication_products, duplication_new, new_upload_product = find_duplication_product(product_exist=products, product_new=new_products)
    print("---------------------------------------")
    print("Duplication Items on shopify: ", len(duplication_products))
    with open("duplication_products.json", "w") as f:
        json.dump(duplication_products, f, indent=2)
    remove_list, admin_list = check_duplication_products_for_delete(duplication_products=duplication_products, exist_products=products)
    print("Remove Items on shopify: ", len(remove_list))
    print("Admin handling Items on shopify: ", len(admin_list))
    with open(REMOVE_PRODUCT_LIST, "w") as f:
        json.dump(remove_list, f, indent=2)
    with open(ADMIN_HANDLE_PRODUCT_LIST, "w") as f:
        json.dump(admin_list, f, indent=2)
    print("---------------------------------------")
    print("Duplication on New Products: ", len(duplication_new))
    with open(DUPLICATION_NEW_PRODCUT, "wt", encoding="utf-8") as f:
        w = csv.writer(f)
        for i in duplication_new:
            w.writerow(i)
    print("---------------------------------------")
    print("New Upload Product: ",len(new_upload_product))
    with open(NEW_CHECKED_PRODUCT, "w") as f:
        json.dump(new_upload_product, f, indent=2)