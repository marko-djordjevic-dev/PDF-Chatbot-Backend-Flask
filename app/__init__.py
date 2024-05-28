from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_cors import CORS
# from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()

def create_app(config=Config):
    app = Flask(__name__)
    app.config.from_object(config)
    CORS(app, supports_credentials=True, origins='*')
    
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)

    # app.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    app.embeddings = OpenAIEmbeddings(
        openai_api_key = Config.OPENAI_KEY, 
        model = 'text-embedding-3-large'
    )
    
    from .routes import bp as routes_bp
    app.register_blueprint(routes_bp, url_prefix='/api')

    return app  