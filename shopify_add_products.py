import os, json
from dotenv import load_dotenv
import shopify
import time

load_dotenv(dotenv_path='.env')

SHOP_NAME = os.getenv('SHOP_NAME')
ADMIN_API_ACCESS_TOKEN = os.getenv('ADMIN_API_ACCESS_TOKEN')
NEW_CHECKED_PRODUCT = os.getenv('NEW_CHECKED_PRODUCT')

session = shopify.Session(
            f'{SHOP_NAME}.myshopify.com',
            "2023-04",
            ADMIN_API_ACCESS_TOKEN
        )
shopify.ShopifyResource.activate_session(session)

def upload_new_products(new_products):
    print("Add New Projects")
    for product in new_products:
        print("-------------------------------------------------------")
        print(product["title"])
        new_product = shopify.Product()
        new_product.product_type = ""
        new_product.body_html = product["title"]
        new_product.title = product["title"]
        new_product.vendor = "OEM PART"
        # set variant
        variant = shopify.Variant()
        variant.price = product["price"] if "price" in product else 0
        variant.sku = ''
        variant.grams = product["weight"]*1000 if "weight" in product else 0
        variant.weight = product["weight"] if "weight" in product else 0
        variant.weight_unit = "kg"

        inventoryItem = shopify.InventoryItem()
        #inventoryItem = variant.inventory_item
        inventoryItem.tracked = True
        variant.inventory_quantity = 1
        inventoryItem.inventory_quantity = 1
        variant.inventory_item = inventoryItem
        
        new_product.variants = [variant]
        # Get the list of all pictures
        dir_list = os.listdir(os.path.join('pictures', product["title"]))
        print(dir_list)
        images = []
        for i in dir_list:
            image = shopify.Image()
            with open(f'pictures/{product["title"]}/{i}',"rb") as f:
                encoded = f.read()
                image.attach_image(encoded, filename=i)
            images.append(image)
        print("[Info] successfully added new images")
        new_product.images = images
        metafield_keys = {
            "Part Name": ["part_name","single_line_text_field"],
            "Part Number": ["part_number","list.single_line_text_field"],
            "UPC":["upc","single_line_text_field"],
            "Condition (New\\Used)":["condition_new_used_", "single_line_text_field"],
            "Car Brand":["car_brand", "single_line_text_field"],
            "Car Model":["car_model", "single_line_text_field"],
            "Car Years range":["year_", "single_line_text_field"],
            "Replacement on vehicle":["replacement_on_vehicle", "single_line_text_field"],
            "Color":["color", "color"],
            "Type":["type", "single_line_text_field"],
            "OEM Part Number": ["oem_part_no_", "single_line_text_field"],
            "Technology":["technology", "multi_line_text_field"],
            "Alternative part number": ["alternative_part_number","single_line_text_field"],
            "Made in": ["made_in", "single_line_text_field"],
            "Country/Region of Manufacture": ["country_region_of_manufacture", "single_line_text_field"],
            "Item height": ["item_height", "dimension"],
            "Item length": ["item_length", "dimension"],
            "Item width": ["item_width", "dimension"],
            "Item included": ["item_included", "multi_line_text_field"]
        }
        product_metafields = []
        for y in metafield_keys:
            if y == "Part Number":
                if product.get(y):
                    value = "[\"" + "\",\"".join(product.get(y)) +"\"]"
                else:
                    value = None
            elif y == "OEM Part Number":
                if product.get(y):
                    value = " , ".join(product.get(y))
                else:
                    value = None
            elif y == "Car Years range":
                if product.get(y):
                    value = "-".join([str(i) for i in product.get(y)])
                else:
                    value = None
            else:
                if product.get(y):
                    value = product.get(y)
                else:
                    value = None
            if value:
                metafield = shopify.Metafield()
                metafield.key = metafield_keys[y][0]
                metafield.value = value
                metafield.type = metafield_keys[y][-1]
                metafield.namespace = "custom"
                product_metafields.append(metafield)

        new_product.save()
        print("[Info] successfully added project")
        for i in product_metafields:
            new_product.add_metafield(i)
        print("[Info] successfully added metafields")
        inventoryitem = shopify.InventoryItem.find(new_product.variants[0].inventory_item_id)
        inventoryitem.tracked = True
        inventoryitem.save()
        print(new_product.variants[0].inventory_item_id)
        inventory = shopify.InventoryLevel.find_first(inventory_item_ids=new_product.variants[0].inventory_item_id).to_dict()
        shopify.InventoryLevel.set(inventory_item_id=inventory["inventory_item_id"], location_id=inventory["location_id"], available=1)
        print("[Info] successfully set inventory items")
        time.sleep(1)
        print("------------------ completed adding this product ------------------")
    print("------------------ completed adding all products ------------------")

if __name__ == "__main__":
    with open(NEW_CHECKED_PRODUCT) as f:
        new_upload_product = json.load(f)
    upload_new_products(new_upload_product)
