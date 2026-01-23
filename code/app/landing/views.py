from flask import (
    Blueprint, render_template)
import sys
from flask import g, redirect, url_for, session
sys.path.append('../')

landing_bp = Blueprint('landing', __name__)

@landing_bp.route('/')
def index():
    if session.get('user_id') is not None:
        return redirect(url_for('projects.index'))
    return render_template('landing/index.html')