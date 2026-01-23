import pandas as pd
import numpy as np
import h5py
import ast
import os
import datetime
import plastic_sniffer.modules.classify_hard as ch
from app import db
from flask import session
from shapely.geometry import shape
from geoalchemy2.shape import from_shape
import json
    
#GID
def int_to_ascii(n):
    n = int(n)
    if 0 <= n <= 9:
        return chr(n + 48)
    elif 10 <= n <= 35:
        return chr(n + 55)
    elif 36 <= n <= 61:
        return chr(n + 61)
    else:
        raise ValueError(f"Must be in the range [0, 61] , but is {n}")

def ascii_to_int(c):
    c = ord(c)
    if 48 <= c <= 57:
        return c - 48
    elif 65 <= c <= 90:
        return c - 55
    elif 97 <= c <= 122:
        return c - 61
    else:
        raise ValueError("Must be in the range [0-9, A-Z, a-z]")
    
def int_to_b62(n):
    if n == 0:
        return "00"
    s = ""
    while n > 0:
        s = int_to_ascii(n % 62) + s
        n = n // 62
    return s.zfill(2)

def b62_to_int(s):
    n = 0
    for i, c in enumerate(s):
        n += ascii_to_int(c) * (62 ** (len(s) - i - 1))
    return n

def generate_GID(img_name, BASE_DATE : datetime.date) -> str:
    """
    This function returns the GID of the object.
    """
    name = img_name.split('_')
    #roi = name[1]
    #date = name[5][:-4]
    #tile = name[3]
    roi = name[1]
    date = name[5][:8]
    tile = name[3]
    gid = int_to_ascii(int(roi)) + int_to_ascii(int(tile)) + int_to_ascii((datetime.datetime.strptime(date, '%Y%m%d').date() - BASE_DATE).days // 5)
    return gid

# export to csv

def export_to_csv(img, img_name : str, objects : list[dict], filename : str, BASE_DATE : datetime.date):
    """
    This function exports the classification of the objects to a csv file.
    Format:
    GID, class
    """
    create_csv(filename)
    data = []
    existing_df = pd.read_csv(filename, index_col=0)
    i = 0
    for obj in objects: #Generate a new funticion to GID the objects
        GID = generate_GID(img_name, BASE_DATE) + int_to_b62(i)
        CLASS = obj['class']
        # Save the GID in the object
        obj['GID'] = GID
        VALIDATED = 0
        data.append([GID, obj['indexes'][0], obj['indexes'][1], obj['indexes'][2], obj['indexes'][3], obj['indexes'][4], obj['indexes'][5], obj['indexes'][6], obj['indexes'][7], obj['indexes'][8], CLASS, VALIDATED])
        i += 1
    df = pd.DataFrame(data, columns=['GID', 'PMLI', 'NDVI', 'BSI', 'BSPI', 'NDWI', 'NDMI', 'APGI', 'CLOUD', 'SHADOW', 'class', 'validated'])
    df = pd.concat([existing_df, df], ignore_index=True)
    df.to_csv(filename, index=True)

def convert_to_native(data):
    """Recursively convert numpy data types to native Python types"""
    if isinstance(data, np.ndarray):
        return data.tolist()  # Convert numpy arrays to lists
    elif isinstance(data, np.generic):
        return data.item()  # Convert numpy scalars to Python scalars
    elif isinstance(data, dict):
        return {k: convert_to_native(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_to_native(v) for v in data]
    return data

def export_to_db(objects : list[dict], img_name : str):
    from app.schemas import Classification, Imagery
    """
    This function exports the classification of the objects to the database.
    """
    i = 0
    for obj in objects:
        imagery_record = Imagery.query.filter_by(image_name=img_name).first()
        if imagery_record is None:
            raise ValueError(f"No Imagery record found for image_name: {img_name}")
        gid_pref = imagery_record.gid_prefix
        GID = gid_pref + int_to_b62(i)
        obj['GID'] = GID
        CLASS = obj['class']
        mask = convert_to_native(obj['segmentation'])
        area = convert_to_native(obj['area'])

        polygon = from_shape(shape(obj['geometry']), srid=4326)

        classification = Classification(
            gid=GID,
            gid_prefix=GID[:7],
            gid_suffix=GID[7:],
            pmli=convert_to_native(obj['indexes'][0]),
            ndvi=convert_to_native(obj['indexes'][1]),
            bsi=convert_to_native(obj['indexes'][2]),
            bspi=convert_to_native(obj['indexes'][3]),
            ndwi=convert_to_native(obj['indexes'][4]),
            ndmi=convert_to_native(obj['indexes'][5]),
            apgi=convert_to_native(obj['indexes'][6]),
            cloud=convert_to_native(obj['indexes'][7]),
            shadow=convert_to_native(obj['indexes'][8]),
            state=0,
            shape=polygon,
            mask=mask,
            area=area,
            user_id=session.get('user_id'),
            field_class=CLASS
        )
        db.session.add(classification)
        i += 1
    db.session.commit()

def create_csv(filename : str):
    """
    This function creates a csv file with the header 'GID, class'.
    """
    if not os.path.exists(filename):
        data = []
        open(filename, 'w').close()
        data.append(['00000', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])    
        df = pd.DataFrame(data, columns=['GID', 'PMLI', 'NDVI', 'BSI', 'BSPI', 'NDWI', 'NDMI', 'APGI', 'CLOUD', 'SHADOW', 'class', 'validated'])
        df.to_csv(filename, index=True)

# save masks

def save_masks_and_info_as_hdf5(masks, output_path, img_name):
    with h5py.File(os.path.join(output_path, f"{img_name}_masks_info.h5"), 'w') as hf:
        print(f"Saving masks and info for {img_name} in {output_path}")
        for i, mask in enumerate(masks):
            # Convert mask['segmentation'] to a NumPy array with a specific data type
            segmentation_array = np.array(mask['segmentation'])#, dtype=np.uint8)
            hf.create_dataset(f"mask_{i}_segmentation", data=segmentation_array)
            hf.create_dataset(f"mask_{i}_area", data=np.array(mask['area'], dtype=np.float32))
            hf.create_dataset(f"mask_{i}_class", data=np.array(mask['class'], dtype=np.float32))
            hf.create_dataset(f"mask_{i}_GID", data=np.bytes_(mask['GID']))
            hf.create_dataset(f"mask_{i}_bbox", data=np.array(mask['bbox'], dtype=np.float32))

def load_masks_and_info_from_hdf5(output_path, img_name):
    masks = []
    with h5py.File(os.path.join(output_path, f"{img_name}_masks_info.h5"), 'r') as hf:
        i = 0
        while f"mask_{i}_segmentation" in hf:
            mask = {
                'segmentation': hf[f"mask_{i}_segmentation"][:],
                'area': hf[f"mask_{i}_area"][()],
                'class': hf[f"mask_{i}_class"][()],
                'GID': hf[f"mask_{i}_GID"].asstr()[()],
                'bbox': hf[f"mask_{i}_bbox"][:],
            }
            masks.append(mask)
            i += 1
    return masks

# base date

def get_base_date(img_name : str) -> datetime.date:
    """
    This function returns the base date of the images.
    """
    name = img_name.split('_')
    date = name[5][:-4] 
    return datetime.datetime.strptime(date, '%Y%m%d').date()

# get img list
def get_img_list(folder):
    names = []
    for filename in os.listdir(folder):
        if filename.endswith(".tif"):
            names.append(filename)
    return names
