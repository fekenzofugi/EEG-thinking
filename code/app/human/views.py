from flask import (Blueprint, flash, redirect, render_template, request, url_for, session)
import base64
from io import BytesIO
from matplotlib.figure import Figure
from ..auth.views import login_required
import os
import datetime as dt
import matplotlib.pyplot as plt
import sys
import os
import re
import numpy as np
from app.schemas import Project, Dataset, Imagery, Classification, User
from app import db
sys.path.append('../')
import plastic_sniffer.modules.utils as ut
import plastic_sniffer.modules.segmentator as seg
import plastic_sniffer.modules.classify_hard as ch
from plastic_sniffer.human import get_img_list, load_mask_info_db
from plastic_sniffer.segmentation import segment
import torch

human_bp = Blueprint('human', __name__)

@human_bp.before_request
def initialize_session():
        session['time_charge'] = "None"
        # flash("Time charge reseted.")

@human_bp.route('/projects/<string:project_name>/<string:title>/segmentation/', methods=('GET', 'POST'))
@login_required
def segmentation(project_name, title):

    BASE_PATH = f"/data/{project_name}/{title}"
    dataset_id = Dataset.query.filter_by(title=title).first().id
    if not os.path.exists(BASE_PATH):
        flash(f"The directory for {title} does not exist.")
        return redirect(url_for('datasets.index', project_name=project_name))
    # if os.path.exists(f"{BASE_PATH}/output"):
    #     flash(f"{title} has already been segmented.")
    #     return redirect(url_for('datasets.index', project_name=project_name))
    if request.method == 'POST':
        res = request.form['segment']
        if res == 'yes':
            segment(BASE_PATH, dataset_id=dataset_id)
            torch.cuda.empty_cache()  # Clear GPU memory after cloudmask application
            flash(f"Segmentation completed for {title}.")
        return redirect(url_for('datasets.index', project_name=project_name, _method='GET'))

    return render_template('human/segmentation.html')

