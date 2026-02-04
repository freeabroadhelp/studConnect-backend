from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection string
MONGO_DETAILS = os.getenv("MONGO_URI", "mongodb+srv://admin:Demo@1910@userauth.zybyise.mongodb.net/")
DATABASE_NAME = os.getenv("MONGO_DATABASE", "studconnect")

# Create async client
client = AsyncIOMotorClient(MONGO_DETAILS)
db = client[DATABASE_NAME]

# Collections
users_collection = db["users"]