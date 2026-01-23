import os
import ee
import json
import multiprocessing
from dotenv import load_dotenv
import numpy as np

from utils.files_info import get_files_info
from utils.downloads import get_s1_col, get_s2_col, get_counting_images, get_training_images
from utils.fusion import fusion
from utils.indices import calculate_indices
from utils.cloudmask import apply_cloudmask, get_s2_cld_col, add_cld_shdw_mask
from utils.fishnet_pixels import fishnet_pixels
import torch

def generate_training_dataset(BASE_PATH, user_choice, CLOUD_FILTER, DATE, selected_bands, selected_indices, masks, dimension, num_tiles, crs, roi_path, service_account):
    # %%%%%%%%%%%%%%%%%%%%%%%% CONFIGURATION %%%%%%%%%%%%%%%%%%%%%%%%
    S1_OUTPUT_DIRECTORY = BASE_PATH + '/Sentinel-1/'
    S2_ALL_PATH = f"{BASE_PATH}/Sentinel-2/"
    FUSED_PATH = f"{BASE_PATH}/Fused"  
    S2_SR_COLLECTION_ID = "COPERNICUS/S2_SR_HARMONIZED"
    S2_TOA_COLLECTION_ID = "COPERNICUS/S2_HARMONIZED"

    credentials_dir = "credentials"
    json_files = [f for f in os.listdir(credentials_dir) if f.endswith('.json')]
    if not json_files:
        raise FileNotFoundError("No JSON credentials file found in the credentials directory.")
    credentials_file = os.path.join(credentials_dir, json_files[0])
    credentials = ee.ServiceAccountCredentials(service_account, credentials_file)
    ee.Initialize(credentials)

    # Print the number of processes that can be used for parallel computing
    PROCESSES = multiprocessing.cpu_count()
    print(f"Number of processes available for parallel computing: {PROCESSES}")

    num_files = int(num_tiles)

    buffer = (int(dimension.split('x')[0]) / 2) * 10 

    final_bands = []

    # EXPORT PARAMETERS
    params = {
        "count": num_files,  # How many image chips to export
        "buffer": buffer,  # The buffer distance (m) around each point
        "scale": 10,  # The scale to do stratified sampling
        "bands": None, # The bands to export
        "seed": 1,  # A randomization seed to use for subsampling.
        "dimensions": dimension,  # The dimension of each image chip
        "format": "GEO_TIFF",  # The output image format, can be png, jpg, ZIPPED_GEO_TIFF, GEO_TIFF, NPY
        "prefix": "tile_",  # The filename prefix
        "processes": min(25, PROCESSES),  # How many processes to used for parallel processing
        "out_dir": "/data/output",  # The output directory. Default to the current working directly
        "crs": crs,  # The CRS to use for the output image
    }

    # Indices
    indices = ['NDVI', 'PMLI', 'BSI']

    num_files, files_ids = get_files_info(roi_path)
    num_images1 = 0
    num_images2 = 0
    if num_files == 0:
        print("No ROIs selected. Exiting...")
        exit()
    else:
        print(f"Total number of ROIs selected: {num_files}")
        geometries = []
        for i in range(num_files):
            with open(f"{roi_path}/roi_{i}.json", "r") as f:
                roi = json.load(f)
                polygon = ee.Geometry(roi['geometry'])
                geometries.append(polygon)
                # Verify the result by printing each geometry
        for geometry in geometries:
            print(geometry.getInfo())

        bands = selected_bands
        selected_bands = json.loads(bands)

        if user_choice.upper() == 'FUSED':
            selected_bands = json.loads(bands)[:12]

        indexes  = selected_indices
        selected_indices = json.loads(indexes)  

        selected_masks = json.loads(masks)

        filter = int(CLOUD_FILTER)

        CLOUD_FILTER = filter

        print(f"Selected bands: {selected_bands}")
        print(f"Selected indices: {selected_indices}")
        print(f"Cloud filter: {CLOUD_FILTER}")
        print(f"Masks: {selected_masks}")
        print(f"Date range: {DATE}")
        print(f"Dimesions: {dimension}")
        print(f"Buffer: {buffer}")
        print(f"Number of tiles: {num_tiles}")
        print(f"CRS: {crs}")


        if selected_bands == []:
            print("No bands selected. Exiting...")
            exit()
        if (params['format'] == 'jpg' or params['format'] == 'png') and user_choice.upper() == 'FUSED':
            print("Fused collection only supports GeoTIFF format. Please select another format.")
            exit()
        if (params['format'] == 'jpg' or params['format'] == 'png') and len(bands) > 3:
            print("JPG and PNG formats only support RGB bands. Please select another collection.")
            exit()
        
        # Get the S2 image collection
        s1_col_list = []
        s2_sr_col_list = []

        for region in geometries:
            s1_col = get_s1_col(region, DATE[0], DATE[1])
            s2_sr_col = get_s2_col(region, DATE[0], DATE[1], S2_SR_COLLECTION_ID, CLOUD_FILTER)
            s2_toa_col = get_s2_col(region, DATE[0], DATE[1], S2_TOA_COLLECTION_ID, CLOUD_FILTER)

            if 'Score+' in selected_masks:
                s2_sr_col = get_s2_cld_col(region, DATE[0], DATE[1], S2_SR_COLLECTION_ID, CLOUD_FILTER)
                s2_sr_col = s2_sr_col.map(add_cld_shdw_mask)
            s1_col_list.append(s1_col)
            s2_sr_col_list.append(s2_sr_col)

        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% S2 %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        images = []
        tiles = []
        s2_images = []
        s2_tiles = []
        if user_choice.upper() == 'SENTINEL-2' or user_choice.upper() == 'FUSED':
            
            cm = []
            if len(selected_masks) > 1 or 'Score+' in selected_masks:
                cm = ['cloudmask']

            params['bands'] = [
                {
                    'id': band, 
                    'scale': (
                        1 if band in indices else
                        10 if band in ['B2', 'B3', 'B4', 'B8'] + cm else 
                        20 if band in ['B5', 'B6', 'B7', 'B8A', 'B11', 'B12'] else 
                        60
                    ), 
                    'crs': params['crs']
                } 
                for band in selected_bands + selected_indices + cm
            ]
            params['out_dir'] = S2_ALL_PATH
            for idx in range(len(geometries)):
                roi_images = []
                roi_tiles = []
                s2_sr_col = s2_sr_col_list[idx]
                if params['format'] == 'GEO_TIFF':
                    num_images2 = s2_sr_col.size().getInfo()
                    print(f"ROI{idx} S2 SR collection has {num_images2} images.")
                    for i in range(s2_sr_col.size().getInfo()):
                        sr_img = s2_sr_col.toList(s2_sr_col.size()).getInfo()[i]
                        tile = sr_img['properties']['PRODUCT_ID']
                        sr_img = s2_sr_col.filter(ee.Filter.eq("PRODUCT_ID", tile)).first()
                        sr_img = sr_img.select(selected_bands + cm)
                        image = sr_img
                        if indices != []:
                            image = calculate_indices(image, selected_indices)
                        roi_images.append(image)
                        roi_tiles.append(tile)
                sort_selected = selected_bands
                sort_selected = sorted(sort_selected, reverse=True)
                if (params['format'] == 'jpg' or params['format'] == 'png' or sort_selected == ['B4', 'B3', 'B2'] or len(selected_bands) == 1) and user_choice.upper() != 'FUSED' and params['format'] != 'GEO_TIFF':
                    for i in range(s2_sr_col.size().getInfo()):
                        sr_img = s2_sr_col.toList(s2_sr_col.size()).getInfo()[i]
                        tile = sr_img['properties']['PRODUCT_ID']
                        sr_img = s2_sr_col.filter(ee.Filter.eq("PRODUCT_ID", tile)).select(selected_bands).first().visualize(min=0, max=5000)
                        image = sr_img
                        if indices != []:
                            image = calculate_indices(image, selected_indices)                        
                        roi_images.append(image)
                        roi_tiles.append(tile)
                        print(image.bandNames().getInfo())
             
                s2_images.append(roi_images)  
                s2_tiles.append(roi_tiles)
            tiles = s2_tiles
            images = s2_images

        if user_choice.upper() == 'FUSED':
            os.makedirs(S2_ALL_PATH, exist_ok=True)
            get_training_images(
                user_choice=user_choice,
                params=params,
                images=images,
                tiles=tiles,
                geometries=geometries
            )

        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% S1 %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        s1_images = []
        s1_tiles = []
        if user_choice.upper() == 'SENTINEL-1' or user_choice.upper() == 'FUSED':    
            bands = ['VV', 'VH']
            params['bands'] = [
                {
                    'id': band, 
                    'scale': 10
                } 
                for band in bands + ['VV/VH']
            ]
            params['out_dir'] = S1_OUTPUT_DIRECTORY
            for j in range(len(s1_col_list)):
                s1_col = s1_col_list[0].toList(s1_col.size())
                num_images1 = s1_col.size().getInfo()
                print(f"ROI{j} S1 collection has {s1_col.size().getInfo()} images.")

            for idx in range(len(geometries)):
                roi_images = []
                roi_tiles = []
                s1_col = get_s1_col(geometries[idx], DATE[0], DATE[1])
                for i in range(s1_col.size().getInfo()):
                    img = s1_col.toList(s1_col.size()).getInfo()[i]
                    tile = img['properties']['system:index']
                    img = s1_col.filter(ee.Filter.eq("system:index", tile)).select(bands).first()
                    if params['format'] == 'jpg' or params['format'] == 'png':
                        ratio = img.select('VV').divide(img.select('VH').max(1e-6))
                        img = ee.Image.rgb(img.select('VV'),
                            img.select('VH'),
                            ratio).visualize(min=-35, max=15).rename(['VV', 'VH', 'VV/VH'])
                    elif params['format'] == 'GEO_TIFF':
                        ratio = img.select('VV').divide(img.select('VH').max(1e-6))
                        img = ee.Image.rgb(img.select('VV'),
                            img.select('VH'),
                            ratio).rename(['VV', 'VH', 'VV/VH'])
                    roi_images.append(img)
                    roi_tiles.append(tile)
                s1_images.append(roi_images) 
                s1_tiles.append(roi_tiles)
            tiles = s1_tiles
            images = s1_images

        final_bands = selected_bands
        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% EXPORT %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        os.makedirs(params['out_dir'], exist_ok=True)
        get_training_images(
            user_choice=user_choice,
            params=params,
            images=images,
            tiles=tiles,
            geometries=geometries
        )

        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% CM %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        if "Senseiv" in selected_masks:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Using device: {device}")
            apply_cloudmask(S2_ALL_PATH, user_choice, device=device)
            torch.cuda.empty_cache()  # Clear GPU memory after cloudmask application

        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% FUSION %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        if user_choice.upper() == 'FUSED':
            os.makedirs(FUSED_PATH, exist_ok=True)
            fusion(
                s2_path=S2_ALL_PATH,
                s1_path=S1_OUTPUT_DIRECTORY,
                fused_path=FUSED_PATH,
                crs=params['crs']
            )
    
    total_num_images = max(num_images1, num_images2)
    return final_bands, total_num_images