@human_bp.route('/projects/<string:project_name>/<string:title>/human/', methods=('GET', 'POST'))
@login_required
def human(project_name, title):

    ## TEMPO INICIAL
    if session['time_reset'] == "True":
        session['time_reset'] = "False"
        session['time_init'] = dt.datetime.now().isoformat()
           
    if session['time_charge'] == "None":
        session['time_charge'] = dt.datetime.now().isoformat()
        # flash(f"Time charged successfully. {session['time_charge']}")


    title = request.args.get('title', title)
    BASE_PATH = f"/data/{project_name}/{title}"

    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    IMG_INPUT_PATH = f'{BASE_PATH}/input/'
    MASK_INPUT_PATH = f'{BASE_PATH}/output/'

    if not os.path.exists(MASK_INPUT_PATH):
        flash(f"The directory for {title} masks does not exist.")
        return redirect(url_for('human.segmentation', project_name=project_name, title=title))

    dataset = Dataset.query.filter_by(title=title).first()
    last_image = Imagery.query.filter_by(dataset_id=dataset.id, state=1, labeler_id=session.get('user_id')).order_by(Imagery.gid_prefix).first()
    if last_image is None:
        flash("You don't have any images to validate.")
        return redirect(url_for('datasets.index', project_name=project_name))
    
    n_rois = dataset.num_rois
    n_tiles = dataset.num_tiles
    n_scans = dataset.num_images
    print(n_rois, n_tiles, n_scans)

    IMAGES = int(n_rois) * int(n_tiles) * int(n_scans)
    page = request.args.get('page', 1, type=int)
    total_pages = IMAGES 

    #Load Images
    img_names = get_img_list(IMG_INPUT_PATH)
    img_names.sort()

    BASE_DATE = dataset.starting_date
    BASE_DATE = dt.datetime.strptime(BASE_DATE, '%Y-%m-%d').date()

    # Criar a figura e os eixos fora do loop
    fig_masked = Figure(figsize=(6, 6)) 
    masked_axes = fig_masked.add_subplot(1, 1, 1)
    fig_original = Figure(figsize=(6, 6))
    original_axes = fig_original.add_subplot(1, 1, 1)

    END = False
    regex_1 = r'^[a-zA-Z0-9]{2} [0-9]$'
    regex_2 = r'^[a-zA-Z0-9]{2} [d]$'
    NEXT = False
    CHANGE = False
    DETAIL = False
    FINAL = False
    PREVIOUS = False

    roi = str(last_image.gid_prefix[2])
    tile = str(last_image.gid_prefix[3:5])
    day = str(last_image.gid_prefix[5:])
    args_roi = roi
    args_tile = tile
    args_day = day
    args_roi = request.args.get('roi', args_roi, type=str)
    args_tile = request.args.get('tile', args_tile, type=str)
    args_day = request.args.get('day', args_day, type=str)  
    if not (str(args_roi) == '0' and str(args_tile) == '00' and str(args_day) == '00'):
        roi = args_roi
        tile = args_tile
        day = args_day
        
    
    page = int(roi) * int(n_tiles) + int(tile) * int(n_scans) + int(day) + 1
    gid_prefix = last_image.gid_prefix

    img_name = last_image.image_name
    img_path = IMG_INPUT_PATH + img_name
    try:
        mask = load_mask_info_db(gid_prefix)
        image_orig, image_tif = seg.load_image_tif(img_path, 3000)
    except:
        print("Image not found.")        

    image_class = image_orig.copy()

    masked_axes.clear()
    masked_axes.imshow(image_class, interpolation='none', aspect='auto')
    masked_axes.set_xticks([])
    masked_axes.set_yticks([])
    masked_axes.set_position([0, 0, 1, 1])  # Remove margins

    seg.show_anns_class_db(mask, masked_axes)

    original_axes.clear()
    original_axes.imshow(image_orig, interpolation='none', aspect='auto')
    original_axes.set_xticks([])
    original_axes.set_yticks([])
    original_axes.set_position([0, 0, 1, 1])  # Remove margins

    if request.method == 'POST':

        # Operations on the image
        while (not NEXT) and (not END):
            entrada = request.form['user_input']
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
            elif entrada.lower() == 'previous':
                CHANGE = False
                DETAIL = False
                PREVIOUS = True
                break
            elif entrada.lower() == 'end':
                CHANGE = False
                DETAIL = False
                END = True
                return redirect(url_for('datasets.index', project_name=project_name))
            else:
                break
        

        # Converter time_init de volta para datetime
        time_init = dt.datetime.fromisoformat(session['time_init'])
        time_charge_init = dt.datetime.fromisoformat(session['time_charge'])
        # Calcular o tempo decorrido
        time_end = dt.datetime.now()
        time_charge_elapsed = (time_end -  time_charge_init).total_seconds()
        time_elapsed = (time_end -  time_init).total_seconds()
        # Exibindo o tempo no flash message
        # flash(f"Time elapsed: {time_elapsed}, Time charge elapsed: {time_charge_elapsed}, Diferential: {time_elapsed - time_charge_elapsed}")
        # Atualizar o tempo no banco de dados (acumulando)
        last_image.time_validation_increase(time_elapsed)
        # Atualizando o 'time_init' para o próximo cálculo de tempo
        session['time_init'] = time_end.isoformat()
        # time_init = dt.datetime.now()

        if CHANGE:

            gid_prefix= last_image.gid_prefix
            entrada = entrada.split(' ')
            valor_proc = gid_prefix + entrada[0]
            new_class = int(entrada[1]) 
            result = Classification.query.filter_by(gid=valor_proc).first()
            if result is not None:
                # result.set_field_class(new_class)
                result.field_class = new_class
                db.session.commit()
                masked_axes.clear()
                masked_axes.imshow(image_class)
                masked_axes.set_xticks([])
                masked_axes.set_yticks([])

                seg.show_anns_class_db(mask, masked_axes)
                

            else:
                print(f'GID {valor_proc} não encontrado no CSV.')

        if NEXT:

            gid_prefix = last_image.gid_prefix
            for classification in Classification.query.filter_by(gid_prefix=gid_prefix).all():
                classification.state = 2
            Imagery.query.filter_by(gid_prefix=gid_prefix).first().check_state()
            db.session.commit()
            
            next_image = Imagery.query.filter_by(dataset_id=dataset.id, state=1, labeler_id=session.get('user_id')).order_by(Imagery.gid_prefix).first()
            if next_image is not None:
                roi = str(next_image.gid_prefix[2])
                tile = str(next_image.gid_prefix[3:5])
                day = str(next_image.gid_prefix[5:])
            else:
                END = True
                FINAL = True
                user = User.query.filter_by(id=session.get('user_id')).first()
                user_images = [img for img in user.images_labeling if img.labeler_id == user.id and img.state == 1]
                labeled_images = Imagery.query.filter_by(labeler_id=session.get('user_id'), state=2).all()
                if len(user_images) == 0:
                    user.with_pack = False
                    user.packs_count = user.packs_count + 1

                    # Create full mask of integers for all images
                    full_mask = np.zeros((image_tif.shape[1], image_tif.shape[2]), dtype=np.int8)
                    for image in labeled_images:
                        objects = Classification.query.filter_by(gid_prefix=image.gid_prefix).all()
                        for obj in objects:
                            field_class = obj.field_class
                            mask = np.array(obj.mask)
                            full_mask[mask] = field_class
                        image.full_mask = full_mask.tolist()

                db.session.commit()   
            return redirect(url_for('human.human', project_name=project_name, title=title, roi=roi, tile=tile, day=day, _method='GET'))
        
        if PREVIOUS:

            prev_image = Imagery.query.filter_by(dataset_id=dataset.id, state=2, labeler_id=session.get('user_id')).order_by(Imagery.gid_prefix.desc()).first()
            if prev_image is not None:
                for classification in Classification.query.filter_by(gid_prefix=last_image.gid_prefix).all():
                    classification.state = 1
                prev_image.state = 1
                db.session.commit()
                roi = str(prev_image.gid_prefix[2])
                tile = str(prev_image.gid_prefix[3:5])
                day = str(prev_image.gid_prefix[5:])
            else:
                flash("You are in the first image.")
            return redirect(url_for('human.human', project_name=project_name, title=title, roi=roi, tile=tile, day=day, _method='GET'))
    
    buf = BytesIO()
    fig_masked.savefig(buf, format="svg")
    buf.seek(0)
    img = buf.getvalue().decode("utf-8")
    buf.close()

    buf2 = BytesIO()
    buf2.seek(0)
    buf2.truncate()
    fig_original.savefig(buf2, format="png")
    # Embed the result in the html output.
    original_image = base64.b64encode(buf2.getbuffer()).decode("ascii")
    buf2.close()

    plt.ioff()
    plt.close(fig_masked)
    plt.close(fig_original)

    return render_template('human/human.html', project_name=project_name, title=title, roi=roi, tile=tile, day=day, total_pages=total_pages, page=page, img=img, original_image=original_image, detail=DETAIL, final=FINAL)