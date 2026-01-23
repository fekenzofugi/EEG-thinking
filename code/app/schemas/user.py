from werkzeug.security import check_password_hash, generate_password_hash

from .. import db

# act as auxiliary table for user and project table
user_labeling = db.Table(
    'user_labeling',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'))
)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password = db.Column(db.String(256))
    with_pack = db.Column(db.Boolean, default=False)
    packs_count = db.Column(db.Integer, default=0)
    projects = db.relationship("Project", backref="user_id", lazy="dynamic")
    datasets_created = db.relationship("Dataset", backref="user_id", lazy="dynamic")
    labelings = db.relationship("Project", secondary=user_labeling, back_populates="labelers")
    images_labeling = db.relationship("Imagery", backref="dataset", lazy="dynamic")

    def __init__(self, username, email, password):
        self.set_username(username)
        self.set_email(email)
        self.set_password(password)
        self.with_pack = False
        self.packs_count = 0

    def set_username(self, username):
        self.username = username

    def get_username(self):
        return self.username

    def set_email(self, email):
        self.email = email

    def get_email(self):
        return self.email

    def set_password(self, password):
            self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    @staticmethod
    def get_all_users():
        users = User.query.all()
        return {user.id: user.username for user in users}

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'gee_project_id': self.gee_project_id,
            'projects': self.projects
        }

    def __repr__(self):
        return f'<User {self.username}>'