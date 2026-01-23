import ee
import os
import requests
import shutil
import logging
from retry import retry
import multiprocessing


def sort_bands(input_bands):
    predefined_order = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B10', 'B11', 'B12']
    return sorted(input_bands, key=lambda band: predefined_order.index(band) if band in predefined_order else float('inf'))


def get_s1_col(aoi, start_date, end_date):
    # Import and filter S1 GRD.
    s1_col = (ee.ImageCollection('COPERNICUS/S1_GRD')
        .filterBounds(aoi)
        .filterDate(start_date, end_date))
    return s1_col


def get_s2_col(aoi, start_date, end_date, S2_COLLECTION_ID, CLOUD_FILTER):
    # Import and filter S2 SR.
    s2_sr_col = (ee.ImageCollection(S2_COLLECTION_ID)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', CLOUD_FILTER)))

    return s2_sr_col


def getRequests(params, image, region):
    img = ee.Image(1).rename("Class").addBands(image)
    points = img.stratifiedSample(
        numPoints=params["count"],
        region=region,
        scale=params["scale"],
        projection=params["crs"],
        seed=params["seed"],
        geometries=True,
    )
    
    return points.aggregate_array(".geo").getInfo()

@retry(tries=10, delay=1, backoff=2)
def getResult(index, point, image, params, id):
    point = ee.Geometry.Point(point["coordinates"])
    region = point.buffer(params["buffer"]).bounds()

    if params["format"] in ["png", "jpg"]:
        url = image.getThumbURL(
            {
                "region": region,
                "dimensions": params["dimensions"],
                "format": params["format"],
            }
        )
    else:
        url = image.getDownloadURL(
            {
                "region": region,
                "dimensions": params["dimensions"],
                "format": params["format"],
                "bands": params["bands"],
                "crs": params["crs"],
            }
        )

    if params["format"] == "GEO_TIFF":
        ext = "tif"
    else:
        ext = params["format"]

    r = requests.get(url, stream=True)
    if r.status_code != 200:
        r.raise_for_status()

    out_dir = os.path.abspath(params["out_dir"])
    basename = str(index).zfill(len(str(params["count"])))
    if len(str(params["count"])) == 1:
        basename = f"0{basename}"
    filename = f"{out_dir}/{id}_{params['prefix']}{basename}.{ext}"
    with open(filename, "wb") as out_file:
        shutil.copyfileobj(r.raw, out_file)
    print("Download Completed: ", id, basename)


def closest_date_with_tile_2d(s1_2d, s2_2d):
    closest_tiles = []
    for date_s1, tile_s1 in s1_2d:
        closest_date_s2, closest_tile_s2 = min(
            s2_2d, key=lambda x: abs(x[0] - date_s1)
        )
        closest_tiles.append([closest_date_s2, closest_tile_s2])
    return closest_tiles

def create_closest_dates_tiles_3d(S1, S2):
    result_3d = []
    for s1_2d, s2_2d in zip(S1, S2):
        result_3d.append(closest_date_with_tile_2d(s1_2d, s2_2d))
    return result_3d


def get_training_images(user_choice, params, images, tiles, geometries):
    for i in range(len(images)):
        roi_images = images[i]
        roi_tiles = tiles[i]
        for j in range(len(roi_images)):
            image_date = ""
            satellite_prefix = roi_tiles[j][:2]
            if satellite_prefix.upper() == 'S1':
                image_date = roi_tiles[j][17:25]
            if satellite_prefix.upper() == 'S2':
                image_date = roi_tiles[j][11:19]
            s2_id = f"ROI{i}_{image_date}_{roi_tiles[j]}" 
            logging.basicConfig()
            items = getRequests(params, images[i][j], geometries[i])
            pool = multiprocessing.Pool(params["processes"])
            pool.starmap(getResult, [(index, item, images[i][j], params, s2_id) for index, item in enumerate(items)])
            pool.close()      


@retry(tries=10, delay=1, backoff=2)
def download_counting_images(region, image, params, id):

    if params["format"] in ["png", "jpg"]:
        url = image.getThumbURL(
            {
                "region": region,
                "dimensions": params["dimensions"],
                "format": params["format"],
            }
        )
    else:
        url = image.getDownloadURL(
            {
                "region": region,
                "dimensions": params["dimensions"],
                "format": params["format"],
                "bands": params["bands"],
                "crs": params["crs"],
            }
        )

    if params["format"] == "GEO_TIFF":
        ext = "tif"
    else:
        ext = params["format"]

    r = requests.get(url, stream=True)
    if r.status_code != 200:
        r.raise_for_status()

    out_dir = os.path.abspath(params["out_dir"])
    filename = f"{out_dir}/{id}.{ext}"
    with open(filename, "wb") as out_file:
        shutil.copyfileobj(r.raw, out_file)
    print("Download Completed: ", id)


def get_counting_images(fishnets_images, fishnets_tiles, fishnet_geometries, user_choice, params):
    for k in range(len(fishnets_images)): # 1 loop
        for i in range(len(fishnets_images[0])): # 3 loops
            for j in range(len(fishnets_images[0][0])): # 5 loops
                for idx in range(len(fishnets_images[0][0][0])): # 2 loops
                    image = fishnets_images[k][i][j][idx]
                    tile = fishnets_tiles[k][i][j][idx]
                    roi = fishnet_geometries[k][i][j]
                    image_date = ""
                    if user_choice.upper() == 'FUSED':
                        if tile[:2] == 'S1':
                            image_date = tile[17:25]
                        if tile[:2] == 'S2':
                            image_date = tile[11:19]
                    if user_choice.upper() == 'SENTINEL-1':
                        image_date = tile[17:25]
                    if user_choice.upper() == 'SENTINEL-2':
                        image_date = tile[11:19]
                    print(image_date)
                    s2_id = f"ROI{k}_{image_date}_{tile}_tile_{i}{j}" 
                    logging.basicConfig()
                    download_counting_images(
                        region=roi,
                        image=image,
                        params=params,
                        id=s2_id
                    )