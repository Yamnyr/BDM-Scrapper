from pymongo import MongoClient
from config import logger, MONGO_URI, DB_NAME, COLLECTION_NAME

def get_mongo_connection():
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        collection.create_index([("title", 1)], unique=True)
        logger.info(f"Connexion MongoDB établie - Base: {DB_NAME}")
        return client, collection
    except Exception as e:
        logger.error(f"Erreur connexion MongoDB: {e}")
        raise
