from flask_login import UserMixin
from .database import db


# Create model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(50))
    password = db.Column(db.String(250))

    def to_dict(self):
        dict_ = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return dict_







def user_load_test_db():
    pass
