from datetime import datetime

from .. import db

class Dataset(db.Model):
    __tablename__ = 'dataset'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    created = db.Column(db.TIMESTAMP, default=lambda: datetime.now(), nullable=False)
    title = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=False)
    bands = db.Column(db.Text, nullable=False)
    indices = db.Column(db.Text)
    masks = db.Column(db.Text)
    ds_type = db.Column(db.Text, nullable=False)
    crs = db.Column(db.Text, nullable=False)
    starting_date = db.Column(db.Text, nullable=False)
    ending_date = db.Column(db.Text, nullable=False)
    cloud_cover = db.Column(db.Integer, nullable=False)
    num_rois = db.Column(db.Integer, nullable=False)
    num_tiles = db.Column(db.Integer, nullable=False)
    num_images = db.Column(db.Integer, nullable=False)
    dataset_creation_time_med = db.Column(db.Float, nullable=True)
    dataset_author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    imageries = db.relationship('Imagery', backref='dataset_created_id', lazy="dynamic")
    
    def __init__(self, title, body, bands, indices, masks, ds_type, crs, starting_date, ending_date, cloud_cover, num_rois, num_tiles, num_images, dataset_author_id=None, project_id=None, dataset_creation_time_med = 0):
        self.title = title
        self.body = body
        self.bands = bands
        self.indices = indices
        self.masks = masks
        self.ds_type = ds_type
        self.crs = crs
        self.starting_date = starting_date
        self.ending_date = ending_date
        self.cloud_cover = cloud_cover
        self.num_rois = num_rois
        self.num_tiles = num_tiles
        self.num_images = num_images
        self.dataset_author_id = dataset_author_id
        self.project_id = project_id
        self.dataset_creation_time_med = dataset_creation_time_med

    def __repr__(self):
        return f'<Dataset {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'created': self.created,
            'title': self.title,
            'body': self.body,
            'bands': self.bands,
            'indices': self.indices,
            'masks': self.masks,
            'ds_type': self.ds_type,
            'crs': self.crs,
            'starting_date': self.starting_date,
            'ending_date': self.ending_date,
            'cloud_cover': self.cloud_cover,
            'project_id': self.project_id,
            'dataset_author_id': self.dataset_author_id
        }    
    
    def get_all_imageries(self):
        return self.imageries
    
    def att_classifications_time(self):
        """
        This function updates the time of all classifications in the dataset.
        """
        for imagery in self.imageries:
            imagery.calc_time_classification()   
        db.session.commit()
        return 0