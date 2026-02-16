import math
import requests
import uuid
from datetime import datetime, timezone
from flask import abort, redirect, url_for, session, request, render_template, flash, jsonify
from app import app, RECAPTCHA_SITE, RECAPTCHA_SECRET, google
from auth_utils import get_current_user, require_business_user
from services.DatabaseService import db
from services.GeocodingService import GeocodingService
from services.ImageStorageService import ImageStorageService
from services.RecommendationService import RecommendationService

ISS = ImageStorageService()

@app.route("/")
def index():
    user = get_current_user()
    user_lat = session.get("user_lat")
    user_lng = session.get("user_lng")
    user_location = session.get("user_location") or "Cornell, Markham"

    page = request.args.get("page", default=1, type=int)
    per_page = 12
    offset = (page - 1) * per_page

    query = request.args.get("query") or None
    category = request.args.get("category") or None
    max_distance = request.args.get("distance", type=int) or 10
    min_rating = request.args.get("rating", type=int) or 0

    if not user_lat or not user_lng:
        user_lat, user_lng = 43.892958, -79.228599

    if category and category != "none" and category != "all":
        categories = [category]
    elif category and category == "all":
        categories = []
    elif user and user["categories"]:
        categories = user["categories"]
    else:
        categories = []

    if max_distance >= 20:
        max_distance = 20020

    businesses, total = RecommendationService.recommend(user_lat=user_lat, user_lng=user_lng, user_query=query, max_distance_km=max_distance, min_rating=min_rating, categories=categories, limit=per_page, offset=offset)

    total_pages = math.ceil(total / per_page)

    if user:
        bookmarked_businesses = [
            db.get_business_info(b) for b in user["bookmarks"]
        ]
    else:
        bookmarked_businesses = None

    if user:
        recent_businesses = [
            db.get_business_info(b) for b in user["recently_viewed"]
        ]
    else:
        recent_businesses = None

    return render_template("index.html", businesses=businesses, address=user_location, bookmarks=bookmarked_businesses, recently_viewed=recent_businesses, page=page, total_pages=total_pages)

@app.route("/businesses/<string:business_uuid>")
def businesses(business_uuid):
    business = db.get_business_info(business_uuid)
    user = get_current_user()

    if user:
        db.add_recent_business(user["uuid"], business_uuid)

    page = request.args.get("page", 1, type=int)
    per_page = 10
    sort = request.args.get("sort", "newest")

    processed_comments = []
    total_pages = 0

    if business and business.get("comments"):
        comments = list(business["comments"].items())

        total_pages = math.ceil(len(comments) / per_page)

        if sort == "most_helpful":
            comments.sort(key=lambda x: (-x[1]["likes"], -x[1]["created"].timestamp()))
        else:
            comments.sort(key=lambda x: x[1]["created"], reverse=True)

        start = (page - 1) * per_page
        end = start + per_page

        for comment_uuid, comment in comments[start:end]:
            author = db.get_user_by_uuid(comment["author_uuid"])
            if not author:
                continue

            processed_comments.append({
                "uuid": comment_uuid,
                "author_name": author["name"],
                "author_picture": author["picture"],
                "comment": comment["comment"],
                "likes": int(comment["likes"]),
                "liked": user and user["uuid"] in comment.get("liked_by", []),
                "created": comment["created"]
            })

    now = datetime.now(timezone.utc)
    active_coupons = {}

    for key, coupon in business["coupons"].items():
        expiry = coupon["expiry"]

        expiry_ts = (expiry.replace(tzinfo=timezone.utc).timestamp() if expiry.tzinfo is None else expiry.timestamp())

        now_ts = now.timestamp()

        if expiry_ts >= now_ts:
            active_coupons[key] = coupon

    business["coupons"] = active_coupons

    return render_template("businesses.html", business=business, now=datetime.now(timezone.utc), uuid=business_uuid, comments=processed_comments, current_user=user, page=page, total_pages=total_pages)

@app.route("/businesses/<string:business_uuid>/bookmark", methods=["POST"])
def businesses_bookmark(business_uuid):
    business = db.get_business_info(business_uuid)
    user = get_current_user()

    if not business or not user or user["type"] != "standard":
        abort(400)

    result = db.bookmark_business(user["uuid"], business_uuid)

    if not result:
        abort(400)

    return {
        "success": True,
        "data": result
    }, 200