def generate_counting_dataset(BASE_PATH, user_choice, CLOUD_FILTER, DATE, selected_bands, selected_indices, masks, dimension, overlap, crs, roi_path, service_account):
    # %%%%%%%%%%%%%%%%%%%%%%%% CONFIGURATION %%%%%%%%%%%%%%%%%%%%%%%%
    S1_OUTPUT_DIRECTORY = BASE_PATH + '/Sentinel-1/'
    S2_ALL_PATH = f"{BASE_PATH}/Sentinel-2/"
    FUSED_PATH = f"{BASE_PATH}/Fused"  
    S2_SR_COLLECTION_ID = "COPERNICUS/S2_SR_HARMONIZED"

    credentials_dir = "credentials"
    json_files = [f for f in os.listdir(credentials_dir) if f.endswith('.json')]
    if not json_files:
        raise FileNotFoundError("No JSON credentials file found in the credentials directory.")
    credentials_file = os.path.join(credentials_dir, json_files[0])
    credentials = ee.ServiceAccountCredentials(service_account, credentials_file)
    ee.Initialize(credentials)

    # Print the number of processes that can be used for parallel computing
    PROCESSES = multiprocessing.cpu_count()
    print(f"Number of processes available for parallel computing: {PROCESSES}")

    buffer = (int(dimension.split('x')[0]) / 2) * 10 

    final_bands = []

    # EXPORT PARAMETERS
    params = {
        "buffer": buffer,  # The buffer distance (m) around each point
        "scale": 10,  # The scale to do stratified sampling
        "bands": None, # The bands to export
        "seed": 1,  # A randomization seed to use for subsampling.
        "dimensions": dimension,  # The dimension of each image chip
        "format": "GEO_TIFF",  # The output image format, can be png, jpg, ZIPPED_GEO_TIFF, GEO_TIFF, NPY
        "processes": min(25, PROCESSES),  # How many processes to used for parallel processing
        "out_dir": "../data/output",  # The output directory. Default to the current working directly
        "crs": crs,  # The CRS to use for the output image
    }

    # Indices
    indices = ['NDVI', 'PMLI', 'BSI']

    num_files, files_ids = get_files_info(f"{roi_path}")
    if num_files == 0:
        print("No ROIs selected. Exiting...")
        exit()
    else:
        print(f"Total number of ROIs selected: {num_files}")
        geometries = []
        for i in range(num_files):
            with open(f"{roi_path}/roi_{i}.json", "r") as f:
                roi = json.load(f)
                polygon = ee.Geometry(roi['geometry'])
                geometries.append(polygon)
                # Verify the result by printing each geometry
        for geometry in geometries:
            print(geometry.getInfo())

        overlap = int(overlap)
        overlap = overlap * 10  
        fishnet_geometries = []
        # ADD FISHNET PIXELS
        for i in range(len(geometries)):
            roi = geometries[i]
            fishnet = fishnet_pixels(roi, overlap=overlap, BUFFER=buffer)
            fishnet_geometries.append(fishnet) # now we have a 3d array
        
        bands = selected_bands
        selected_bands = json.loads(bands)

        if user_choice.upper() == 'FUSED':
            selected_bands = json.loads(bands)[:13]

        indexes  = selected_indices
        selected_indices = json.loads(indexes)  
        selected_masks = json.loads(masks)
        filter = int(CLOUD_FILTER)
        CLOUD_FILTER = filter

        print(f"Selected bands: {selected_bands}")
        print(f"Selected indices: {selected_indices}")
        print(f"Cloud filter: {CLOUD_FILTER}")
        print(f"Masks: {selected_masks}")
        print(f"Date range: {DATE}")
        print(f"Dimesions: {dimension}")
        print(f"Buffer: {buffer}")
        print(f"Overlap: {overlap}")
        print(f"CRS: {crs}")

        if selected_bands == []:
            print("No bands selected. Exiting...")
            exit()

        s1_fishnet_col_list = []
        s2_sr_fishnet_col_list = []
        for k in range(len(fishnet_geometries)):
            fishnet = fishnet_geometries[k]
            num_rows = fishnet.shape[0]
            s1_col_list = []
            s2_sr_col_list = []
            for i in range(num_rows):
                num_rows = fishnet_geometries[0].shape[0]
                row = fishnet[i]
                s1_row_col_list = []
                s2_sr_row_col_list = []
                for region in row:
                    s1_col = get_s1_col(region, DATE[0], DATE[1])
                    s2_sr_col = get_s2_col(region, DATE[0], DATE[1], S2_SR_COLLECTION_ID, CLOUD_FILTER)
                    if 'Score+' in selected_masks:
                        s2_sr_col = get_s2_cld_col(region, DATE[0], DATE[1], S2_SR_COLLECTION_ID, CLOUD_FILTER)
                        s2_sr_col = s2_sr_col.map(add_cld_shdw_mask)
                    s1_row_col_list.append(s1_col)
                    s2_sr_row_col_list.append(s2_sr_col)
                s1_col_list.append(s1_row_col_list)
                s2_sr_col_list.append(s2_sr_row_col_list)
            s1_fishnet_col_list.append(s1_col_list)
            s2_sr_fishnet_col_list.append(s2_sr_col_list)
        
        shp = np.array(s2_sr_fishnet_col_list).shape
        print(shp)

        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% S2 %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        fishnets_images = []
        fishnets_tiles = []
        if user_choice.upper() == 'SENTINEL-2' or user_choice.upper() == 'FUSED':

            for i in range(len(s2_sr_fishnet_col_list)):
                s2_sr_fishnet = s2_sr_fishnet_col_list[0]
                s2_sr_row = s2_sr_fishnet[0]
                s2_sr_col = s2_sr_row[0]
                print(f"ROI{i} Using the S2 SR collection with {s2_sr_col.size().getInfo()} images.")

                if user_choice.upper() == 'FUSED':
                    selected_bands = [band for band in selected_bands if band != 'VV']
                    selected_bands = [band for band in selected_bands if band != 'VH']
                    final_bands = [band for band in final_bands if band != 'VV']
                    final_bands = [band for band in final_bands if band != 'VH']
            
            cm = []
            if len(selected_masks) > 1 or 'Score+' in selected_masks:
                cm = ['cloudmask']

            params['bands'] = [
                {
                    'id': band, 
                    'scale': (
                        1 if band in indices else
                        10 if band in ['B2', 'B3', 'B4', 'B8'] + cm else 
                        20 if band in ['B5', 'B6', 'B7', 'B8A', 'B11', 'B12'] else 
                        60
                    )
                } 
                for band in selected_bands + selected_indices + cm
            ]

            params['out_dir'] = S2_ALL_PATH
            for k in range(len(s2_sr_fishnet_col_list)): # rois
                print(f"roi {k}")
                s2_sr_col_fishnet = s2_sr_fishnet_col_list[k]
                fishnet = fishnet_geometries[k]
                num_rows = fishnet.shape[0]
                num_cols = fishnet.shape[1]
                s2_fishnet_images = [] 
                s2_fishnet_tiles = [] 
                for i in range(num_rows): # rows
                    print(f"row {i}")
                    s2_sr_col_row = s2_sr_col_fishnet[i]
                    s2_row_images = [] 
                    s2_row_tiles = []
                    for j in range(num_cols): # cols
                        print(f"col {j}")
                        col_images = [] 
                        col_tiles = [] 
                        s2_sr_col = s2_sr_col_row[j]
                        for idx in range(s2_sr_col.size().getInfo()): # images -> temporal axis
                            print(f"image {idx}")
                            sr_img = s2_sr_col.toList(s2_sr_col.size()).getInfo()[idx]
                            tile = sr_img['properties']['PRODUCT_ID']
                            sr_img = s2_sr_col.filter(ee.Filter.eq("PRODUCT_ID", tile)).select(selected_bands + cm).first()
                            image = sr_img
                            if indices != []:
                                image = calculate_indices(image, selected_indices)
                            col_images.append(image) 
                            col_tiles.append(tile) 
                        s2_row_images.append(col_images) 
                        s2_row_tiles.append(col_tiles) 
                    s2_fishnet_images.append(s2_row_images)
                    s2_fishnet_tiles.append(s2_row_tiles) 
                fishnets_images.append(s2_fishnet_images)
                fishnets_tiles.append(s2_fishnet_tiles) 
        
        if user_choice.upper() == 'FUSED':
            os.makedirs(S2_ALL_PATH, exist_ok=True)
            get_counting_images(
                fishnets_images=fishnets_images,
                fishnets_tiles=fishnets_tiles,
                fishnet_geometries=fishnet_geometries,
                user_choice=user_choice,
                params=params
            )

        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% S1 %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        if user_choice.upper() == 'SENTINEL-1' or user_choice.upper() == 'FUSED':
            fishnets_images = []
            fishnets_tiles = []    

            for i in range(len(s1_fishnet_col_list)):
                s1_fishnet = s1_fishnet_col_list[0]
                s1_row = s1_fishnet[0]
                s1_col = s1_row[0]
                print(f"ROI{i} Using the S1 collection with {s1_col.size().getInfo()} images.")


            bands = ['VV', 'VH']
            params['bands'] = [
                {
                    'id': band, 
                    'scale': 10
                } 
                for band in bands + ['VV/VH']
            ]
            params['out_dir'] = S1_OUTPUT_DIRECTORY
            
            
            for k in range(len(s1_fishnet_col_list)): # 1 loop
                s1_col_fishnet = s1_fishnet_col_list[k]
                fishnet = fishnet_geometries[k]
                num_rows = fishnet.shape[0]
                num_cols = fishnet.shape[1]
                s1_fishnet_images = [] 
                s1_fishnet_tiles = [] 
                for i in range(num_rows): # 3 loops
                    s1_col_row = s1_col_fishnet[i]
                    s1_row_images = [] 
                    s1_row_tiles = []
                    for j in range(num_cols): # 5 loops
                        col_images = [] 
                        col_tiles = [] 
                        s1_col = s1_col_row[j]
                        for idx in range(s1_col.size().getInfo()): # 2 loops
                            s1_img = s1_col.toList(s2_sr_col.size()).getInfo()[idx]
                            tile = s1_img['properties']['system:index']
                            s1_img = s1_col.filter(ee.Filter.eq("system:index", tile)).select(bands).first()  
                            ratio = s1_img.select('VV').divide(s1_img.select('VH').max(1e-6))
                            s1_img = ee.Image.rgb(s1_img.select('VV'),
                                s1_img.select('VH'),
                                ratio).rename(['VV', 'VH', 'VV/VH'])                            
                            image = s1_img
                            col_images.append(image) 
                            col_tiles.append(tile) 
                        s1_row_images.append(col_images) 
                        s1_row_tiles.append(col_tiles) 
                    s1_fishnet_images.append(s1_row_images) 
                    s1_fishnet_tiles.append(s1_row_tiles) 
                fishnets_images.append(s1_fishnet_images)
                fishnets_tiles.append(s1_fishnet_tiles)

        shp = np.array(fishnets_images).shape
        print(shp)
        print(fishnets_tiles)
        final_bands = selected_bands
        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% EXPORT %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        os.makedirs(params['out_dir'], exist_ok=True)
        get_counting_images(
            fishnets_images=fishnets_images,
            fishnets_tiles=fishnets_tiles,
            fishnet_geometries=fishnet_geometries,
            user_choice=user_choice,
            params=params
        )

        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% SENSEIV %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        if "Senseiv" in selected_masks:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Using device: {device}")
            apply_cloudmask(S2_ALL_PATH, user_choice, device=device)
    

        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% FUSION %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        if user_choice.upper() == 'FUSED':
            os.makedirs(FUSED_PATH, exist_ok=True)
            fusion(
                s2_path=S2_ALL_PATH,
                s1_path=S1_OUTPUT_DIRECTORY,
                fused_path=FUSED_PATH,
                crs=params['crs']
            )
        

    return final_bands