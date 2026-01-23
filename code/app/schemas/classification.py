from .. import db
import pandas as pd
from geoalchemy2 import Geometry

class Classification(db.Model):
    __tablename__ = 'classifications'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gid = db.Column(db.String, nullable=False)
    gid_prefix = db.Column(db.String, db.ForeignKey('imagery.gid_prefix'), nullable=False)
    gid_suffix = db.Column(db.String, nullable=False)
    state = db.Column(db.Integer, nullable=False)
    area = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.String, nullable=False)
    field_class = db.Column(db.Integer, nullable=False)
    prev_class = db.Column(db.Integer, nullable=True)
    time_classification = db.Column(db.Float, nullable=True)
    pmli = db.Column(db.Float, nullable=False)
    ndvi = db.Column(db.Float, nullable=False)
    bsi = db.Column(db.Float, nullable=False)
    bspi = db.Column(db.Float, nullable=False)
    ndwi = db.Column(db.Float, nullable=False)
    ndmi = db.Column(db.Float, nullable=False)
    apgi = db.Column(db.Float, nullable=False)
    cloud = db.Column(db.Float, nullable=False)
    shadow = db.Column(db.Float, nullable=False)
    shape = db.Column(Geometry('POLYGON'), nullable=False)
    mask = db.Column(db.ARRAY(db.Boolean), nullable=False)

    def __init__(self, gid, gid_prefix, gid_suffix, pmli, ndvi, bsi, bspi, ndwi, ndmi, apgi, cloud, shadow, state, shape, mask, area, user_id, field_class):
        self.gid = gid
        self.gid_prefix = gid_prefix
        self.gid_suffix = gid_suffix
        self.pmli = pmli
        self.ndvi = ndvi
        self.bsi = bsi
        self.bspi = bspi
        self.ndwi = ndwi
        self.ndmi = ndmi
        self.apgi = apgi
        self.cloud = cloud
        self.shadow = shadow
        self.state = state
        self.shape = shape
        self.mask = mask
        self.area = area
        self.user_id = user_id
        self.field_class = field_class
        self.prev_class = None
        self.time_classification = 0

    @staticmethod
    def get_dataframe():
        query = db.session.query(Classification)
        df = pd.read_sql(query.statement, db.session.bind)
        return df
    
    def set_field_class(self, field_class):
        self.field_class = field_class
        db.session.commit()
        return 0
    
    def set_prev_class(self, prev_class):
        self.prev_class = prev_class
        self.field_class = prev_class
        db.session.commit()
        return 0
    
    def set_time_classification(self, time_classification):
        self.time_classification = time_classification
        db.session.commit()
        return 0