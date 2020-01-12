from config import db, session
from passlib.hash import pbkdf2_sha256 as sha256
from sqlalchemy import ForeignKey

class UserModel(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(120), unique = True, nullable = False)
    password = db.Column(db.String(120), nullable = False)
    normalPosture = db.Column(db.JSON, default={'eye_distance': '0', 'head_slope': '0',
                                                'left_shoulder_neck': '0', 'right_shoulder_neck': '0',
                                                'shoulder_width': '0', 'shoulder_slope': '0'})
    
    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_username(cls, username):
        return cls.query.filter_by(username = username).first()

    @classmethod
    def find_posture_data(cls, username):
        return session.query(
                        UserModel, PostureModel
                ).filter(
                        UserModel.id == PostureModel.uid
                ).filter(
                        UserModel.username == username
                ).all()

    @staticmethod
    def generate_hash(password):
        return sha256.hash(password)
    
    @staticmethod
    def verify_hash(password, hash):
        return sha256.verify(password, hash)


class PostureModel(db.Model):
    __tablename__ = 'postures'
    
    id = db.Column(db.Integer, primary_key = True)
    uid = db.Column(db.Integer, ForeignKey('users.id'))
    postureData = db.Column(db.JSON, default={'Normal': '0', 'FHP': '0', 'Scoliosis': '0', 'Slouch': '0'})
    created = db.Column(db.DateTime, server_default=db.func.now())

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

