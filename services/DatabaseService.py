from pymongo import MongoClient, ReturnDocument
import os
from dotenv import load_dotenv
from bson.objectid import ObjectId

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db_client = client["db"]
users = db_client["users"]
business_profiles = db_client["business_profiles"]

users.create_index("auth.google", unique=True, sparse=True)

business_profiles.create_index([("location", "2dsphere")])

class db:
    @staticmethod
    def get_user_by_google_id(google_id: str):
        return users.find_one({"auth.google": google_id})

    @staticmethod
    def get_user_by_id(user_id: str):
        return users.find_one({"_id": ObjectId(user_id)})
    
    @staticmethod
    def get_user_by_uuid(uuid: str):
        return users.find_one({"uuid": uuid})
    
    @staticmethod
    def get_business_info(uuid: str):
        return business_profiles.find_one({"uuid": uuid})
    
    @staticmethod
    def get_top_businesses(top: int = 10):
        return list(business_profiles.aggregate([{"$sample": {"size": top}}]))

    @staticmethod
    def create_user(user_data: dict):
        return users.insert_one(user_data)
    
    @staticmethod
    def create_business_profile(business_data: dict):
        return business_profiles.insert_one(business_data)

    @staticmethod
    def link_provider(user_id: str, provider: str, provider_id: str):
        users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {f"auth.{provider}": provider_id}}
        )

    @staticmethod
    def bookmark_business(user_uuid: str, business_uuid: str):
        user = users.find_one({"uuid": user_uuid}, {"bookmarks": 1})

        if not user:
            return None

        bookmarks = user.get("bookmarks", [])
        already_bookmarked = business_uuid in bookmarks

        if already_bookmarked:
            users.update_one({"uuid": user_uuid}, {"$pull": {"bookmarks": business_uuid}})

            business = business_profiles.find_one_and_update({"uuid": business_uuid, "bookmarks": {"$gt": 0}}, {"$inc": {"bookmarks": -1}}, projection={"bookmarks": 1, "_id": 0}, return_document=ReturnDocument.AFTER)

            return {
                "bookmarked": False,
                "business_bookmarks": business["bookmarks"],
                "business_uuid": business_uuid
            }

        else:
            users.update_one({"uuid": user_uuid}, {"$addToSet": {"bookmarks": business_uuid}})

            business = business_profiles.find_one_and_update({"uuid": business_uuid}, {"$inc": {"bookmarks": 1}}, projection={"bookmarks": 1, "_id": 0}, return_document=ReturnDocument.AFTER)

            return {
                "bookmarked": True,
                "business_bookmarks": business["bookmarks"],
                "business_uuid": business_uuid
            }

    @staticmethod
    def rate_business(user_uuid: str, business_uuid: str, rating: int):
        if rating < 1 or rating > 5:
            return None

        user = users.find_one({"uuid": user_uuid}, {"rated": 1})

        if not user:
            return None

        rated = user.get("rated", {})
        previous_rating = rated.get(business_uuid)

        if previous_rating is not None:
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
