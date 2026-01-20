import requests
import uuid
from datetime import datetime, timezone
from flask import redirect, url_for, session, request, render_template, flash
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
        flash("ReCAPTCHA verification failed. Please try again.", "danger")
        return redirect(url_for("login"))

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

    google_id = user_info["sub"]

    user = db.get_user_by_google_id(google_id)

    if not user:
        session["new_user"] = {
            "auth": {
                "google": google_id
            },
            "email": user_info.get("email"),
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
        data = session["new_user"]

        account_type = request.form.get("type")
        categories = request.form.getlist("categories") or []

        VALID_CATEGORIES = {"Food", "Service", "Shop", "Health"}

        user_uuid = str(uuid.uuid4())

        if account_type not in ("standard", "business"):
            return render_template("signup_redirect.html", error="Please select a valid account type.")
        
        if account_type == "standard":
            if len(categories) > 4:
                return render_template("signup_redirect.html", error="You can select up to 4 categories only." )

            if not all(cat in VALID_CATEGORIES for cat in categories):
                return render_template("signup_redirect.html", error="Invalid category selection.")
            
            user_name = data["name"]
        else:
            categories = []

            user_name = request.form.get("business_name")

            business = {
                "uuid": user_uuid,
                "name": request.form.get("business_name"),
                "category": request.form.get("business_category"),
                "address": request.form.get("address"),
                "city": request.form.get("city"),
                "province": request.form.get("province"),
                "country": "Canada",
                "postal_code": request.form.get("postal_code").replace(" ", "").upper()[:6],
                "description": request.form.get("description"),
                "phone": request.form.get("phone"),
                "socials": {
                    "instagram": request.form.get("instagram") or None,
                    "website": request.form.get("website") or None
                },
                "rating": 0,
                "bookmarks": 0,
                "comments": [],
                "coupons": {}
            }

            required_fields = [business["name"], business["address"], business["city"], business["province"], business["postal_code"], business["description"], business["phone"]]

            if not all(required_fields):
                return render_template("signup_redirect.html", error="Please complete all required business fields.")

        user = {
            "uuid": user_uuid,
            "auth": data["auth"],
            "email": data["email"],
            "name": user_name,
            "picture": data["picture"],
            "type": account_type,
            "categories": categories,
            "bookmarks": [],
            "created_at": datetime.now(timezone.utc)
        }

        result = db.create_user(user)

        if account_type == "business":
            db.create_business_profile(business)

        session.pop("new_user")
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