@app.route("/businesses/<string:business_uuid>/rate", methods=["POST"])
def businesses_rate(business_uuid):
    business = db.get_business_info(business_uuid)
    user = get_current_user()

    if not business or not user or user["type"] != "standard":
        abort(403)

    if not request.form.get("rating").isdigit():
        abort(400)

    rating = int(request.form.get("rating"))

    if rating > 5 or rating < 1:
        abort(400)

    result = db.rate_business(user["uuid"], business_uuid, rating)

    if not result:
        abort(400)

    flash(f"Successfully rated {business['name']} {rating} stars!", "success")
    return redirect(f"/businesses/{business_uuid}")

@app.route("/businesses/<string:business_uuid>/comments", methods=["POST"])
def post_comment(business_uuid):
    user = get_current_user()
    business = db.get_business_info(business_uuid)

    if not user or user["type"] != "standard" or not business:
        abort(400)

    data = request.get_json()
    text = (data.get("comment") or "").strip()

    if not text or len(text) > 1000:
        abort(400)

    result = db.add_business_comment(business_uuid, user["uuid"], text)

    if result == "RATE_LIMIT":
        return jsonify({"error": "You're commenting too fast."}), 429

    if result == "DUPLICATE":
        return jsonify({"error": "Duplicate comment detected."}), 400

    if not result:
        abort(400)

    return {"success": True}, 201

@app.route("/businesses/<string:business_uuid>/comments/<string:comment_uuid>/like", methods=["POST"])
def like_comment(business_uuid, comment_uuid):
    user = get_current_user()

    if not user or user["type"] != "standard":
        abort(400)

    result = db.toggle_comment_like(business_uuid, comment_uuid, user["uuid"])

    if not result:
        abort(400)

    return {"success": True, "data": result}, 200

@app.route("/login")
def login():
    if get_current_user():
        return redirect("/")
    
    return render_template("login.html", recaptcha_site_key=RECAPTCHA_SITE)

@app.route("/set_location", methods=["POST"])
def set_location():
    try:
        lat, lng = GeocodingService.geocode(
            address = request.form.get("address"),
            city = request.form.get("city"),
            province = request.form.get("province")
        )
    except Exception:
        flash("Address not found. Please check the address.", "danger")
        return redirect("/")
    
    formatted_address = request.form.get("address").title() + ", " + request.form.get("city").title()

    session["user_lat"] = lat
    session["user_lng"] = lng
    session["user_location"] = formatted_address

    return redirect("/")

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

            try:
                lat, lng = GeocodingService.geocode(
                    address = request.form.get("address"),
                    city = request.form.get("city"),
                    province = request.form.get("province")
                )
            except Exception:
                return render_template("signup_redirect.html", error="We couldn't locate your address. Please check and try again.")

            business = {
                "uuid": user_uuid,
                "name": request.form.get("business_name"),
                "category": request.form.get("business_category"),
                "address": request.form.get("address"),
                "city": request.form.get("city"),
                "province": request.form.get("province"),
                "country": "Canada",
                "postal_code": request.form.get("postal_code").replace(" ", "").upper()[:6],
                "location": {
                    "type": "Point",
                    "coordinates": [lng, lat]
                },
                "description": request.form.get("description"),
                "phone": request.form.get("phone"),
                "socials": {
                    "instagram": request.form.get("instagram") or None,
                    "website": request.form.get("website") or None
                },
                "image_url": "https://core.myblueprint.ca/Client/Images/EmptyState/icon_desertEmpty.svg",
                "combined_rating": 0,
                "users_rated": 0,
                "bookmarks": 0,
                "comments": {},
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
            "rated": {},
            "recently_viewed": [],
            "created_at": datetime.now(timezone.utc)
        }

        result = db.create_user(user)

        if account_type == "business":
            db.create_business_profile(business)

        session.pop("new_user")
        session["user_id"] = str(result.inserted_id)

        if account_type == "business": return redirect(url_for("dashboard"))

        return redirect("/")

    return render_template("signup_redirect.html")

@app.route("/dashboard")
def dashboard():
    if not get_current_user():
        return redirect("/login")

    user = db.get_user_by_id(session["user_id"])

    if user["type"] == "standard":
        return render_template("dashboard.html", user=user)
    elif user["type"] == "business":
        business_profile = db.get_business_info(user["uuid"])
        return render_template("dashboard.html", user=user, business=business_profile, now=datetime.now())
    else:
        flash("Something went wrong.", "danger")
        return render_template("dashboard.html", user=user)

