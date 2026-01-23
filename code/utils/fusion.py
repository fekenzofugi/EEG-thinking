import rasterio
from utils.files_info import get_files_info, alphanum_key
import numpy as np
import os
import pandas as pd
from datetime import datetime

import os
import numpy as np
import rasterio
from datetime import datetime

def is_date_in_period(date, start_date, end_date):
    """
    Check if a date is within a period defined by two dates.
    Args:
        date (str): The date to check in the format YYYYMMDD.
        start_date (str): The start date of the period in the format YYYYMMDD.
        end_date (str): The end date of the period in the format YYYYMMDD.
    Returns:
        bool: True if the date is within the period, False otherwise.
    """
    date_format = "%Y%m%d"
    date = datetime.strptime(date, date_format)
    start_date = datetime.strptime(start_date, date_format)
    end_date = datetime.strptime(end_date, date_format)
    return start_date <= date <= end_date

def date_difference(date1, date2):
    """
    Calculate the absolute difference in days between two dates.
    Args:
        date1 (str): The first date in the format YYYYMMDD.
        date2 (str): The second date in the format YYYYMMDD.
    Returns:
        int: The absolute difference in days between the two dates.
    """
    date_format = "%Y%m%d"
    d1 = datetime.strptime(date1, date_format)
    d2 = datetime.strptime(date2, date_format)
    return abs((d2 - d1).days)

