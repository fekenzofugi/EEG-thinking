import plastic_sniffer.modules.segmentator as seg 
import plastic_sniffer.modules.utils as ut
import plastic_sniffer.modules.classify_tree as ct
import plastic_sniffer.modules.classify_hard as ch
import matplotlib.pyplot as plt
import datetime
import numpy as np
import time
import shutil
import os
import argparse
from app.schemas import Imagery, Dataset, Satellite
from app import db
import torch

def segment(BASE_PATH, dataset_id):

    import os
    torch.cuda.empty_cache() 
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    #Define constants
    s2_path = BASE_PATH + '/Sentinel-2/'
    input_path = BASE_PATH + '/input/'
    output_path = BASE_PATH + '/output/'
    model_path = '/'.join(BASE_PATH.split("/")[:-1]) + '/models/'

    if not os.path.exists(input_path):
        os.makedirs(input_path)

    for file_name in os.listdir(s2_path):
        full_file_name = os.path.join(s2_path, file_name)
        if os.path.isfile(full_file_name):
            shutil.copy(full_file_name, input_path)
    masker = seg.load_sam()
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    if not os.path.exists(input_path):
        os.makedirs(input_path)
    if not os.path.exists(model_path):
        os.makedirs(model_path)
        REF_NAME = 'tree_att.pkl'
        # Copy the tree model file from ../Checkpoints to model_path
        src_model_path = f"Checkpoints/{REF_NAME}"
        dst_model_path = os.path.join(model_path, 'tree_att.pkl')
        if os.path.exists(src_model_path):
            shutil.copy(src_model_path, dst_model_path)
        else:
            raise FileNotFoundError(f"Model file not found at {src_model_path}")

    time_hist = []

    img_names = ut.get_img_list(input_path)
    img_names.sort()

    #Renomeando imagens
    for arquivo in img_names:
        if arquivo.endswith('.tif') and not arquivo.startswith('Img'):
            name = arquivo.split('_')
            roi = name[0][3:]
            date = name[1]
            tile = name[-1][:-4]
            satellite_tile = f"{name[5]}_{name[6]}_{name[7]}"
            old_path = os.path.join(input_path, arquivo)
            new_name = f"ImgROI_{roi}_Tile_{tile}_Date_{date}.tif"
            new_path = os.path.join(input_path, new_name)
            os.rename(old_path, new_path)
            # adicionar satélite ao banco de dados
            satellite = db.session.query(Satellite).filter(Satellite.satellite_tile == satellite_tile).first()
            satellite_id = None
            if satellite is None:
                satellite = Satellite(satellite_tile)
                db.session.add(satellite)
                db.session.commit()
                satellite_id = Satellite.query.filter_by(satellite_tile=satellite_tile).first().id
            else:
                satellite_id = satellite.id
                satellite = Satellite(satellite_tile)
                db.session.add(satellite)
                db.session.commit()
                satellite_id = Satellite.query.filter_by(satellite_tile=satellite_tile).first().id
            # adicionar imagem ao banco de dados
            imagery = Imagery(
                image_name=new_name,
                dataset_id=dataset_id,
                subpoint_id=int(tile),
                date=date,
                satellite_id=satellite_id
            )
            
            db.session.add(imagery)
    db.session.commit()
    Imagery.generate_gid_prefix()

    img_names = ut.get_img_list(input_path)
    img_names.sort()

    tempo_inicial_total = time.time()
    # Load the Decision Tree model
    time_load_start = time.time()
    model = ct.load_tree(model_path + 'tree_att.pkl')
    time_load_end = time.time()
    print(f"Modelo carregado em: {time_load_end - time_load_start:.2f} segundos!")
    for img_name in img_names:
        print(f'Iniciando:{img_name}')
        start_time = time.time()
        img_path = input_path + img_name
        image, img_tif = seg.load_image_tif(img_path, 3000)
        image = seg.overlay_predictions(image, img_tif[-2])
        masks = seg.segment(image, masker)
        polygons = seg.masks_to_polygons(masks, img_path, output_path)
        masks = seg.polygons_to_masks(polygons, img_path)
        for obj in masks:
            obj['class'] = ch.hard_classify(img_tif, obj)
        masks = [m for m in masks if m['class'] != 5]
        ut.export_to_db(masks, img_name)
        seg.save_masks(image, masks, img_name, output_path)
        # Salvar máscaras e informações de segmentação em HDF5
        # print(f"Salvando máscaras e informações de segmentação em HDF5 para {img_name} em {output_path}")
        # ut.save_masks_and_info_as_hdf5(masks, output_path, img_name)
        end_time = time.time()
        elapsed_time = end_time - start_time
        # Salvar o tempo de processamento no banco de dados
        imagem = Imagery.query.filter_by(image_name=img_name).first()
        if imagem is not None:
            # Atualizar o tempo de segmentação no banco de dados
            imagem.set_time_segmentation(elapsed_time)
            db.session.commit()
        else:
            print(f"Imagem {img_name} não encontrada no banco de dados.")
        time_hist.append(elapsed_time)
        print(f"Imagem {img_name}, processada com sucesso em : {elapsed_time:.2f} segundos!")
    # descobrir o project_name
    project_name = BASE_PATH.split("/")[-2]
    # Classify the csv file
    time_tree_start = time.time()
    ct.classify_tree_db(project_name, model)
    time_tree_end = time.time()
    print(f"Classificação pela árvore concluída em: {time_tree_end - time_tree_start:.2f} segundos!")
    tempo_total = time.time() - tempo_inicial_total
    print(f"Processamento finalizado!\n Foram processadas {len(img_names)} imagens em: {tempo_total:.2f} segundos!")
    shutil.rmtree(s2_path)
