from .. import db
from datetime import datetime
import sys
sys.path.append('../')
import plastic_sniffer.modules.utils as utils
from app.schemas import Classification
from app.schemas import Dataset

class Imagery(db.Model):
    __tablename__ = 'imagery'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gid_prefix = db.Column(db.String, nullable=True, unique=True)
    image_name = db.Column(db.String, nullable=False)
    subpoint_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String, nullable=False)
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'))
    satellite_id = db.Column(db.Integer, db.ForeignKey('satellite.id'))
    roi = db.Column(db.Integer, nullable=False)
    state = db.Column(db.Integer, nullable=False) # 0: not labelled, 1: being labelled, 2: labelled
    time_download = db.Column(db.Float, nullable=True)
    time_segmentation = db.Column(db.Float, nullable=True)
    time_classification = db.Column(db.Float, nullable=True)
    time_validation = db.Column(db.Float, nullable=True)
    labeler_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    classifications = db.relationship('Classification', backref='imagery', lazy=True)
    full_mask = db.Column(db.ARRAY(db.Integer), nullable=True)

    def __init__(self, dataset_id, satellite_id, subpoint_id, image_name, date):
        self.image_name = image_name
        self.dataset_id = dataset_id
        self.subpoint_id = subpoint_id
        self.date = date
        self.roi = image_name.split('_')[1]
        self.satellite_id = satellite_id
        self.time_download = Dataset.query.filter_by(id=dataset_id).first().dataset_creation_time_med
        self.time_segmentation = 0
        self.time_classification = 0
        self.time_validation = 0
        self.state = 0
        self.labeler_id = None
        self.full_mask = None

    @staticmethod
    def generate_gid_prefix():
        for image in Imagery.query.all():
            if image.gid_prefix == None:
                dig0 = utils.int_to_ascii(image.dataset_id)
                dig1 = utils.int_to_ascii(image.satellite_id)
                dig2 = utils.int_to_ascii(image.roi)
                dig34 = utils.int_to_b62(image.subpoint_id)

                dataset = Dataset.query.filter_by(id=image.dataset_id).first()
                base_date = datetime.strptime(dataset.starting_date, '%Y-%m-%d').date()
                image_date = datetime.strptime(image.date, '%Y%m%d').date()
                date_diff = image_date - base_date

                dig56 = utils.int_to_b62(date_diff.days//5)
                gid_prefix = f'{dig0}{dig1}{dig2}{dig34}{dig56}'
                if Imagery.query.filter_by(gid_prefix=gid_prefix).first():
                    continue
                image.gid_prefix = gid_prefix
        db.session.commit()
        return 0
    
    def check_state(self):
        objects_with_gid_prefix = Classification.query.filter_by(gid_prefix=self.gid_prefix).all()
        if all(object.state == 2 for object in objects_with_gid_prefix):
            self.state = 2
        elif all(object.state == 1 for object in objects_with_gid_prefix):
            self.state = 1
        else:
            self.state = 0
        db.session.commit()
        return self.state
    
    def set_labeler(self, user):
        self.labeler_id = user.id
        self.state = 1
        user.with_pack = True
        db.session.commit()
        return 0
    
    def time_validation_increase(self, time):
        self.time_validation += time
        db.session.commit()
        return 0
    
    def set_time_download(self, time):
        self.time_download = time
        db.session.commit()
        return 0
    
    def set_time_segmentation(self, time):
        self.time_segmentation = time
        db.session.commit()
        return 0
    
    def calc_time_classification(self):
        objects_with_gid_prefix = Classification.query.filter_by(gid_prefix=self.gid_prefix).all()
        self.time_classification = sum(object.time_classification for object in objects_with_gid_prefix)
        db.session.commit()
        return 0

    def __repr__(self):
        return f'<Imagery {self.image_name}>'
    