@app.route("/profile/avatar", methods=["POST"])
def upload_avatar():
    user = get_current_user()
    if not user:
        return redirect("/login")

    file = request.files.get("avatar")
    if not file:
        flash("No file uploaded.", "danger")
        return redirect("/dashboard")

    try:
        file_bytes = file.read()
        new_url = ISS.upload_profile_picture(user["uuid"], file_bytes)

        db.update_user_picture(user["uuid"], new_url)

        flash("Successfully updated profile picture!", "success")
        return redirect("/dashboard")

    except ValueError as e:
        flash(str(e), "danger")
        return redirect("/dashboard")

    except Exception:
        flash("Something went wrong uploading your image.", "danger")
        return redirect("/dashboard")

@app.route("/profile/business/image", methods=["POST"])
def upload_business_image():
    user = get_current_user()
    if not user:
        return redirect("/login")

    if user["type"] != "business":
        flash("Unauthorized request.", "danger")
        return redirect("/dashboard")

    business = db.get_business_info(user["uuid"])
    if not business:
        flash("Business profile not found.", "danger")
        return redirect("/dashboard")

    if business.get("uuid") != user.get("uuid"):
        flash("Unauthorized action detected.", "danger")
        return redirect("/dashboard")

    file = request.files.get("image")
    if not file:
        flash("No file uploaded.", "danger")
        return redirect("/dashboard")

    try:
        file_bytes = file.read()

        new_url = ISS.upload_business_picture(user["uuid"], file_bytes)

        print(new_url)

        db.update_business_image(user["uuid"], new_url)

        flash("Successfully updated business thumbnail!", "success")
        return redirect("/dashboard")

    except ValueError as e:
        flash(str(e), "danger")
        return redirect("/dashboard")

    except Exception:
        flash("Something went wrong uploading your business thumbnail.", "danger")
        return redirect("/dashboard")

@app.route("/dashboard/standard", methods=["POST"])
def modify_standard():
    user = get_current_user()
    if not user:
        return redirect("/login")
    
    if user["type"] != "standard":
        flash("Invalid account type. (Error: 401)", "danger")
    
    name = request.form.get("name")
    categories = request.form.getlist("categories") or []

    VALID_CATEGORIES = {"Food", "Service", "Shop", "Health"}

    if not all(cat in VALID_CATEGORIES for cat in categories):
        flash("Invalid category selection.", "danger")
        return redirect("/dashboard")
    
    try:
        db.update_standard_profile(user["uuid"], name, categories)

        flash("Successfully updated profile!", "success")
        return redirect("/dashboard")

    except ValueError as e:
        flash(str(e), "danger")
        return redirect("/dashboard")

    except Exception:
        flash("Something went wrong updating your profile.", "danger")
        return redirect("/dashboard")

@app.route("/dashboard/business", methods=["POST"])
def modify_business():
    user = get_current_user()
    if not user:
        return redirect("/login")
    
    business = db.get_business_info(user["uuid"])
    if not business:
        flash("Business profile not found.", "danger")
        return redirect("/dashboard")

    if user["type"] != "business":
        flash("Invalid account type. (Error: 401)", "danger")
        return redirect("/dashboard")
    
    if business.get("uuid") != user.get("uuid"):
        flash("Unauthorized action detected.", "danger")
        return redirect("/dashboard")

    # -------- Get Form Data --------
    name = (request.form.get("name") or "").strip()
    description = (request.form.get("description") or "").strip()
    category = (request.form.get("category") or "").strip()

    address = (request.form.get("address") or "").strip()
    city = (request.form.get("city") or "").strip()
    province = (request.form.get("province") or "").strip()
    postal_code = (request.form.get("postal_code") or "").replace(" ", "").upper().strip()

    phone = (request.form.get("phone") or "").strip()
    instagram = (request.form.get("instagram") or "").strip() or None
    website = (request.form.get("website") or "").strip() or None

    VALID_CATEGORIES = {"Food", "Service", "Shop", "Health"}

    # -------- Validate Required Fields --------
    required_fields = [name, description, category, address, city, province, postal_code, phone]
    if not all(required_fields):
        flash("Please complete all required business fields.", "danger")
        return redirect("/dashboard")

    # -------- Validate Category --------
    if category not in VALID_CATEGORIES:
        flash("Invalid category selection.", "danger")
        return redirect("/dashboard")

    # -------- Validate Postal Code --------
    if len(postal_code) != 6:
        flash("Postal code must be 6 characters.", "danger")
        return redirect("/dashboard")

    # -------- Geocode if Address Changed --------
    try:
        address_changed = (
            address != business.get("address") or
            city != business.get("city") or
            province != business.get("province")
        )

        if address_changed:
            lat, lng = GeocodingService.geocode(
                address=address,
                city=city,
                province=province
            )
        else:
            lng, lat = business["location"]["coordinates"]

    except Exception:
        flash("We couldn't locate your address. Please check and try again.", "danger")
        return redirect("/dashboard")

    # -------- Build Updated Business Object --------
    updated_business = {
        "name": name,
        "category": category,
        "address": address,
        "city": city,
        "province": province,
        "postal_code": postal_code[:6],
        "description": description,
        "phone": phone,
        "socials": {
            "instagram": instagram,
            "website": website
        },
        "location": {
            "type": "Point",
            "coordinates": [lng, lat]
        }
    }

    try:
        db.update_business_profile(user["uuid"], updated_business)

        flash("Successfully updated business profile!", "success")
        return redirect("/dashboard")

    except ValueError as e:
        flash(str(e), "danger")
        return redirect("/dashboard")

    except Exception:
        flash("Something went wrong updating your business profile.", "danger")
        return redirect("/dashboard")

