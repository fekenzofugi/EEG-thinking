from datetime import datetime
from .. import db

class Project(db.Model):
    __tablemame__ = 'project'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created = db.Column(db.TIMESTAMP, default=lambda: datetime.now(), nullable=False)
    project_name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    service_account = db.Column(db.Text, nullable=False)
    datasets = db.relationship('Dataset', backref='project', lazy=True)
    labelers = db.relationship('User', secondary='user_labeling', back_populates='labelings')

    def __init__(self, project_name, service_account, description, author_id=None):
        self.project_name = project_name
        self.service_account = service_account
        self.description = description
        self.author_id = author_id

    def get_all_datasets(self):
        return self.datasets
    
    def set_labelers(self, users):
        self.labelers = users
    
    def remove_labeler(self, user):
        if user in self.labelers:
            self.labelers.remove(user)

    def __repr__(self):
        return f'<Project {self.project_name}>'