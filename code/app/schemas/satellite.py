from .. import db

class Satellite(db.Model):
    __tablename__ = 'satellite'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    satellite_tile = db.Column(db.Text, nullable=False)
    imageries = db.relationship('Imagery', backref='satellite', lazy=True)

    def __init__(self, satellite_tile):
        self.satellite_tile = satellite_tile
    
    def __repr__(self):
        return f'<Satellite {self.satellite_tile}>'