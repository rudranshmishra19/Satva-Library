from flask import Flask
from app.config import Config
from app.models import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize database
    db.init_app(app)

   
    from app.routes.main import main_bp
    from app.routes.booking import booking_bp
    from app.routes.auth import auth_bp
    from app.routes.misc import misc_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(misc_bp)

    # Create tables inside app context 
    with app.app_context():
        db.create_all()

    return app
