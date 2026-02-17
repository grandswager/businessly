# Businessly

**Businessly** is a Flask-based web application that helps users discover and interact with local businesses through location-based recommendations, filtering, ratings, comments, bookmarks, and business profile management.

It supports two account types:

- **Standard users** (browse, rate, comment, bookmark businesses)
- **Business users** (manage a business profile, upload business image, create presence)

Some sample business images used in the project are sourced from **Adobe Stock** (for demonstration purposes).

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Environment Variables (.env)](#environment-variables-env)
- [Running the App](#running-the-app)
- [Features](#features)
- [Modules / Dependencies](#modules--dependencies)
- [Frontend Assets](#frontend-assets)
- [Services Overview](#services-overview)
- [Security Notes](#security-notes)
- [Demo](#demo)
- [Credits](#credits)

---

## Tech Stack

### Backend
- **Python**
- **Flask**
- **MongoDB (PyMongo)**
- **Authlib (Google OAuth login)**
- **Cloudinary (image storage)**

### Frontend
- **HTML (Jinja2 templates)**
- **CSS**
- **JavaScript**

### External APIs
- **Google OAuth**
- **Google reCAPTCHA**
- **OpenStreetMap Nominatim API** (geocoding)
- **Cloudinary API** (image upload + CDN hosting)

See [Modules / Dependencies](#modules--dependencies) for more information.

---

## Project Structure
```
businessly-main/
│── app.py
│── routes.py
│── auth_utils.py
│── requirements.txt
│
├── services/
│ ├── DatabaseService.py
│ ├── GeocodingService.py
│ ├── ImageStorageService.py
│ ├── RecommendationService.py
│
├── helpers/
│ └── business_insert.py
│
├── static/
│ ├── logo.png
│ └── css/
│ ├── businesses.css
│ ├── dashboard.css
│ ├── header.css
│ ├── index.css
│ ├── login.css
│ ├── signup_redirect.css
│ └── styles.css
│
└── templates/
├── index.html
├── businesses.html
├── businesses_comments.html
├── dashboard.html
├── login.html
├── signup_redirect.html
└── navbar.html
```

---

## Installation
Install all dependencies using:
```bash
pip install -r requirements.txt
```

---

## Environment Variables (.env)
Create a .env file in the root directory.
Example:
```
# Flask
FLASK_SECRET_KEY=your_flask_secret_key

# MongoDB
MONGO_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Google reCAPTCHA
RECAPTCHA_SITE_KEY=your_recaptcha_site_key
RECAPTCHA_SECRET_KEY=your_recaptcha_secret_key

# Cloudinary
CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
```

---

## Running the App
Run the Flask development server:
```bash
flask run --host=0.0.0.0
```
The app will be accessible on your local network.

---

## Features
### General User Features
* Browse businesses with pagination
* Location-based business search
* Business recommendations based on distance + popularity + rating
* Search by business name/description
* Filter by category
* Filter by rating
* Filter by maximum distance
* View business details page
* View business coupons (active only)
* Bookmark businesses
* Recently viewed business history
* Rate businesses (1–5 stars)
* Post comments on businesses
* Like/unlike comments
* Sort comments by:
    * newest
    * most helpful (likes)

### Authentication Features
* Login via Google OAuth
* Session-based login system
* Signup redirect flow after OAuth for new users
* Account type seledction during signup:
    * Standard
    * Business

### Standard User Profile Features
* Update profile picture
* Select preferred categories

### Business User Features
* Create a business profile during signup
* Update business profile details:
    * name
    * category
    * address
    * postal code
    * phone
    * description
    * socials (instagram, website)
* Upload / update business thumbnail image

### Image Upload Features
* Upload user avatar image
* Upload business thumbnail image
* Validation:
    * max 5MB
    * only JPEG/PNG allowed
* Uploaded images stored via Cloudinary CDN

### Data Integrity / Moderation
* Profanity filtering (better-profanity)
* Comment spam prevention:
    * rate limiting
    * duplicate detection

---

## Modules / Dependencies
All backend dependencies are defined in requirements.txt.

### Python Packages Used
| Package            | Purpose                                            |
| ------------------ | -------------------------------------------------- |
| `flask`            | Web framework                                      |
| `flask-pymongo`    | MongoDB support                                    |
| `pymongo`          | MongoDB driver (used directly)                     |
| `authlib`          | Google OAuth authentication                        |
| `python-dotenv`    | Loads environment variables                        |
| `requests`         | API requests (geocoding + recaptcha)               |
| `uuid`             | Generates unique IDs for users/businesses/comments |
| `better-profanity` | Filters profanity in user content                  |
| `cloudinary`       | Upload and host images                             |
| `pillow`           | Image validation (format checking)                 |

### Frontend Dependencies
These dependencies are used in the HTML/CSS/JS frontend (typically loaded through `<link>` / `<script>` tags):

| Library                 | Purpose                                           |
| ----------------------- | ------------------------------------------------- |
| **Google Fonts**        | Custom typography across the UI                   |
| **Font Awesome**        | Icons (stars, UI buttons, navigation icons, etc.) |
| **Leaflet.js**          | Interactive maps (displaying business locations)  |
| **OpenStreetMap Tiles** | Map tile provider used with Leaflet               |

### External APIs / Services Used
| API / Service                   | Purpose                                     |
| ------------------------------- | ------------------------------------------- |
| **Google OAuth 2.0 API**        | User authentication/login via Google        |
| **Google reCAPTCHA API**        | Bot protection on login/signup forms        |
| **OpenStreetMap Nominatim API** | Address → coordinate geocoding              |
| **Cloudinary API**              | Image upload, storage, and delivery via CDN |

---

## Services Overview
### DatabaseService.py
Handles all database operations.

Includes:
* User creation and lookup
* Business profile creation and lookup
* Ratings and rating calculation
* Bookmarks system
* Recently viewed history
* Comments system (likes + timestamps)
* MongoDB indexing
* Profanity filtering integration

Collections:
* users
* business_profiles

Indexes:
* users.auth.google (unique, sparse)
* business_profiles.location (2dsphere index for geo queries)

### GeocodingService.py
Uses OpenStreetMap Nominatim API to convert addresses into coordinates.

Key features:
* Address sanitization (removes unit/suite info)
* Calls Nominatim API via requests
* Returns (latitude, longitude)

### ImageStorageService.py
Handles uploads to Cloudinary.

Key features:
* Max file size enforced: 5MB
* Allowed formats: JPEG, PNG
* Upload profile picture
* Upload business picture
* Delete profile picture
* Uses deterministic `public_id` to overwrite old images automatically

### RecommendationService.py
Responsible for ranking and filtering businesses.

Uses:
* MongoDB $geoNear query
* Optional filtering:
    * category match
    * search query regex
* Post-processing:
    * computes rating
    * computes distance (Haversine formula)
    * assigns score
* Sorting by score descending
* Scoring formula:
```python
(rating * 2) + log(bookmarks + 1) - (distance_km * 0.2)
```

---

## Security Notes
Businessly includes multiple security measures:
* Session-based authentication
* Google OAuth secure login
* Google reCAPTCHA to prevent bot abuse
* Input validation on:
    * ratings
    * comment length
    * form fields
    * categories
* Business profile modification checks:
    * only owner can modify their business profile
* Profanity filtering via better-profanity
* Comment spam protection:
    * duplicate detection
    * rate limiting logic

---

## Demo
A working demo can be can be found at [https://businessly.fxk3b.com](https://businessly.fxk3b.com).

---

## Credits
### Assets
* Some business placeholder/demo images on the [demo website](https://businessly.fxk3b.com) are from Adobe Stock.
