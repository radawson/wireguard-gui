from flask_login import UserMixin
from .database import db
from flask_marshmallow import Marshmallow
from marshmallow import fields

ma = Marshmallow()


# Create model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(50))
    password = db.Column(db.String(250))

    def to_dict(self):
        dict_ = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return dict_


# JSON Schema
class UserSchema(ma.Schema):
    id = fields.Int()
    username = fields.Str(allow_none=True)
    email = fields.Str(allow_none=True)
    password = fields.Str(allow_none=True)


user_schema = UserSchema()
users_schema = UserSchema(many=True)




def user_load_test_db():
    pass
