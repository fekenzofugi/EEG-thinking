## Set-up
import numpy as np
import torch
import matplotlib.pyplot as plt
import cv2
import rasterio
import pandas as pd
from PIL import Image
import os

from app.schemas import Classification

import fiona
from shapely.geometry import shape, mapping
from shapely.geometry.polygon import Polygon
from shapely.geometry.multipolygon import MultiPolygon

import rasterio.features
from shapely.geometry import shape
import geopandas as gpd

import sys
from plastic_sniffer.segment_anything import sam_model_registry, SamAutomaticMaskGenerator
import plastic_sniffer.modules.classify_hard as clah
import time

# Function to display masks overlaid on the image
def show_anns(anns, ax=None):
    '''Show annotations on the image'''
    if len(anns) == 0:
        return
    sorted_anns = sorted(anns, key=(lambda x: x['area']), reverse=True)
    
    if ax is None:
        ax = plt.gca()
    ax.set_autoscale_on(False)

    img = np.ones((sorted_anns[0]['segmentation'].shape[0], sorted_anns[0]['segmentation'].shape[1], 4))
    img[:,:,3] = 0
    for ann in sorted_anns:
        m = ann['segmentation']
        color_mask = np.concatenate([np.random.random(3), [0.35]])
        img[m] = color_mask
    ax.imshow(img)

def show_anns_index(anns, img_tif, ax=None, index:str = None):
    if len(anns) == 0:
        return
    indexes = {'PMLI': clah.PMLI, 'NDVI': clah.NDVI, 'BSI': clah.BSI, 'NBSPI': clah.NBSPI}
    if index is not None:
        if index not in indexes:
            print('Invalid index')
            return
        index_function = indexes[index]
    sorted_anns = sorted(anns, key=(lambda x: x['area']), reverse=True)
    if ax is None:
        ax = plt.gca()
    ax.set_autoscale_on(False)

    img = np.ones((sorted_anns[0]['segmentation'].shape[0], sorted_anns[0]['segmentation'].shape[1], 4))
    img[:,:,3] = 0
    for i, ann in enumerate(sorted_anns):
        m = ann['segmentation']
        if index is None:
            index_result = [round(functions(img_tif, ann), 2) for functions in indexes.values()]
        else:
            index_result = round(index_function(img_tif, ann), 2)
        
        color_mask = np.concatenate([np.random.random(3), [0.35]])
        if index is None:
            index_result = "\n".join(map(str, index_result))

        img[m] = color_mask
        y, x = np.where(m)
        # Get the center of the mask to place the text
        if len(x) > 0 and len(y) > 0:
            center_x = int(np.mean(x))
            center_y = int(np.mean(y))
            ax.text(center_x, center_y, index_result, color='white', fontsize=10, ha='center', va='center')
                
    ax.imshow(img)

def show_anns_class(anns, ax=None):
    if len(anns) == 0:
        return
    sorted_anns = sorted(anns, key=(lambda x: x['area']), reverse=True)
    
    if ax is None:
        ax = plt.gca()
    ax.set_autoscale_on(False)

    img = np.ones((sorted_anns[0]['segmentation'].shape[0], sorted_anns[0]['segmentation'].shape[1], 4))
    img[:,:,3] = 0
    for i, ann in enumerate(sorted_anns):
        m = ann['segmentation']
        color = np.random.uniform(0.5, 1)
        class_colors = {
            0: [color, 0, 0, 0.35],  # Red with alpha 0.35 # Soil
            1: [color, color, 0, 0.35],  # Yellow with alpha 0.35 # Herb
            2: [0, 0, color, 0.35],  # Blue with alpha 0.35 # Plastic
            3: [0, color, color, 0.35],  # Cyan with alpha 0.35 # Grow
            4: [0, color, 0, 0.35],  # Green with alpha 0.35 # Vegetation
            5: [color, color, color, 0.35],  # White with alpha 0.35 # Cloud
            6: [color, 0, color, 0.35],  # Purple with alpha 0.35 # Florest
            7: [0, 0, 0, 0.65],  # Black with alpha 0.35 # Other
        }
        color_mask = class_colors.get(ann['class'], [1, 1, 1, 0.35])  # Default to white with alpha 0.35 if class not found
            

        img[m] = color_mask
        y, x = np.where(m)
        # Get the center of the mask to place the text
        if len(x) > 0 and len(y) > 0:
            center_x = int(np.mean(x))
            center_y = int(np.mean(y))
            label = ann['GID'] +" "+ str(ann['class'])
            ax.text(center_x, center_y, label, color='white', fontsize=8, ha='center', va='center')
                
    ax.imshow(img)

