# myapp/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.config.from_object('config')  # assuming your config file is named config.py
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from app import routes, model

if __name__ == '__main__':
    app.run()
