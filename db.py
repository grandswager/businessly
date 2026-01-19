from pymongo import MongoClient
import os
from dotenv import load_dotenv
from bson.objectid import ObjectId

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db_client = client["db"]
users = db_client["users"]

users.create_index("auth.google", unique=True, sparse=True)

class db:
    @staticmethod
    def get_user_by_google_id(google_id: str):
        return users.find_one({"auth.google": google_id})

    @staticmethod
    def get_user_by_id(user_id: str):
        return users.find_one({"_id": ObjectId(user_id)})

    @staticmethod
    def create_user(user_data: dict):
        return users.insert_one(user_data)

    @staticmethod
    def link_provider(user_id: str, provider: str, provider_id: str):
        users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {f"auth.{provider}": provider_id}}
        )
