import numpy as np
import rasterio
import os
from PIL import Image, ImageDraw, ImageFont
from utils.files_info import get_files_info, alphanum_key
from utils.date_format import format_date


def normalize(band):
    band_min, band_max = (band.min(), band.max())
    return ((band-band_min)/((band_max - band_min)))


def generate_gif(path, ds_type, output, bands=['B4', 'B3', 'B2'], hasB1=False, position=None, speed=600, crs='EPSG:4326'):
    num_files, ids = get_files_info(path)
    ids = sorted(ids, key=alphanum_key)

    bands = sorted(bands, reverse=True)
    # Create a string linked with a loop on bands
    bands_str = "_".join(bands)
    image_id = f"{bands_str}"
    
    extention = ids[0].split('.')[-1]

    if bands == ['VV', 'VH'] or bands == ['VH', 'VV'] or bands == ['VV'] or bands == ['VH']:
        bands = ['VV', 'VH']

    data = []
    if extention == 'tif':
        for i in range(num_files):
            with rasterio.open(
                os.path.join(path, f'{ids[i]}'), mode='r', 
                driver='GTiff',
                crs=crs,
                ) as src:
                full_img = src.read()  # Read all bands into memory 

                print(f"Image Shape: {full_img.shape}")
                print(f"Gif bands: {bands}, position {position}")

                img = full_img  # Initialize empty list for image
                if bands == ['B4', 'B3', 'B2']:
                    if hasB1:
                        img = np.stack([full_img[3], full_img[2], full_img[1]], axis=-1) / 10000
                    else:
                        img = np.stack([full_img[2], full_img[1], full_img[0]], axis=-1) / 10000

                elif bands == ['VV', 'VH'] and (full_img.shape[0]) == 3:
                    img = np.stack([full_img[0], full_img[1], full_img[2]], axis=-1) / 50   # Normalize and rearrange bands
                elif bands == ['VV', 'VH'] and (full_img.shape[0]) > 2: 
                    img = np.stack([full_img[-3], full_img[-2], full_img[-1]], axis=-1) / 50  # Normalize and rearrange bands
                elif len(bands) == 1:
                    if not bands[0][-1].isdigit():
                        img = full_img[position]
                    else:
                        img = full_img[position] / 10000

                elif len(bands) == 3:
                    img = np.stack([full_img[2], full_img[1], full_img[0]], axis=-1) / 10000
                data.append(img)  # Normalize the image data

        data = np.array(data)
        bands_str = "_".join(bands)
    
        for i in range(len(data)):
            id = ids[i]
            image_id = ""
            if ds_type.upper() == "TRAINING":
                image_id = f"{id.split('_')[0]}_tile_{id.split('_')[-1][:2]}"
            if ds_type.upper() == "COUNTING":
                image_id = f"{id.split('_')[0]}_{id.split('_')[1]}_{id.split('_')[2]}"

            output_image_dir = os.path.join(output, f'{image_id}')
            os.makedirs(output_image_dir, exist_ok=True)
            # Convert the NumPy array to uint8
            image_array = (data[i] * 255).astype(np.uint8)
            
            # Convert the NumPy array to a Pillow Image
            image = Image.fromarray(image_array)

            image_date = ''
            if ds_type.upper() == "TRAINING":
                if id.split('_')[2][:2] == 'S1':
                    image_date = format_date(id.split('_')[1], 0, 8)
                if id.split('_')[2][:2] == 'S2':
                    image_date = format_date(id.split('_')[1], 0, 8)
            if ds_type.upper() == "COUNTING":
                if id.split('_')[4][:2] == 'S1':
                    image_date = format_date(id.split('_')[3], 0, 8)
                if id.split('_')[4][:2] == 'S2':
                    image_date = format_date(id.split('_')[3], 0, 8)

            # Call draw Method to add 2D graphics in an image
            I1 = ImageDraw.Draw(image)
            
            # Add Text to an image
            # Define a larger font size for the text
            try:
                font = ImageFont.truetype("arial.ttf", 25)
            except IOError:
                font = ImageFont.load_default()
                font = font.font_variant(size=25)
            if len(bands) == 1:
                I1.text((28, 36), f"{image_date}", font=font, spacing=8, fill=0)
            else:
                I1.text((28, 36), f"{image_date}", font=font, spacing=8, fill=(255, 0, 0))

            image.save(os.path.join(output_image_dir, f"{id.split('.')[0]}.jpg"))
            
            # Open only the .png files and store them in a list
            img_ids = sorted([img for img in os.listdir(output_image_dir) if img.endswith('.jpg')])  # Ensure sorted order
            images = [Image.open(os.path.join(output_image_dir, img)) for img in img_ids]

            # Save as GIF
            images[0].save(os.path.join(output_image_dir, f'{image_id}_{bands_str}.gif'),
                        save_all=True,
                        append_images=images[1:],
                        duration=speed,  # Duration of each frame in milliseconds
                        loop=0)  # 0 means loop indefinitely
            
        for i in range(len(data)):
            id = ids[i]
            image_id = ""
            if ds_type.upper() == "TRAINING":
                image_id = f"{id.split('_')[0]}_tile_{id.split('_')[-1][:2]}"
            if ds_type.upper() == "COUNTING":
                image_id = f"{id.split('_')[0]}_{id.split('_')[1]}_{id.split('_')[2]}"                
            output_image_dir = os.path.join(output, f'{image_id}')
            # Remove all .png files in the output directory
            for file_name in os.listdir(output_image_dir):
                if file_name.endswith('.jpg'):
                    os.remove(os.path.join(output_image_dir, file_name))
        print(f"Generated GIF for all {bands_str} tiles in all ROIs Successfully!")

    