import os, json, requests
from dotenv import load_dotenv
import shopify
import time
from PIL import Image
from io import BytesIO

load_dotenv(dotenv_path='.env')

SHOP_NAME = os.getenv('SHOP_NAME')
ADMIN_API_ACCESS_TOKEN = os.getenv('ADMIN_API_ACCESS_TOKEN')
updating_pictures_product_list = os.getenv('REMOVE_BACKGROUND_PICTURES_PRODUCTS')
remove_api = os.getenv("REMOVE_API")

session = shopify.Session(
            f'{SHOP_NAME}.myshopify.com',
            "2023-04",
            ADMIN_API_ACCESS_TOKEN
        )
shopify.ShopifyResource.activate_session(session)

def update_picture_processing(title):
    print("Title: ", title)
    pro = shopify.Product.find(title=title)[0]
    images = pro.to_dict()["images"]
    new_images = []
    print("[Info] Removing backgorund of images")
    for i, image in enumerate(images):
        src_url = image["src"]
        bg_remove_pic = download_image(src_url)
        if bg_remove_pic:
            new_image = shopify.Image()
            # with open(bg_remove_pic, 'rb') as f:
            #     encode = f.read()
            new_image.attach_image(bg_remove_pic, filename=f'{i}')
            new_images.append(new_image)
    pro.images = new_images
    print("[Info] Uploading new images on shopify")
    try:
        pro.save()
        print("[Info] successfully added new images")
    except:
        print("[Info] successfully added new images")


def set_background_color(image):
    # Create a new image with a white background
    new_image = Image.new("RGBA", image.size, color=(255, 255, 255))
    
    # Composite the original image on the white background
    new_image.paste(image, (0, 0), image)
    
    return new_image

def download_image(url):
    url_remove = 'https://api.removal.ai/3.0/remove'
    headers = {
        'accept': 'image/jpg',
        'Rm-Token': remove_api,
    }
    files = {
        'image_url': ('', url),
        'crop': ('', '0'),
        'ecom': ('', '0'),
        'get_base64': ('', '0'),
    }
    url_picture = requests.post(url_remove, headers=headers, files=files).json()["url"]
    response = requests.get(url=url_picture)
    if response.status_code == 200:
        
        # Open the image from the response content
        image = Image.open(BytesIO(response.content)).convert("RGBA")

        # Set the background color to white
        image_with_white_bg = set_background_color(image)
        new_image = image_with_white_bg.convert("RGB")
        # print(url_picture.split("/")[-1].split("?")[0].split(".")[0])
        buffer = BytesIO()

        # Save the image to the buffer
        new_image.save(buffer, format="JPEG")

        # Retrieve the image data from the buffer
        econd = buffer.getvalue()
        return econd

    else:
        return False

if __name__ == "__main__":
    with open(updating_pictures_product_list, 'r', encoding='utf-8') as f:
        text = f.readlines()
    for i, title in enumerate(text):
        print(f'-------------------{i+1} Product -------------------')
        t = title.replace("\n", "")
        update_picture_processing(title=t)
    