def fusion(s2_path, s1_path, fused_path, crs):
    """
    Fuses Sentinel-1 and Sentinel-2 images based on closest dates.
    Args:
        s2_path (str): Path to Sentinel-2 images.
        s1_path (str): Path to Sentinel-1 images.
        fused_path (str): Path to save fused images.
        crs (str): Coordinate Reference System (CRS) of the images.
    """
    # Get file info
    s2_num_files, s2_ids = get_files_info(s2_path)
    s1_num_files, s1_ids = get_files_info(s1_path)

    # Sort the files based on the alphanumeric order
    s1_ids = sorted(s1_ids, key=alphanum_key)
    s2_ids = sorted(s2_ids, key=alphanum_key)
    # Read Sentinel-2 images
    sentinel2_images = []
    for i in range(s2_num_files):
        sentinel2_path = os.path.join(s2_path, s2_ids[i])
        src1 = rasterio.open(sentinel2_path, mode='r', driver='GTiff', crs=crs)
        s2 = src1.read()
        id = s2_ids[i]
        sentinel2_images.append([s2, id])

    # Read Sentinel-1 images
    sentinel1_images = []
    for i in range(s1_num_files):
        sentinel1_path = os.path.join(s1_path, s1_ids[i])
        src2 = rasterio.open(sentinel1_path, mode='r', driver='GTiff', crs=crs)
        s1 = src2.read()
        id = s1_ids[i]
        sentinel1_images.append([s1, id])

    
    # Extract dates from Sentinel-1 and Sentinel-2 images
    s1_dates = [img[1].split("_")[1] for img in sentinel1_images]
    s2_dates = [img[1].split("_")[1] for img in sentinel2_images]

    # Convert dates to datetime objects
    s1_dates = [datetime.strptime(date, "%Y%m%d") for date in s1_dates]
    s2_dates = [datetime.strptime(date, "%Y%m%d") for date in s2_dates]

    # Plot the dates
    import matplotlib.pyplot as plt

    plt.figure(figsize=(10, 5))
    plt.plot(s1_dates, [1] * len(s1_dates), 'ro', label='Sentinel-1')
    plt.plot(s2_dates, [2] * len(s2_dates), 'bo', label='Sentinel-2')
    plt.yticks([1, 2], ['Sentinel-1', 'Sentinel-2'])
    plt.xlabel('Date')
    plt.title('Sentinel-1 and Sentinel-2 Image Dates')
    plt.legend()
    plt.grid(True)
    plt.savefig(f'{fused_path}/fused_temporal_resolution.png')

    # Fuse Sentinel-1 and Sentinel-2 images
    # APPROACH 1: Closest Dates
    # 1. For each Sentinel-1 image, find the closest images in Sentinel-2.
    # 2. Every Sentinel-2 image should be compared with the current Sentinel-1 image and the next one.
    # 3. After finding the closest images, fuse them and remove them from the list.
    # Get all unique dates from Sentinel-1 and Sentinel-2 images
    s1_dates = sorted(list(set([img[1].split("_")[1] for img in sentinel1_images])))
    s2_dates = sorted(list(set([img[1].split("_")[1] for img in sentinel2_images])))
    print(f"Total Sentinel-1 Dates: {len(s1_dates)}")
    print(f"Total Sentinel-2 Dates: {len(s2_dates)}")
    print(f"Sentinel-1 Dates: {s1_dates}")
    print(f"Sentinel-2 Dates: {s2_dates}")

    s1_s2_closest_dates = []
    for i in range(len(s1_dates)):
        s1_current_date = s1_dates[i]
        if i == 0 and len(s1_dates) > 1:
            s1_after_date = s1_dates[i + 1]
            s1_s2_pairing = [s1_current_date]
            for j in range(len(s2_dates)):
                s2_date = s2_dates[j]
                current_diff = date_difference(s2_date, s1_current_date)
                after_diff = date_difference(s2_date, s1_after_date)
                if current_diff <= after_diff:
                    s1_s2_pairing.append(s2_date)
                if current_diff > after_diff:
                    s2_dates = s2_dates[j:]
                    break

            s1_s2_closest_dates.append(s1_s2_pairing)
        elif i != 0 and i != len(s1_dates) - 1:
            s1_before_date = s1_dates[i - 1]
            s1_after_date = s1_dates[i + 1]
            s1_s2_pairing = [s1_current_date]

            for j in range(len(s2_dates)):
                s2_date = s2_dates[j]
                before_diff = date_difference(s2_date, s1_before_date)
                current_diff = date_difference(s2_date, s1_current_date)
                after_diff = date_difference(s2_date, s1_after_date)
                if current_diff <= after_diff:
                    s1_s2_pairing.append(s2_date)
                if current_diff > after_diff:
                    s2_dates = s2_dates[j:]
                    break

            s1_s2_closest_dates.append(s1_s2_pairing)
        elif i == len(s1_dates) - 1:
            s1_before_date = s1_dates[i - 1]
            s1_s2_pairing = [s1_current_date]
            for j in range(len(s2_dates)):
                s2_date = s2_dates[j]

                before_diff = date_difference(s2_date, s1_before_date)
                current_diff = date_difference(s2_date, s1_current_date)
                if current_diff <= before_diff:
                    s1_s2_pairing.append(s2_date)
                if current_diff > before_diff:
                    break
            s1_s2_closest_dates.append(s1_s2_pairing)
    print(f"Paring: {s1_s2_closest_dates}")     

    fused_images = []
    for i in range(len(s1_s2_closest_dates)):
        s1_date = s1_s2_closest_dates[i][0]
        s2_dates = s1_s2_closest_dates[i][1:]
        total_tiles = int(len(sentinel1_images) / len(s1_dates))
        for j in range(len(s2_dates)): 
            s2_date = s2_dates[j]
            for k in range(total_tiles): 

                # FILTER SENTINEL-1 IMAGES WITH DATE
                filtered_s1_images = [img for img in sentinel1_images if s1_date in img[1]]
                # FILTER SENTINEL-2 IMAGES WITH DATE
                filtered_s2_images = [img for img in sentinel2_images if s2_date in img[1]]

                s1_img = filtered_s1_images[k]
                
                # Filtrar todas as imagens S2 do tile correspondente
                s2_tile_id = s1_img[1].split("_")[-1].split(".")[0]  # Ajuste conforme seu padrão de nome
                s2_imgs_tile = [img for img in filtered_s2_images if s2_tile_id in img[1]]

                if not s2_imgs_tile:
                    continue  # Nenhuma imagem S2 para esse tile/data

                # Selecionar a imagem S2 com o menor número de zeros
                min_zeros = None
                best_s2_img = None
                for img in s2_imgs_tile:
                    zero_count = np.sum(img[0] == 0)
                    if (min_zeros is None) or (zero_count < min_zeros):
                        min_zeros = zero_count
                        best_s2_img = img

                s2_np = best_s2_img[0]
                s2_id = best_s2_img[1]
            
                s2_date = s2_dates[j]
                s1_np = s1_img[0]
                s1_id = s1_img[1]
                fused_img = np.concatenate((s2_np, s1_np), axis=0)
                fused_images.append(fused_img)
                s2_tile = s2_id.split(".")[0][-2:]
                s1_prefix = s1_id.split("_")[2] + "_" + s1_date
                s2_prefix = '_'.join(s2_id.split("_")[:-2])
                fused_id = f"{s2_prefix}_{s1_prefix}_tile_{s2_tile}.tif"
                final_path = os.path.join(fused_path, fused_id)
                # Open a new dataset for writing
                new_dataset = rasterio.open(
                    final_path,
                    mode='w',
                    driver='GTiff',
                    height=fused_img.shape[1],
                    width=fused_img.shape[2],
                    count=fused_img.shape[0],
                    dtype=fused_img.dtype,
                    crs=src1.crs,  # Use the CRS from the source dataset
                    transform=src1.transform  # Use the transform from the source dataset
                )        
                try:
                    for u in range(fused_img.shape[0]):
                        new_dataset.write(fused_img[u], u + 1)
                finally:
                    new_dataset.close()