import requests
from flask import redirect, url_for, session, request, render_template
from app import app, RECAPTCHA_SITE, RECAPTCHA_SECRET, google
from db import db
from auth_utils import get_current_user, require_business_user

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    if get_current_user():
        return redirect("/")
    
    return render_template("login.html", recaptcha_site_key=RECAPTCHA_SITE)

@app.route("/login/google", methods=["POST"])
def google_login():
    recaptcha_response = request.form.get("g-recaptcha-response")

    r = requests.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data={
            "secret": RECAPTCHA_SECRET,
            "response": recaptcha_response,
        },
    ).json()

    if not r.get("success"):
        return "reCAPTCHA failed", 400

    redirect_uri = url_for("google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/auth/callback")
def google_callback():
    token = google.authorize_access_token()

    if not token:
        return "Failed to authorize", 400

    user_info = google.get(
        "https://openidconnect.googleapis.com/v1/userinfo"
    ).json()

    email = user_info["email"]
    user = db.get_user_by_email(email)

    if not user:
        session["new_user"] = {
            "email": email,
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
        }
        return redirect("/signup_redirect")

    session["user_id"] = str(user["_id"])
    return redirect("/")

@app.route("/signup_redirect", methods=["GET", "POST"])
def signup_redirect():
    if "new_user" not in session:
        return redirect("/")

    if request.method == "POST":
        type = request.form.get("type")
        data = session.pop("new_user")

        if type != "standard" and type != "business":
            return render_template("signup_redirect.html", error="An unexpected error occured.")

        user = {
            "email": data["email"],
            "name": data["name"],
            "picture": data["picture"],
            "type": type,
        }

        result = db.create_user(user)
        session["user_id"] = str(result.inserted_id)

        return redirect("/")

    return render_template("signup_redirect.html")

@app.route("/dashboard")
def dashboard():
    if not get_current_user():
        return redirect("/login")

    user = db.get_user_by_id(session["user_id"])
    return render_template("dashboard.html", user=user)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
