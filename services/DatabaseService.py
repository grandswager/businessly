from pymongo import MongoClient, ReturnDocument
import os
import uuid
from better_profanity import profanity
from bson.objectid import ObjectId
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db_client = client["db"]
users = db_client["users"]
business_profiles = db_client["business_profiles"]
sponsored_businesses = db_client["sponsored_businesses"]

users.create_index("auth.google", unique=True, sparse=True)
business_profiles.create_index([("location", "2dsphere")])
sponsored_businesses.create_index([("location", "2dsphere")])

class db:
    """
    Database abstraction layer for handling user and business operations.
    All methods are static to allow direct access without instantiating the class.
    """

    @staticmethod
    def get_user_by_google_id(google_id: str):
        """
        Retrieve a user by their Google authentication ID.
        """
        return users.find_one({"auth.google": google_id})

    @staticmethod
    def get_user_by_id(user_id: str):
        """
        Retrieve a user by MongoDB ObjectId.
        """
        return users.find_one({"_id": ObjectId(user_id)})
    
    @staticmethod
    def get_user_by_uuid(uuid: str):
        """
        Retrieve a user by internal UUID.
        """
        return users.find_one({"uuid": uuid})
    
    @staticmethod
    def get_business_info(uuid: str):
        """
        Retrieve business profile information by UUID.
        """
        return business_profiles.find_one({"uuid": uuid})
    
    @staticmethod
    def get_top_businesses(top: int = 10):
        """
        Return a random selection of businesses.
        Default is 10 businesses.
        """
        return list(business_profiles.aggregate([{"$sample": {"size": top}}]))

    @staticmethod
    def create_user(user_data: dict):
        """
        Insert a new user document into the database.
        """
        return users.insert_one(user_data)
    
    @staticmethod
    def create_business_profile(business_data: dict):
        """
        Insert a new business profile document.
        """
        return business_profiles.insert_one(business_data)

    @staticmethod
    def link_provider(user_id: str, provider: str, provider_id: str):
        """
        Link an authentication provider (e.g., Google, Facebook) to a user.
        """
        users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {f"auth.{provider}": provider_id}}
        )

    @staticmethod
    def update_user_picture(user_uuid: str, picture_url: str):
        """
        Update a user's profile picture.
        """
        return users.update_one(
            {"uuid": user_uuid},
            {"$set": {"picture": picture_url}}
        )
    
    @staticmethod
    def update_business_image(business_uuid: str, picture_url: str):
        """
        Update a business profile image.
        """
        return business_profiles.update_one(
            {"uuid": business_uuid},
            {"$set": {"image_url": picture_url}}
        )

    @staticmethod
    def update_standard_profile(user_uuid: str, name: str, categories: list):
        """
        Update a standard user's name and category preferences.
        """
        return users.update_one(
            {"uuid": user_uuid},
            {"$set": {"name": name, "categories": categories}}
        )

    @staticmethod
    def update_business_profile(user_uuid: str, updated_data: dict):
        """
        Update both the user's display name and the associated business profile data.
        Returns True on success or ValueError on failure.
        """
        try:
            users.update_one(
                {"uuid": user_uuid},
                {"$set": {"name": updated_data["name"]}}
            )

            business_profiles.update_one(
                {"uuid": user_uuid},
                {"$set": updated_data}
            )

            return True
        except:
            return ValueError("Something went wrong while updating your profile. Please try again later.")

    @staticmethod
    def create_coupon(business_uuid: str, coupon: dict):
        """
        Create a new coupon under a business profile.
        Coupons are stored as a nested dictionary keyed by UUID.
        """
        coupon_id = str(uuid.uuid4())

        return business_profiles.update_one(
            {"uuid": business_uuid},
            {"$set": {f"coupons.{coupon_id}": coupon}}
        )
    
    @staticmethod
    def delete_coupon(business_uuid: str, coupon_id: str):
        """
        Remove a coupon from a business profile using its UUID.
        """
        return business_profiles.update_one(
            {"uuid": business_uuid},
            {"$unset": {f"coupons.{coupon_id}": ""}}
        )

    @staticmethod
    def add_recent_business(user_uuid: str, business_uuid: str):
        """
        Add a business to the user's recently viewed list.
        Maintains uniqueness and limits to 10 most recent.
        """
        user = users.find_one({"uuid": user_uuid}, {"recently_viewed": 1})

        if not user:
            return None

        recent_businesses = user.get("recently_viewed", [])

        # Move to front if already exists
        if business_uuid in recent_businesses:
            recent_businesses.remove(business_uuid)

        recent_businesses.insert(0, business_uuid)

        # Keep only latest 10
        recent_businesses = recent_businesses[:10]

        users.update_one(
            {"uuid": user_uuid},
            {"$set": {"recently_viewed": recent_businesses}}
        )

        return recent_businesses

    @staticmethod
    def bookmark_business(user_uuid: str, business_uuid: str):
        """
        Toggle bookmark status for a business.
        Also updates business bookmark counter.
        Returns bookmark state and updated count.
        """
        user = users.find_one({"uuid": user_uuid}, {"bookmarks": 1})

        if not user:
            return None

        bookmarks = user.get("bookmarks", [])
        already_bookmarked = business_uuid in bookmarks

        if already_bookmarked:
            # Remove bookmark
            users.update_one({"uuid": user_uuid}, {"$pull": {"bookmarks": business_uuid}})

            business = business_profiles.find_one_and_update({"uuid": business_uuid, "bookmarks": {"$gt": 0}}, {"$inc": {"bookmarks": -1}}, projection={"bookmarks": 1, "_id": 0}, return_document=ReturnDocument.AFTER)

            return {
                "bookmarked": False,
                "business_bookmarks": business["bookmarks"],
                "business_uuid": business_uuid
            }

        else:
            # Add bookmark
            users.update_one({"uuid": user_uuid}, {"$addToSet": {"bookmarks": business_uuid}})

            business = business_profiles.find_one_and_update({"uuid": business_uuid}, {"$inc": {"bookmarks": 1}}, projection={"bookmarks": 1, "_id": 0}, return_document=ReturnDocument.AFTER)

            return {
                "bookmarked": True,
                "business_bookmarks": business["bookmarks"],
                "business_uuid": business_uuid
            }

    @staticmethod
    def rate_business(user_uuid: str, business_uuid: str, rating: int):
        """
        Add or update a user's rating for a business.
        Rating must be between 1 and 5.
        Updates combined rating and total users rated.
        """
        if rating < 1 or rating > 5:
            return None

        user = users.find_one({"uuid": user_uuid}, {"rated": 1})

        if not user:
            return None

        rated = user.get("rated", {})
        previous_rating = rated.get(business_uuid)

        if previous_rating is not None:
            # Update existing rating
            users.update_one({"uuid": user_uuid}, {"$set": {f"rated.{business_uuid}": rating}})

            business = business_profiles.find_one_and_update({"uuid": business_uuid}, {"$inc": {"combined_rating": rating - previous_rating}}, projection={"combined_rating": 1, "users_rated": 1, "_id": 0}, return_document=ReturnDocument.AFTER)

            return {
                "rated": True,
                "updated": True,
                "rating": rating,
                "business_uuid": business_uuid,
                "combined_rating": business["combined_rating"],
                "users_rated": business["users_rated"]
            }

        else:
            # New rating
            users.update_one({"uuid": user_uuid}, {"$set": {f"rated.{business_uuid}": rating}})

            business = business_profiles.find_one_and_update({"uuid": business_uuid}, {"$inc": {"combined_rating": rating, "users_rated": 1}}, projection={"combined_rating": 1, "users_rated": 1, "_id": 0}, return_document=ReturnDocument.AFTER)

            return {
                "rated": True,
                "updated": False,
                "rating": rating,
                "business_uuid": business_uuid,
                "combined_rating": business["combined_rating"],
                "users_rated": business["users_rated"]
            }

    @staticmethod
    def add_business_comment(business_uuid, user_uuid, text):
        """
        Add a comment to a business profile.
        Includes:
        - Profanity filtering
        - 30-second rate limit per user
        - Duplicate comment detection
        """
        business = business_profiles.find_one(
            {"uuid": business_uuid},
            {"comments": 1}
        )

        if not business:
            return None

        comments = business.get("comments")

        # Ensure comments field exists and is a dictionary
        if not isinstance(comments, dict):
            business_profiles.update_one(
                {"uuid": business_uuid},
                {"$set": {"comments": {}}}
            )
            comments = {}

        now = datetime.now(timezone.utc)

        # Rate limit and duplicate check
        for c in comments.values():
            if c["author_uuid"] == user_uuid:
                created = c["created"]

                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                
                if (now - created).total_seconds() < 30:
                    return "RATE_LIMIT"

                if c["comment"].lower() == text.lower():
                    return "DUPLICATE"

        comment_uuid = str(uuid.uuid4())

        comment = {
            "author_uuid": user_uuid,
            "comment": profanity.censor(text),
            "likes": 0,
            "liked_by": [],
            "created": now
        }

        business_profiles.update_one(
            {"uuid": business_uuid},
            {"$set": {f"comments.{comment_uuid}": comment}}
        )

        return comment_uuid

    @staticmethod
    def toggle_comment_like(business_uuid, comment_uuid, user_uuid):
        """
        Toggle like/unlike on a specific comment.
        Updates like counter and liked_by array atomically.
        """
        path = f"comments.{comment_uuid}"

        business = business_profiles.find_one(
            {"uuid": business_uuid, path: {"$exists": True}},
            {path: 1}
        )

        if not business:
            return None

        comment = business["comments"][comment_uuid]

        if user_uuid in comment.get("liked_by", []):
            # Unlike comment
            business_profiles.update_one(
                {"uuid": business_uuid},
                {
                    "$pull": {f"{path}.liked_by": user_uuid},
                    "$inc": {f"{path}.likes": -1}
                }
            )
            liked = False
        else:
            # Like comment
            business_profiles.update_one(
                {"uuid": business_uuid},
                {
                    "$addToSet": {f"{path}.liked_by": user_uuid},
                    "$inc": {f"{path}.likes": 1}
                }
            )
            liked = True

        updated = business_profiles.find_one(
            {"uuid": business_uuid},
            {f"{path}.likes": 1}
        )

        return {
            "liked": liked,
            "likes": updated["comments"][comment_uuid]["likes"]
        }
