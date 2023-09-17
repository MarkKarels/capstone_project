# myapp/__init__.py
import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

import config

app = Flask(__name__)
os.environ["OPENAI_API_KEY"] = config.OPENAI_API_KEY
app.config.from_object('config')  # assuming your config file is named config.py
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from app import routes, model

if __name__ == '__main__':
    app.run()
