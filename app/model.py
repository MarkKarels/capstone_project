from app import db
from datetime import datetime
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class Question(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    question = db.Column(db.String, unique=True, nullable=False)
    option1 = db.Column(db.String, nullable=False)
    option2 = db.Column(db.String, nullable=False)
    option3 = db.Column(db.String, nullable=False)
    option4 = db.Column(db.String, nullable=False)
    answer = db.Column(db.String, nullable=False)
    team = db.Column(db.String, nullable=False)
    date = db.Column(db.String, default=lambda: datetime.now().strftime('%m-%d-%Y'), nullable=False)
