import pandas as pd
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.plot import show
import os

def output_from_csv(data_path,img_name, mask, output_path):
    file_path = os.path.join(data_path, "input", f'{img_name}.tif')
    dataframe = pd.read_csv(os.path.join("data/output", 'classifications.csv'))
    with rasterio.open(file_path) as src:
        out_shape = (src.height, src.width)
    labels = np.zeros(out_shape, dtype=np.uint8)
    for obj in mask:
        gid = obj['GID']
        segmentation = obj['segmentation']
        classification = dataframe.loc[dataframe['GID'] == gid, 'class'].values[0]
        labels[segmentation == 1] = classification
    outdir = os.path.join(data_path, "labels")
    os.makedirs(outdir, exist_ok=True)
    output_path = os.path.join(outdir, f'{img_name}_labels.tif')
    add_layer_to_tiff(file_path, labels, output_path)

def output_from_db(db, img_name, mask, output_path):
    pass

def add_layer_to_tiff(input_tiff_path, new_layer_data, output_tiff_path):
    # Open the original TIFF file
    with rasterio.open(input_tiff_path) as src:
        # Read the original data
        original_data = src.read()
        original_meta = src.meta

        # Create a new layer with the same dimensions as the original data
        new_layer = np.array(new_layer_data, dtype=original_data.dtype)

        # Stack the new layer with the original data
        new_data = np.vstack((original_data, new_layer[np.newaxis, ...]))

        # Update the metadata to reflect the new number ofa layers
        original_meta.update(count=new_data.shape[0])

        # Write the new data to a new TIFF file
        with rasterio.open(output_tiff_path, 'w', **original_meta) as dst:
            dst.write(new_data)