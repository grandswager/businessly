import os
from flask import Flask, session
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

from services.DatabaseService import db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# OAuth
oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@app.context_processor
def inject_globals():
    return dict(
        current_user=db.get_user_by_id(session["user_id"]) if "user_id" in session else None,
        current_path=request.path
    )

RECAPTCHA_SECRET = os.getenv("RECAPTCHA_SECRET_KEY")
RECAPTCHA_SITE = os.getenv("RECAPTCHA_SITE_KEY")

from routes import *