def show_anns_class_bank(anns, ax=None, csv : pd.DataFrame = None):
    if len(anns) == 0:
        return
    sorted_anns = sorted(anns, key=(lambda x: x['area']), reverse=True)
    
    if ax is None:
        ax = plt.gca()
    ax.set_autoscale_on(False)

    img = np.ones((sorted_anns[0]['segmentation'].shape[0], sorted_anns[0]['segmentation'].shape[1], 4))
    img[:,:,3] = 0
    for i, ann in enumerate(sorted_anns):
        m = ann['segmentation']
        color = np.random.uniform(0.5, 1)
        # list_class = ['soil', 'herb', 'plastic', 'grow', 'vegetation', 'cloud', 'florest', 'other']
        # class_numbers = [0, 1, 2, 3, 4, 5, 6, 7]
        class_colors = {
            0: [color, 0, 0, 0.35],  # Red with alpha 0.35 # Soil
            1: [color, color, 0, 0.35],  # Yellow with alpha 0.35 # Herb
            2: [0, 0, color, 0.35],  # Blue with alpha 0.35 # Plastic
            3: [0, color, color, 0.35],  # Cyan with alpha 0.35 # Grow
            4: [0, color, 0, 0.35],  # Green with alpha 0.35 # Vegetation
            5: [color, color, color, 0.35],  # White with alpha 0.35 # Cloud
            6: [color, 0, color, 0.35],  # Purple with alpha 0.35 # Florest
            7: [0, 0, 0, 0.65],  # Black with alpha 0.35 # Other
        }
        classification = csv.loc[csv['GID'] == ann['GID']].values[0][10]
        # color_mask = class_colors.get(ann['class'], [1, 1, 1, 0.35])  # Default to white with alpha 0.35 if class not found # Get from mask
        color_mask = class_colors.get(classification, [0, 0, 0, 0.35])  # Default to black with alpha 0.35 if class not found # Get from csv
            
        img[m] = color_mask
        y, x = np.where(m)
        # Get the center of the mask to place the text
        if len(x) > 0 and len(y) > 0:
            center_x = int(np.mean(x))
            center_y = int(np.mean(y))
            label = ann['GID'][-2:] +" "+ str(classification)
            ax.text(center_x, center_y, label, color='white', fontsize=8, ha='center', va='center')

        # Draw the contour of the object in black
        contours, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            ax.plot(contour[:, 0, 0], contour[:, 0, 1], color='black', linewidth=1)
    ax.imshow(img)

