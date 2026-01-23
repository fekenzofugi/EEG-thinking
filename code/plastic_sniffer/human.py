import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import h5py
import ast
import sys
import os
import warnings
import contextlib
import logging
import re
sys.path.append('../')
import plastic_sniffer.modules.utils as ut
import plastic_sniffer.modules.segmentator as seg
import plastic_sniffer.modules.classify_hard as ch
from app import db
from app.schemas import Imagery, Classification
import json

# Suprimir avisos do matplotlib
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

# Suprimir avisos do numpy
warnings.filterwarnings("ignore", category=RuntimeWarning, module="numpy")

# Configurar logging para suprimir mensagens de erro
logging.getLogger('matplotlib').setLevel(logging.ERROR)


#This module

def get_img_list(folder):
    names = []
    for filename in os.listdir(folder):
        if filename.endswith(".tif"):
            names.append(filename)
    return names

def load_mask_info(img_name, MASK_INPUT_PATH):
    try:
        masks = ut.load_masks_and_info_from_hdf5(MASK_INPUT_PATH, img_name)
    except:
        print('Error loading masks')
        masks = None
    return masks

def load_mask_info_db(gid_prefix):
    objects = Classification.query.filter(Classification.gid_prefix == gid_prefix).all()
    masks = []
    for obj in objects:
        dictionary = {
            "segmentation": obj.mask,
            "area": obj.area,
            "GID": obj.gid
        }
        masks.append(dictionary)
    return masks

def move_figure(f, x, y):
    backend = plt.get_backend()
    if backend == 'TkAgg':
        f.canvas.manager.window.wm_geometry(f"+{x}+{y}")
    elif backend == 'WXAgg':
        f.canvas.manager.window.SetPosition((x, y))
    else:
        print(f"Backend {backend} não suportado para mover a janela")


