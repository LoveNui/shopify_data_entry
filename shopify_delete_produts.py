import os, json
from dotenv import load_dotenv
import shopify

load_dotenv(dotenv_path='.env')

SHOP_NAME = os.getenv('SHOP_NAME')
ADMIN_API_ACCESS_TOKEN = os.getenv('ADMIN_API_ACCESS_TOKEN')
remove_product_list = os.getenv('REMOVE_PRODUCT_LIST')

session = shopify.Session(
            f'{SHOP_NAME}.myshopify.com',
            "2023-04",
            ADMIN_API_ACCESS_TOKEN
        )
shopify.ShopifyResource.activate_session(session)

if __name__ == "__main__":
    with open(remove_product_list) as f:
        remove_products = json.load(f)
    
    for product in remove_products:
        print("---------------------------------------")
        print(product["title"])
        try:
            shopify.Product.delete(product["id"])
            print("Successfully deleted project.")
        except:
            print("Failed to delete project.")
