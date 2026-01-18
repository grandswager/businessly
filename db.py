from pymongo import MongoClient
import os
from dotenv import load_dotenv
from bson.objectid import ObjectId

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db_client = client["db"]
users = db_client["users"]

class db:
    @staticmethod
    def get_user_by_email(email: str):
        return users.find_one({"email": email})

    @staticmethod
    def get_user_by_id(user_id: str):
        return users.find_one({"_id": ObjectId(user_id)})

    @staticmethod
    def create_user(user_data: dict):
        return users.insert_one(user_data)

    @staticmethod
    def update_user_role(user_id: str, role: str):
        users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"role": role}}
        )
