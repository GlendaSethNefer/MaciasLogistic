import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY','cambia_esta_clave')
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://root:@localhost/maciaslogistic"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
