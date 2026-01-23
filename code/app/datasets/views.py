from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, session)
from werkzeug.exceptions import abort
import json
from ..auth.views import login_required
from ..schemas import Dataset, Project, User
from .. import db
import os
from utils.generate_dataset import generate_training_dataset, generate_counting_dataset
from utils.gif_generator import generate_gif
from utils.files_info import get_files_info
import sys
import time
import os
import requests
sys.path.append('../')



datasets_bp = Blueprint('datasets', __name__)

data = ["Sentinel-1", "Sentinel-2", "Fused"]
ds_types = ['Training', 'Counting']
dimensions = ['256x256','512x512']

@datasets_bp.route('/projects/<string:project_name>/')
def index(project_name):
    project = db.session.query(Project).filter_by(project_name=project_name).first()
    datasets = db.session.query(Dataset).filter_by(project_id=project.id).all()
    current_user = db.session.query(User).filter_by(id=session.get('user_id')).first()
    users = User.get_all_users()
    session["time_reset"] = "True"
    return render_template('datasets/index.html', users=users, project_name=project_name, project=project, datasets=datasets, current_user=current_user)

@datasets_bp.route('/projects/<string:project_name>/create/rois')
@login_required
def rois(project_name):
    return redirect(f"/solara_app/?project_name={project_name}&username={session.get('username')}")

@datasets_bp.route('/projects/<string:project_name>/create', methods=('GET', 'POST'))
@login_required
def create(project_name):
    bind_data_path = f"/data/{project_name}/{session.get('username')}/rois"
    num_rois, rois_ids = get_files_info(bind_data_path)
    project = db.session.query(Project).filter_by(project_name=project_name).first()
    service_account = project.service_account
    if request.method == 'POST':
        bands = request.form['selected_bands']
        indices = request.form['selected_indices']
        masks = request.form['selected_masks']
        cloud_percentage = request.form['cloud_percentage']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        body = request.form['body']
        ds_type = request.form['ds_type']
        dimension = request.form['dimensions']
        num_tiles = request.form['num_sample_tiles']
        crs = request.form['crs']
        overlap = request.form['overlap']
        title = request.form['title']

        BASE_PATH = f"/data/{project_name}/{title}"
        project = db.session.query(Project).filter_by(project_name=project_name).first()
        existing_post = db.session.query(Dataset).filter_by(title=title, project_id=project.id).first()

        if existing_post is not None:
            flash(f"A dataset with the title '{title}' already exists.")
            return redirect(url_for('datasets.create', project_name=project_name))

        error = None
        # Validate required data
        if not bands:
            error = "At least one band must be selected."
        if not indices:
            error = "At least one index must be selected."
        if not cloud_percentage:
            error = "Cloud percentage is required."
        if not start_date or not end_date:
            error = "Start and end dates are required."
        
        if error is not None:
            flash(error)
        else:

            DATE = [start_date, end_date]
            selected_bands = bands
            num_images = 0
            time_init = time.time()
            if ds_type.upper() == 'TRAINING':
                selected_bands, num_images = generate_training_dataset(BASE_PATH, body, cloud_percentage, DATE, bands, indices, masks, dimension, num_tiles, crs, roi_path=bind_data_path, service_account=service_account)
            if ds_type.upper() == 'COUNTING':
                # selected_bands = generate_counting_dataset(BASE_PATH, body, cloud_percentage, DATE, bands, indices, masks, dimension, overlap, crs, roi_path=bind_data_path, service_account=service_account)
                pass
            time_end = time.time()
            media_time = (time_end - time_init)/max(num_images,1)
            print(f"Download Completed! All images have been exported to {BASE_PATH}")

            selected_bands = json.dumps(selected_bands)
            indices = json.dumps(json.loads(indices))
            masks = json.dumps(json.loads(masks))
            
            print(f"num images: {num_images}")
            # Insert the post into the database
            db.session.add(Dataset(
                title=title, 
                body=body, 
                bands=selected_bands, 
                indices=indices, 
                masks=masks, 
                ds_type=ds_type, 
                crs=crs,
                starting_date=start_date, 
                ending_date=end_date, 
                cloud_cover=cloud_percentage, 
                num_rois=num_rois, 
                num_tiles=num_tiles, 
                num_images = num_images, 
                dataset_author_id = session.get('user_id'), 
                dataset_creation_time_med = media_time,
                project_id=project.id))
            db.session.commit()
            return redirect(url_for('datasets.gif', project_name=project_name, title=title, _method='GET'))

    return render_template('datasets/create.html', project_name=project_name, data=data, num_rois=num_rois, ds_types=ds_types, dimensions=dimensions)