def human_classify(BASE_PATH):
    matplotlib.use('TkAgg')

    IMG_INPUT_PATH = f'{BASE_PATH}/input/'
    MASK_INPUT_PATH = f'{BASE_PATH}/output/'

    csv = pd.read_csv(f'{MASK_INPUT_PATH}/classifications.csv', index_col=0)

    last_value = csv.iloc[-1, 0]
    n_rois = ut.ascii_to_int(last_value[0]) + 1
    n_tiles = ut.ascii_to_int(last_value[1]) + 1
    n_scans = ut.ascii_to_int(last_value[2]) + 1
    print(n_rois, n_tiles, n_scans)

    #Load Images
    img_names = get_img_list(IMG_INPUT_PATH)
    img_names.sort()
    BASE_DATE = ut.get_base_date(img_names[0])

    #Activate interactive mode
    plt.ion()
    # Criar a figura e os eixos fora do loop
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    fig.suptitle(f'Legenda: 1 - Plástico ; 2 - Plantação ; 3 - Dúvida ; 0 - Outros', fontsize=16)
    move_figure(fig, 100, 100)
    with plt.ioff():
        fig2, axes_d = plt.subplots(2, 1, figsize=(6, 6))
        move_figure(fig2, 1300, 100)

    END = False
    regex_1 = r'^[a-zA-Z0-9]{2} [0-3]$'
    regex_2 = r'^[a-zA-Z0-9]{2} [d]$'
    for roi in range(n_rois):
        if END:
            break
        for tile in range(n_tiles):
            if END:
                break
            for day in range(n_scans):
                if END:
                    break
                NEXT = False
                CHANGE = False
                DETAIL = False

                gid_prefix = f'{ut.int_to_ascii(roi)}{ut.int_to_ascii(tile)}{ut.int_to_ascii(day)}'
                validation_values = csv.loc[csv['GID'].str.startswith(gid_prefix), 'validated']
                if validation_values.eq(1).all():
                    continue

                date = (BASE_DATE + dt.timedelta(days=day*5)).strftime('%Y%m%d')
                img_name = f'ImgROI_{roi}_Tile_{tile:02d}_Date_{date}.tif'
                img_path = IMG_INPUT_PATH + img_name
                try:
                    mask = load_mask_info(img_name, MASK_INPUT_PATH)
                    image_orig, image_tif = seg.load_image_tif(img_path, 3000)
                except:
                    print(f'Não existe a imagem: ROI {roi}, Tile {tile} e Data {date}.')
                    continue
                print(f'Nome da imagem: {img_name}')
                image_class = image_orig.copy()

                # Atualizar os dados do plot
                axes[0].clear()
                axes[0].imshow(image_class)
                axes[0].set_title(f'Image {roi}-{tile}-{day} (Class)')
                
                # seg.show_anns_index(mask, image_tif, axes[0])
                seg.show_anns_class_bank(mask, axes[0],csv)
                
                axes[1].clear()
                axes[1].imshow(image_orig)
                axes[1].set_title(f'Image {roi}-{tile}-{day} (Original)')

                fig.canvas.draw()
                fig.canvas.flush_events()

                # Operations on the image
                while (not NEXT) and (not END):
                    # Input request
                    while True:
                        entrada = input("Digite o valor de processamento (5 caracteres alfanuméricos seguidos por um número de 0 a 2): ")
                        if re.match(regex_1, entrada):
                            CHANGE = True
                            DETAIL = False
                            break
                        elif re.match(regex_2, entrada):
                            CHANGE = False
                            DETAIL = True
                            break
                        elif entrada.lower() == 'next': 
                            CHANGE = False
                            DETAIL = False
                            NEXT = True
                            break
                        elif entrada.lower() == 'end':
                            CHANGE = False
                            DETAIL = False
                            END = True
                            break
                        else:
                            print("Input inválido. Tente novamente.")
                    # Input processing
                    if CHANGE:
                        entrada = entrada.split(' ')
                        valor_proc = gid_prefix + entrada[0]
                        new_class = int(entrada[1]) 
                        result = csv.loc[csv['GID'] == valor_proc]
                        if not result.empty:
                            csv.loc[csv['GID'] == valor_proc, 'class'] = new_class
                            csv.to_csv('./Data/output/classifications.csv')
                            print(f'a entrada foi: {entrada}, o GID do objeto é: {valor_proc} e a nova classificação é: {new_class}')

                            # Atualizar os dados do plot
                            axes[0].clear()
                            axes[0].imshow(image_class)
                            axes[0].set_title(f'Image {roi}-{tile}-{day} (Class)')
                            # seg.show_anns_index(mask, image_tif, axes[0])
                            seg.show_anns_class_bank(mask, axes[0],csv)
                            fig.canvas.draw()
                            fig.canvas.flush_events()
                        else:
                            print(f'GID {valor_proc} não encontrado no CSV.')
                    elif DETAIL:
                        entrada = entrada.split(' ')
                        valor_proc = gid_prefix + entrada[0]
                        result = csv.loc[csv['GID'] == valor_proc]
                        if not result.empty:
                            xr, yr = ch.reflectance(image_tif, next((item for item in mask if item.get('GID') == valor_proc), None))
                            axes_d[0].plot(xr, yr, label=valor_proc, marker='o')
                            axes_d[0].set_title(f'Espectral Reflectance')
                            axes_d[0].legend()
                            xind, yind = ch.indexes(image_tif, next((item for item in mask if item.get('GID') == valor_proc), None))
                            axes_d[1].plot(xind, yind, label=valor_proc, marker='o')
                            axes_d[1].set_title(f'Indexes')
                            axes_d[1].legend()
                            fig2.canvas.draw()
                            fig2.canvas.flush_events()
                            fig2.show()

                        else:
                            print(f'GID {valor_proc} não encontrado no CSV.')
                    if not DETAIL:
                        plt.close(fig2)
                        with plt.ioff():
                            # fig2 = plt.figure(2, figsize=(6, 3))
                            # dx = fig2.add_subplot(2, 1, 1)
                            fig2, axes_d = plt.subplots(2, 1, figsize=(6, 6))
                            move_figure(fig2, 1300, 100)
                    if NEXT:
                        csv.loc[csv['GID'].str.startswith(gid_prefix), 'validated'] = 1
                        csv.to_csv('./Data/output/classifications.csv')
                    
                
    plt.ioff()
    plt.close(fig)
    plt.close(fig2)