def show_anns_class_db(anns, ax=None):
    if len(anns) == 0:
        return
    sorted_anns = sorted(anns, key=(lambda x: x['area']), reverse=True)
    
    if ax is None:
        ax = plt.gca()
    ax.set_autoscale_on(False)

    img = np.ones((np.array(sorted_anns[0]['segmentation']).shape[0], np.array(sorted_anns[0]['segmentation']).shape[1], 4))
    img[:,:,3] = 0
    for i, ann in enumerate(sorted_anns):
        m = ann['segmentation']
        color = np.random.uniform(0.5, 1)
        class_colors = {
            0: [0, 0, 0, 0.65],  # Black with alpha 0.35 # Other
            1: [color, 0, 0, 0.35],  # Red with alpha 0.35 # Soil
            2: [color, color, 0, 0.35],  # Yellow with alpha 0.35 # Herb
            3: [0, 0, color, 0.35],  # Blue with alpha 0.35 # Plastic
            4: [0, color, color, 0.35],  # Cyan with alpha 0.35 # Grow
            5: [0, color, 0, 0.35],  # Green with alpha 0.35 # Vegetation
            6: [color*(35/255), color*(120/255), color, 0.35],  # Green with alpha 0.35 # Vegetation
            7: [color, 0, color, 0.35],  # Purple with alpha 0.35 # Florest
            8: [color, color, color, 0.65],  # White with alpha 0.35 # Unknown
        }
        classification = Classification.query.filter_by(gid=ann['GID']).first().field_class
        color_mask = class_colors.get(classification, [0, 0, 0, 0.35])  # Default to black with alpha 0.35 if class not found # Get from csv
            
        img[m] = color_mask
        y, x = np.where(m)
        # Get the center of the mask to place the text
        if len(x) > 0 and len(y) > 0:
            center_x = int(np.mean(x))
            center_y = int(np.mean(y))
            label = ann['GID'][-2:] +" "+ str(classification)
            ax.text(center_x, center_y, label, color='white', fontsize=8, ha='center', va='center')

        # Draw the contour of the object in black
        contours, _ = cv2.findContours(np.array(m).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            ax.plot(contour[:, 0, 0], contour[:, 0, 1], color='black', linewidth=1)
    ax.imshow(img)

def load_image_jpg(img_path):
    '''
    Load an .jpg image from the input folder.

    Parameters:
        img_path (str): The path of the image file to load
    '''
    image = cv2.imread(img_path + '.jpg')
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return image

def load_image_tif(img_path, factor=5000):
    '''
    Load an .tif image from the input folder.

    Parameters:
        img_path (str): The path of the image file to load.
        factor (int): The factor to divide the image by. Default is 5000.

    Returns:
        np.array: The image in RGB format.
        np.array: The image in tif format.
    '''
    if factor == 0:
        factor = 5000
    if not img_path.endswith(".tif"):
        img_path = img_path + '.tif'
    # Possíveis valores para o parâmetro dtype:
    # 'uint8', 'uint16', 'int16', 'uint32', 'int32', 'float32', 'float64', 'complex', 'complex64', 'complex128'
    src = rasterio.open(
        img_path,
        mode='r',
        driver='GTiff',
        count=None,
        crs='EPSG:4326', #TODO - Verificar se é necessário alterar
        transform=None,
        dtype='float32', 
    )
    # Converter as imagens para o formato RGB  partir do tif (Sentinel-2)
    image_tif = src.read()
    image = np.moveaxis(image_tif[[3, 2, 1]], 0, -1) / factor    
    return image, image_tif

def convert_tif_to_jpg(image , img_path):
    '''
    Convert an image from float to uint8 and from tif to jpg.

    Parameters:
        image (np.array): The image to convert.
    '''
    output_image = Image.fromarray((image * 255).astype(np.uint8))
    img_path = img_path + '.jpg'
    output_image.save(img_path)
    return True

def load_sam():
    '''
    Load the SAM model.
    '''
    sam_path = "Checkpoints/"
    sam_checkpoint = sam_path + "sam_vit_l_0b3195.pth"
    model_type = "vit_l"
    device = "cuda"
    sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
    sam.to(device=device)
    masker = SamAutomaticMaskGenerator(
        model=sam,
        points_per_side=32,
        pred_iou_thresh=0.86,
        stability_score_thresh=0.92,
        crop_n_layers=1,
        crop_n_points_downscale_factor=2,
        min_mask_region_area=100,  # Requires open-cv to run post-processing
    )
    return masker

# Functions to convert a mask to a polygon
def mask_to_polygon(mask):
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    polygons = [Polygon(contour[:, 0, :]) for contour in contours if len(contour) > 2]
    return MultiPolygon(polygons)

# Função para salvar os polígonos em um arquivo Shapefile
def save_polygons_to_shapefile(polygons, filepath, schema):
    '''
    Save polygons to a shapefile.
    Parameters:
        polygons (list): The list of polygons to save.
        filepath (str): The path to save the shapefile.
        schema (dict): The schema of the shapefile.
    '''
    with fiona.open(filepath, 'w', 'ESRI Shapefile', schema) as c:
        for i, polygon in enumerate(polygons):
            c.write({
                'geometry': mapping(polygon),
                'properties': {'id': i},
            })

def segment(image, masker):
    #TODO verify the format of image
    mask = masker.generate(image)
    for m in mask:
        m['GID'] = ''
        m['class'] = 0
    return mask

def save_masks(image, masks, img_name, output_path):
    fig, ax = plt.subplots(figsize=(20, 20))
    ax.imshow(image)
    show_anns(masks)
    ax.axis('off')

    # Salva a figura em um arquivo JPG
    fig.savefig(output_path + img_name +' - Mask' + '.jpg', bbox_inches='tight', pad_inches=0)
    plt.close(fig)

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
 
def save_polygons(masks, img_name, output_path):
        # Converter todas as máscaras em polígonos
    polygons = [mask_to_polygon(mask['segmentation']) for mask in masks]

    # Definir o esquema do arquivo vetorizado
    schema = {
        'geometry': 'MultiPolygon',
        'properties': {'id': 'int'},
    }

    # Especificar o caminho e o nome do arquivo
    mask_path = output_path + 'masks/'
    create_directory(mask_path)
    
    filepath = mask_path + img_name + '.shp'  # Altere este valor conforme necessário

    # Salvar os polígonos no arquivo especificado
    save_polygons_to_shapefile(polygons, filepath, schema)

def generate_gdf(masks, img_path):
    # Abrir a imagem para obter metadados geográficos
    with rasterio.open(img_path) as src:
        transform = src.transform  # Transformação espacial (pixel -> coordenada)
        crs = src.crs  # Sistema de coordenadas
    # Inicializar lista para guardar os polígonos
    geometries = []
    # Iterar sobre todos os objetos na lista `masks`
    for mask in masks:
        # Obter a máscara binária de cada objeto
        mascara = mask['segmentation']  # Array binário (True/False)
        # Converter a máscara para 'uint8' e gerar polígonos
        polygons = rasterio.features.shapes(mascara.astype('uint8'), transform=transform)
        # Adicionar os polígonos ao conjunto de geometria
        geometries.extend([shape(geom) for geom, value in polygons if value == 1])
    # Criar GeoDataFrame com todas as geometrias extraídas
    gdf = gpd.GeoDataFrame({'geometry': geometries}, crs=crs)
    return gdf

def separete_polygons(gdf):
    l_polygonos = gdf.iterrows()
    l_polygonos = list(l_polygonos)
    l_polygonos.sort(key=lambda x: x[1].geometry.area, reverse=True)
    # Identificar relações entre polígonos
    from shapely.geometry import Polygon
    # Supondo que gdf contém os polígonos
    for idx_maior, pol_maior in l_polygonos:
        for idx_menor, pol_menor in l_polygonos:
            if idx_maior != idx_menor and pol_maior.geometry.area > pol_menor.geometry.area:  # Evitar auto-interseção
                # Calcular interseção
                interseccao = pol_maior.geometry.intersection(pol_menor.geometry)
                # Criar buraco apenas se houver interseção
                if not interseccao.is_empty and not interseccao.contains(pol_maior.geometry):
                    gdf.at[idx_maior, 'geometry'] = pol_maior.geometry.difference(interseccao)
    return gdf

def individualize_polygons(gdf):
    # GeoDataFrame de exemplo (gdf já existente)
    novas_geometrias = []  # Lista para armazenar os polígonos separados
    for idx, row in gdf.iterrows():
        geometria = row.geometry
        # Verificar se a geometria é um MultiPolygon
        if isinstance(geometria, MultiPolygon):
            # Adicionar cada polígono individual ao novo conjunto
            novas_geometrias.extend(list(geometria.geoms))
        else:
            # Se for um Polygon normal, adicionar diretamente
            novas_geometrias.append(geometria)
    # Criar um novo GeoDataFrame com as geometrias contínuas separadas
    gdf_separado = gpd.GeoDataFrame({'geometry': novas_geometrias}, crs=gdf.crs)
    return gdf_separado
    
def masks_to_polygons(masks, img_path, output_path):
    '''
    Save the masks to a shapefile.
    '''
    gdf = generate_gdf(masks, img_path)
    gdf = separete_polygons(gdf)
    gdf = individualize_polygons(gdf)
    
    # Salvar o resultado ou continuar manipulando
    # gdf.to_file(os.path.join(output_path,"polygons.shp")) //TODO #7 - Verificar se é necessário salvar
    return gdf

def polygons_to_masks(polygons, img_path):
    # Carregar o shapefile
    gdf = polygons
    # Abrir a imagem para obter metadados geográficos
    with rasterio.open(img_path) as src:
        img_tif = src.read()
        transform = src.transform  # Transformação espacial (pixel -> coordenada)
        out_shape = (src.height, src.width)  # Tamanho da imagem
        crs = src.crs  # Sistema de coordenadas
    # Inicializar uma máscara binária com zeros
    mask = [{'segmentation' :np.zeros(out_shape, dtype=np.uint8)} for _ in range(len(gdf))]
    # Iterar sobre cada geometria no GeoDataFrame
    for idx, row in gdf.iterrows():
        geom = row.geometry
        # Rasterizar a geometria e adicionar à máscara
        geom_mask = rasterio.features.geometry_mask([(geom,1)], transform=transform, invert=True, out_shape=out_shape)    
        mask[idx]['segmentation'] = geom_mask
        mask[idx]['m_area'] = geom.area
        mask[idx]['area'] = geom_mask.sum()
        mask[idx]['GID'] = ''
        mask[idx]['class'] = 0
        mask[idx]['geometry'] = geom
        contours, _ = cv2.findContours(geom_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            mask[idx]['bbox'] = (x, y, w, h)

        _ , mask[idx]['indexes'] = clah.indexes(img_tif, mask[idx])
    # Create a new list to store the filtered masks
    filtered_mask = [m for m in mask if 60000 >= m['area'] >= 150]
    mask = filtered_mask
    return mask

def overlay_predictions(image, prediction):

    # Create an overlay image
    overlay = image.copy() 
    overlay[prediction == 1] = 0
    
    return overlay

def main():

        # Load the image
    NAME = "Imagem C"
    BASE_PATH = '../Data/'
    img_path = BASE_PATH + 'input/' + NAME
    image = load_image_tif(img_path)
    
        # Load the SAM model
    sam_path = "Checkpoints/"
    sam_checkpoint = sam_path + "sam_vit_h_4b8939.pth"
    model_type = "vit_h"
    device = "cuda"
    sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
    sam.to(device=device)
    # Create a fast predictor
    mask_generator_fast = SamAutomaticMaskGenerator(sam)
    # Create a detail predictor
    mask_generator_det = SamAutomaticMaskGenerator(
        model=sam,
        points_per_side=32,
        pred_iou_thresh=0.86,
        stability_score_thresh=0.92,
        crop_n_layers=1,
        crop_n_points_downscale_factor=2,
        min_mask_region_area=100,  # Requires open-cv to run post-processing
    )


    # Generate masks
    start_time_fast = time.time()
    mask_f = mask_generator_fast.generate(image)
    end_time_fast = time.time()
    print(f"Fast mask generation took {end_time_fast - start_time_fast} seconds")

    start_time_det = time.time()
    mask_d = mask_generator_det.generate(image)
    end_time_det = time.time()
    print(f"Detailed mask generation took {end_time_det - start_time_det} seconds")

    
    # Mask generation returns a list over masks, where each mask is a dictionary containing various data about the mask. These keys are:
    # * `segmentation` : the mask
    # * `area` : the area of the mask in pixels
    # * `bbox` : the boundary box of the mask in XYWH format
    # * `predicted_iou` : the model's own prediction for the quality of the mask
    # * `point_coords` : the sampled input point that generated this mask
    # * `stability_score` : an additional measure of mask quality
    # * `crop_box` : the crop of the image used to generate this mask in XYWH format

    '''
    Show all the masks overlayed on the image.
    '''
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))

    # First subplot with the fast mask
    ax1.imshow(image)
    show_anns(mask_f, ax=ax1)
    ax1.axis('off')
    ax1.set_title('Fast Mask')

    # Second subplot with the detailed mask
    ax2.imshow(image)
    show_anns(mask_d, ax=ax2)
    ax2.axis('off')
    ax2.set_title('Detailed Mask')

    plt.show()
    
    '''
    ## Automatic mask generation options
    There are several tunable parameters in automatic mask generation that control how densely points are sampled 
    and what the thresholds are for removing low quality or duplicate masks.
    Additionally, generation can be automatically run on crops of the image to get improved performance on smaller objects, 
    and post-processing can remove stray pixels and holes. Here is an example configuration that samples more masks:
    '''

if __name__ == '__main__':
    main()