@app.route("/dashboard/business/coupons/create", methods=["POST"])
def create_coupon():
    user = get_current_user()
    if not user:
        return redirect("/login")

    if user["type"] != "business":
        flash("Unauthorized request.", "danger")
        return redirect("/dashboard")

    business = db.get_business_info(user["uuid"])
    if not business:
        flash("Business profile not found.", "danger")
        return redirect("/dashboard")

    if business.get("uuid") != user.get("uuid"):
        flash("Unauthorized action detected.", "danger")
        return redirect("/dashboard")

    name = (request.form.get("name") or "").strip()
    code = (request.form.get("code") or "").strip().upper()
    description = (request.form.get("description") or "").strip()
    discount_percent = request.form.get("discount")
    expiry_date = request.form.get("expiry")

    if not all([name, code, description, discount_percent, expiry_date]):
        flash("Please fill in all required coupon fields.", "danger")
        return redirect("/dashboard")

    if not discount_percent.isdigit():
        flash("Discount must be a number.", "danger")
        return redirect("/dashboard")

    discount_percent = int(discount_percent)

    if discount_percent < 1 or discount_percent > 100:
        flash("Discount must be between 1 and 100.", "danger")
        return redirect("/dashboard")

    discount = discount_percent / 100

    try:
        expiry_dt = datetime.strptime(expiry_date, "%Y-%m-%d")
        expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
    except Exception:
        flash("Invalid expiry date format.", "danger")
        return redirect("/dashboard")

    if expiry_dt < datetime.now(timezone.utc):
        flash("Expiry date cannot be in the past.", "danger")
        return redirect("/dashboard")

    coupon = {
        "name": name,
        "code": code,
        "description": description,
        "discount": discount,
        "expiry": expiry_dt
    }

    result = db.create_coupon(user["uuid"], coupon)

    if not result:
        flash("Failed to create coupon.", "danger")
        return redirect("/dashboard")

    flash("Coupon created successfully!", "success")
    return redirect("/dashboard")

@app.route("/dashboard/business/coupons/delete", methods=["POST"])
def delete_coupon():
    user = get_current_user()
    if not user:
        return redirect("/login")

    if user["type"] != "business":
        flash("Unauthorized request.", "danger")
        return redirect("/dashboard")

    business = db.get_business_info(user["uuid"])
    if not business:
        flash("Business profile not found.", "danger")
        return redirect("/dashboard")

    if business.get("uuid") != user.get("uuid"):
        flash("Unauthorized action detected.", "danger")
        return redirect("/dashboard")

    coupon_id = request.form.get("coupon_id")
    if not coupon_id:
        flash("Invalid coupon selected.", "danger")
        return redirect("/dashboard")

    result = db.delete_coupon(user["uuid"], coupon_id)

    if not result:
        flash("Failed to delete coupon.", "danger")
        return redirect("/dashboard")

    flash("Coupon deleted successfully.", "success")
    return redirect("/dashboard")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
