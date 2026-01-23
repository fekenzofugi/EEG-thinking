from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, session)
from ..auth.views import login_required
from ..schemas import Dataset, Project, User, Imagery
from .. import db
from plastic_sniffer.evolution import evolution
import sys
import ee
import os
sys.path.append('../')

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/projects')
def index():
    projects = db.session.query(Project).all()
    users = User.get_all_users()
    return render_template('projects/index.html', users=users, projects=projects)

@projects_bp.route('/projects/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        project_name = request.form['project_name']
        service_account = request.form['service_account']
        description = request.form['description']

        existing_project = db.session.query(Project).filter(Project.project_name == project_name).first()

        if existing_project is not None:
            flash(f"A project with the name '{project_name}' already exists.")
            return redirect(url_for('projects.create'))
        
        error = None
        # Validate required data
        if not description:
            error = 'Description is required.'
        
        if error is not None:
            flash(error)
        else:
            print(f"Creating project {project_name} with Google Cloud ID {service_account} and description {description}")
            try:
                credentials_dir = "credentials"
                json_files = [f for f in os.listdir(credentials_dir) if f.endswith('.json')]
                if not json_files:
                    raise FileNotFoundError("No JSON credentials file found in the credentials directory.")
                credentials_file = os.path.join(credentials_dir, json_files[0])
                credentials = ee.ServiceAccountCredentials(service_account, credentials_file)
                ee.Initialize(credentials)
            except ee.ee_exception.EEException as e:
                error = str(e) + ' Change project or reset EE credentials.'
                print(error)
            # Insert the post into the database
            db.session.add(Project(project_name=project_name, service_account=service_account, description=description, author_id=session.get('user_id')))
            db.session.commit()
            return redirect(url_for('projects.index'))

    return render_template('projects/create.html')

@projects_bp.route('/projects/<string:project_name>/labelers', methods=('GET', 'POST'))
@login_required
def labelers(project_name):
    project = db.session.query(Project).filter_by(project_name=project_name).first()
    users = User.query.all()
    if request.method == 'POST':
        labelers = request.form.getlist('labelers')
        labeler_users = []
        for user_id in labelers:
            user = db.session.query(User).filter_by(id=int(user_id)).first()
            labeler_users.append(user)
        project.set_labelers(labeler_users)
        print(f"Labelers: {project.labelers}")
        db.session.commit()
        return redirect(url_for('projects.labelers', project_name=project_name))

    return render_template('projects/labelers.html', project=project, users=users)

@projects_bp.route('/projects/<string:project_name>/stats', methods=['GET', 'POST'])
@login_required
def stats(project_name):
    project = db.session.query(Project).filter_by(project_name=project_name).first()
    project_owner = db.session.query(User).filter_by(id=project.author_id).first()
    if not project:
        flash("Project not found", "error")
        return redirect(url_for('projects.index'))  # Redirect if project doesn't exist

    labelers_with_owner = [project_owner] + project.labelers

    if not labelers_with_owner:
        # If there are no labelers, pass an empty structure to prevent errors
        labeler_stats = {"labels": [], "values": []}
    else:
        # Compute labeled images per labeler
        labeler_stats = {
            "labels": [labeler.username for labeler in labelers_with_owner],
            "values": [
            db.session.query(Imagery).filter_by(labeler_id=labeler.id, state=2).count()
            for labeler in labelers_with_owner
            ]
        }

    return render_template('projects/stats.html', project=project, labeler_stats=labeler_stats)



@projects_bp.route('/projects/<string:project_name>/settings', methods=('GET', 'POST'))
@login_required
def settings(project_name):
    project = db.session.query(Project).filter_by(project_name=project_name).first()
    datasets = db.session.query(Dataset).filter_by(project_id=project.id).all()

    if request.method == 'POST':
        new_project_name = request.form['project_name']
        new_service_account = request.form['service_account']
        new_description = request.form['description']
        
        project = db.session.query(Project).filter(Project.project_name==project_name).update({Project.project_name: new_project_name, Project.service_account: new_service_account, Project.description: new_description})
        db.session.commit()
        return redirect(url_for('projects.index'))

    return render_template('projects/settings.html', project=project, datasets=datasets)


@projects_bp.route('/projects/<string:project_name>/delete', methods=('POST',))
@login_required
def delete(project_name):
    project = db.session.query(Project).filter_by(project_name=project_name).first()
    if project is None:
        flash("Project not found.", "error")
        return redirect(url_for('projects.index'))

    
    datasets = db.session.query(Dataset).filter_by(project_id=project.id).all()

    for dataset in datasets:
        db.session.delete(dataset)

    db.session.delete(project)
    db.session.commit()

    flash("Project deleted successfully.", "success")
    return redirect(url_for('projects.index'))

@projects_bp.route('/projects/<string:project_name>/packs', methods=('GET', 'POST'))
@login_required
def get_packs(project_name):
    project = db.session.query(Project).filter_by(project_name=project_name).first()
    current_user = User.query.filter_by(id=session.get('user_id')).first()
    users = [current_user] + project.labelers

    if request.method == 'POST':
        pack_size = int(request.form['pack_size'])
        labelers = request.form.getlist('labelers')

        not_labelled_images = Imagery.query.filter_by(labeler_id=None, state=0).all()
        if not_labelled_images is None:
            flash("No images to pack.")
            return redirect(url_for('projects.get_packs', project_name=project_name))
        else:
            for i in range(len(labelers)):
                labeler = db.session.query(User).filter_by(id=int(labelers[i])).first()
                labeler_packs = Imagery.query.filter_by(labeler_id=labeler.id).all()
                if labeler.with_pack:
                    flash(f"Labeler {labeler.username} already has packs.")
                    return redirect(url_for('projects.get_packs', project_name=project_name))
                else:
                    for j in range(pack_size):
                        if j < len(not_labelled_images):
                            image = not_labelled_images[j]
                            image.set_labeler(labeler)
                        else:
                            break
            labeler_names = [db.session.query(User).filter_by(id=int(user_id)).first().username for user_id in labelers]
            flash(f"Packs of size {pack_size} images created for labelers: {', '.join(labeler_names)}")

    return render_template('projects/packs.html', project=project, users=users, current_user=current_user)

@projects_bp.route('/projects/<string:project_name>/evolve/', methods=('GET', 'POST'))
@login_required
def evolve(project_name):

    BASE_PATH = f"/data/{project_name}"
    if not os.path.exists(BASE_PATH):
        flash(f"The directory for {project_name} does not exist.")
        return redirect(url_for('datasets.index', project_name=project_name))
    if request.method == 'POST':
        res = request.form['evolve']
        if res == 'yes':
            evolution(BASE_PATH)
            flash(f"Re-classification completed for {project_name}.")
        return redirect(url_for('datasets.index', project_name=project_name))
    
    return render_template('projects/evolve.html')

from plastic_sniffer.modules.output import add_layer_to_tiff
@projects_bp.route('/projects/<string:project_name>/download/', methods=('GET', 'POST'))
@login_required
def download(project_name):
    try:
        output_path = f"/data/{project_name}/labeled_images"
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        project = db.session.query(Project).filter_by(project_name=project_name).first()
        datasets = db.session.query(Dataset).filter_by(project_id=project.id).all()
        for dataset in datasets:
            input_path = f"/data/{project_name}/{dataset.title}/input"
            labeled_images = Imagery.query.filter_by(dataset_id=dataset.id, state=2).all()
            if not labeled_images:
                flash("No labeled images found.")
                return redirect(url_for('datasets.index', project_name=project_name))
            for image in labeled_images:
                full_mask = image.full_mask
                add_layer_to_tiff(
                    f"{input_path}/{image.image_name}",
                    full_mask,
                    f"{output_path}/{dataset.id}_{image.image_name}"
                )
        flash("Labeled images downloaded.")   
        return redirect(url_for('datasets.index', project_name=project_name))  
    except Exception as e:
        flash(f"An error occurred: {str(e)}")
        return redirect(url_for('datasets.index', project_name=project_name))