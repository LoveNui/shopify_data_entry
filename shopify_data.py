import requests
import json
import os, re, csv
from dotenv import load_dotenv

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

url = f'https://{SHOP_NAME}.myshopify.com/admin/api/2024-01/graphql.json'

# Function to get all products with pagination
def get_all_products():
    all_products = []
    end_cursor = None
    has_next_page = True

    while has_next_page:
        # GraphQL query with pagination
        query = """
        {
            products(first: 250%s) {
                edges {
                    cursor
                    node {
                        id
                        title
                        handle
                        vendor
                        metafields(first: 250) {
                            edges {
                                node {
                                    key
                                    value
                                }
                            }
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                }
            }
        }
        """ % (", after: \"%s\"" % end_cursor if end_cursor else "")

        response = requests.post(url=url, headers=headers, json={'query': query})
        response_json = response.json()

        edges = response_json['data']['products']['edges']
        all_products.extend(edge['node'] for edge in edges)
        has_next_page = response_json['data']['products']['pageInfo']['hasNextPage']

        if edges:
            end_cursor = edges[-1]['cursor']

    return all_products

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
        if exist_product:
            numbers = []
            metafield = {}
            for k in exist_product["metafields"]["edges"]:
                if k["node"]["key"] == "part_number":
                    mk = format_exist_product_part_number(k["node"]["value"])
                    metafield[k["node"]["key"]] = mk
                    if mk:
                        numbers.extend(mk)
                elif k["node"]["key"] == "oem_part_no_":
                    mk = get_part_number(k["node"]["value"])
                    metafield[k["node"]["key"]] = mk
                    if mk:
                        numbers.extend(mk)
                else:
                    metafield[k["node"]["key"]] = k["node"]["value"]
            save_product = {
                "id": int(exist_product["id"].split("/")[-1]),
                "title": exist_product["title"],
                "handle": exist_product["handle"],
                "metafields":metafield
            }
            numbers = list(set(numbers))
            for y in numbers:
                if y in part_numbers.keys():
                    try:
                        duplication_products[y].append(save_product)
                        break
                    except:
                        duplication_products[y] = [part_numbers[y], save_product]
                        break
                else:
                    part_numbers[y] = save_product

    new_upload_product = []
    for i, new_product in enumerate(product_new):
        flag = True
        if new_product["Part Number"]:
            for y in new_product["Part Number"]:
                if y in part_numbers:
                    duplication_new.append([new_product["url"], part_numbers[y]["title"], part_numbers[y]["id"]])
                    flag = False
                    break
            if not flag:
                continue
        if new_product["OEM Part Number"]:
            for y in new_product["OEM Part Number"]:
                if y in part_numbers:
                    duplication_new.append([new_product["url"], part_numbers[y]["title"], part_numbers[y]["id"]])
                    flag = False
                    break
            if not flag:
                continue
        if new_product["Manufacturer Part Number"]:
            for y in new_product["Manufacturer Part Number"]:
                if y in part_numbers:
                    duplication_new.append([new_product["url"], part_numbers[y]["title"], part_numbers[y]["id"]])
                    flag = False
                    break
            if not flag:
                continue
        if new_product["Interchange Part Number"]:
            for y in new_product["Interchange Part Number"]:
                if y in part_numbers:
                    duplication_new.append([new_product["url"], part_numbers[y]["title"], part_numbers[y]["id"]])
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
        if key == "metafields":
            if len(product1[key].keys()) > len(product2[key].keys()):
                return False, 1
            elif len(product1[key].keys()) < len(product2[key].keys()):
                return False, 0
            for k in product1[key].keys():
                try:                        
                    if product1[key][k].strip() != product2[key][k].strip():
                        if k in ["part_name", "car_brand", "car_model", "year_"]:
                            if product1["title"] != product2["title"]:
                                return False, mk
                        else:
                            return False, mk
                except:
                    if product1[key][k]!= product2[key][k]:
                        return False, mk
        elif not key in ["id", "body_html", "title", "tags", "published_scope", "tags", "status", "options", "handle"] :
            try:
                if product1[key] != product2[key]:
                    return False, mk
            except:
                return False, mk
        else:
            pass
    return True, mk

def check_duplication_products_for_delete(duplication_products):
    remove_list = []
    admin_list = {}
    for key in duplication_products.keys():
        products = duplication_products[key]
        if products:
            same_product = []
            incorrect_prodcuts = []
            for product in products:
                if product["metafields"].get("part_number") and product["metafields"].get("oem_part_no_"):
                    if set(product["metafields"].get("part_number")).issubset(set(product["metafields"].get("oem_part_no_"))):
                        same_product.append(product)
                    else:
                        incorrect_prodcuts.append(product)
                else:
                    incorrect_prodcuts.append(product)
            if incorrect_prodcuts == []:
                ask_product = [same_product[0]]
                for i in range(1, len(same_product)):
                    new_ask_product = ask_product
                    flag = True
                    for base in ask_product:
                        result, mk = check_same_products(base, same_product[i])
                        if result == True:
                            remove_list.append(same_product[i])
                            flag = True
                            break
                        elif mk == 1:
                            remove_list.append(same_product[i])
                            flag = True
                            break
                        elif mk == 0:
                            remove_list.append(base)
                            new_ask_product.remove(base)
                            flag = False
                        else:
                            flag = False
                    if flag == False:
                        new_ask_product.append(same_product[i])
                    ask_product = new_ask_product
                if len(ask_product) == 1:
                    pass
                else:
                    admin_list[key] = ask_product
            elif same_product == []:
                flag = True
                base_prodcut = incorrect_prodcuts[0]
                for i in range(1, len(incorrect_prodcuts)-1):
                    result, mk = check_same_products(base_prodcut, incorrect_prodcuts[i])
                    if result == False:
                        if mk != -1:
                            if mk == 1:
                                remove_list.append(incorrect_prodcuts[i])
                            else:
                                remove_list.append(base_prodcut)
                                base_prodcut = incorrect_prodcuts[i]
                        else:
                            admin_list[key] = [pro for pro in incorrect_prodcuts]
                            flag = False
                            break
                    else:
                        remove_list.append(incorrect_prodcuts[i])
                if flag:
                    remove_list.extend(incorrect_prodcuts[1::])
            else:
                remove_list.extend(incorrect_prodcuts)
        
    return remove_list, admin_list


if __name__ == "__main__":
    print("Extracting exist porducts from shopify ...")
    products = get_all_products()
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
    remove_list, admin_list = check_duplication_products_for_delete(duplication_products=duplication_products)
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