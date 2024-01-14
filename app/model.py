from app import db
from datetime import datetime
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), nullable=False)
    score = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
    date = db.Column(
        db.String, default=lambda: datetime.now().strftime("%m-%d-%Y"), nullable=False
    )


class HistoryQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question = db.Column(db.String(512), unique=True, nullable=False)
    option1 = db.Column(db.String, nullable=False)
    option2 = db.Column(db.String, nullable=False)
    option3 = db.Column(db.String, nullable=False)
    option4 = db.Column(db.String, nullable=False)
    answer = db.Column(db.String, nullable=False)
    team = db.Column(db.String, nullable=False)
    date = db.Column(
        db.String, default=lambda: datetime.now().strftime("%m-%d-%Y"), nullable=False
    )


class LiveQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question = db.Column(db.String(512), unique=True, nullable=False)
    option1 = db.Column(db.String, nullable=False)
    option2 = db.Column(db.String, nullable=False)
    option3 = db.Column(db.String, nullable=False)
    option4 = db.Column(db.String, nullable=False)
    answer = db.Column(db.String, nullable=False)
    team = db.Column(db.String, nullable=False)
    week = db.Column(db.Integer, nullable=False)
    date = db.Column(
        db.String, default=lambda: datetime.now().strftime("%m-%d-%Y"), nullable=False
    )


class Vague(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question = db.Column(db.String(512), nullable=False)
    answer = db.Column(db.String, nullable=False)
    team = db.Column(db.String, nullable=False)
    topic = db.Column(db.String, nullable=False)
    date = db.Column(
        db.String, default=lambda: datetime.now().strftime("%m-%d-%Y"), nullable=False
    )


class Duplicate(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question = db.Column(db.String(512), nullable=False)
    answer = db.Column(db.String, nullable=False)
    team = db.Column(db.String, nullable=False)
    topic = db.Column(db.String, nullable=False)
    date = db.Column(
        db.String, default=lambda: datetime.now().strftime("%m-%d-%Y"), nullable=False
    )


class Accuracy(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question = db.Column(db.String(512), nullable=False)
    answer = db.Column(db.String, nullable=False)
    team = db.Column(db.String, nullable=False)
    topic = db.Column(db.String, nullable=False)
    date = db.Column(
        db.String, default=lambda: datetime.now().strftime("%m-%d-%Y"), nullable=False
    )


class Roster(db.Model):
    jerseyNum = db.Column(db.Integer, primary_key=True)
    team = db.Column(db.String(8), primary_key=True)
    fullName = db.Column(db.String(64), nullable=False)
    abbrName = db.Column(db.String(32))
    position = db.Column(db.String(8))


class Play(db.Model):
    play_id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(
        db.String(128), db.ForeignKey("game.id"), primary_key=True, nullable=False
    )
    week_num = db.Column(db.Integer, nullable=False)
    quarter = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.String(5), nullable=False)
    description = db.Column(db.String(256), nullable=False)


class Game(db.Model):
    id = db.Column(db.String(128), primary_key=True)
    home_team = db.Column(db.String(8), nullable=False)
    away_team = db.Column(db.String(8), nullable=False)
    week_num = db.Column(db.Integer, nullable=False)
    plays = db.relationship("Play", backref="game", lazy=True)
