from pymongo import MongoClient
from config import logger, MONGO_URI, DB_NAME, COLLECTION_NAME

def get_mongo_connection():
    try:
        # Connexion au serveur MongoDB
        client = MongoClient(MONGO_URI)

        # Accès à la base de données et à la collection
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        # Création d'un index unique sur le champ 'title' pour éviter les doublons
        collection.create_index([("title", 1)], unique=True)

        logger.info(f"Connexion MongoDB établie - Base: {DB_NAME}")
        return client, collection

    except Exception as e:
        # En cas d'erreur, logge le message et relance l'exception
        logger.error(f"Erreur connexion MongoDB: {e}")
        raise
