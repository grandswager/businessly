from pymongo import MongoClient
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