@datasets_bp.route('/projects/<string:project_name>/<string:title>/gif', methods=('GET', 'POST'))
@login_required
def gif(project_name, title):

    project = db.session.query(Project).filter_by(project_name=project_name).first()
    dataset = db.session.query(Dataset).filter_by(title=title, project_id=project.id).first().to_dict()

    # Retrieve data from the post
    bands = dataset['bands']
    indices = dataset['indices']
    user_choice = dataset['body']
    masks = dataset['masks']
    title = dataset['title']
    ds_type = dataset['ds_type']
    crs = dataset['crs']

    selected_bands = json.loads(bands)
    selected_indices = json.loads(indices)
    selected_masks = json.loads(masks)


    BASE_PATH = f"/data/{project_name}/{title}"
    S1_OUTPUT_DIRECTORY = BASE_PATH + '/Sentinel-1/'
    S2_ALL_PATH = f"{BASE_PATH}/Sentinel-2/"
    FUSED_PATH = f"{BASE_PATH}/Fused"
    GIF_OUTPUT_DIRECTORY = os.path.join(BASE_PATH, "Gifs/")

    if request.method == 'POST':
        gif_type = request.form['gif-type']
        band0_gif = request.form['gif-bands0']
        band1_gif = request.form['gif-bands1']
        band2_gif = request.form['gif-bands2']
        band3_gif = request.form['gif-bands3']
        # Check if the data is available
        if not bands or not indices:
            flash("The selected data is not available. Please make the selection again.")
            return redirect(url_for('datasets.create', project_name=project_name))
        
        if user_choice.upper() == 'FUSED':
            selected_bands = selected_bands[:13] + selected_indices + selected_bands[13:] + selected_masks
        
        gif_state = 'YES'
        while(gif_state.upper() == 'YES'):
            gif_state = request.form['generateGif']
            bands_gif = []
            if gif_state.upper() == 'YES':
                extended_bands = selected_bands
                if user_choice.upper() == 'SENTINEL-2':
                    extended_bands = selected_bands + selected_indices + selected_masks
                if gif_type.upper() == 'MONOCROMATIC':
                    bands_gif = [band0_gif]
                elif gif_type.upper() == 'CUSTOM':
                    bands_gif = [band1_gif, band2_gif, band3_gif]
                elif gif_type.upper() == 'RGB':
                    bands_gif = ['B4', 'B3', 'B2']
                print(bands_gif,gif_type.upper())
                index = 0
                if len(bands_gif) == 1:
                    print(f"Image Bands: {extended_bands}")
                    index = extended_bands.index(bands_gif[0])
                if (len(bands_gif) <= 3):
                    print(f"Generating gif")
                    if user_choice.upper() == 'SENTINEL-1':
                        generate_gif(S1_OUTPUT_DIRECTORY, ds_type,GIF_OUTPUT_DIRECTORY, ['VV', 'VH'], False, speed=1200, crs=crs)
                    if user_choice.upper() == 'SENTINEL-2':
                        generate_gif(S2_ALL_PATH, ds_type, GIF_OUTPUT_DIRECTORY, bands_gif, selected_bands[0] == 'B1', index, speed=1200, crs=crs)    
                    if user_choice.upper() == 'FUSED':
                        generate_gif(FUSED_PATH, ds_type, GIF_OUTPUT_DIRECTORY, bands_gif, True, index, speed=1200, crs=crs)
                    flash(f"{gif_type} Gif generated successfully for band {bands_gif}.")
                    return redirect(url_for('datasets.gif', project_name=project_name, title=title))
            else:
                return redirect(url_for('datasets.index', project_name=project_name))     

    # Pass the data to the template
    return render_template('datasets/gif.html', data=['Monocromatic', 'RGB', 'Custom'], selected_bands=selected_bands + selected_indices + selected_masks)

@datasets_bp.route('/projects/<string:project_name>/<string:title>/update', methods=('GET', 'POST'))
@login_required
def update(project_name, title):
    project = db.session.query(Project).filter_by(project_name=project_name).first()
    dataset = db.session.query(Dataset).filter_by(title=title, project_id=project.id).first()
    users = db.session.query(Project).all()
    users_dict = {user.id: user for user in users}

    if request.method == 'POST':
        new_title = request.form['title']
        error = None

        if not new_title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            dataset = db.session.query(Dataset).filter(Dataset.title==title).update({Dataset.title: new_title})
            db.session.commit()
            return redirect(url_for('datasets.index', project_name=project_name))

    return render_template('datasets/update.html', users_dict=users_dict, project_name=project_name, title=title, dataset=dataset, data=data)

@datasets_bp.route('/projects/<string:project_name>/<string:title>/delete', methods=('POST',))
@login_required
def delete(project_name, title):
    project = db.session.query(Project).filter_by(project_name=project_name).first()
    dataset = db.session.query(Dataset).filter_by(title=title, project_id=project.id).first()

    if dataset is None or dataset.project_id != project.id:
        flash("Dataset not found or you don't have permission to delete it.", "error")
        return redirect(url_for('datasets.index', project_name=project_name))
    
    db.session.delete(dataset)
    db.session.commit()

    flash("Dataset deleted successfully.", "success")
    return redirect(url_for('datasets.index', project_name=project_name))