import pymongo
from pymongo import MongoClient
import logging

# Configuration du logging pour suivre l'exécution et les erreurs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ArticleFetcher:

    def __init__(self, mongo_uri="mongodb://localhost:27017/", db_name="blogdumoderateur"):

        try:
            # Établissement de la connexion à MongoDB
            self.client = MongoClient(mongo_uri)

            # Accès à la base de données et à la collection "articles"
            self.db = self.client[db_name]
            self.collection = self.db.articles

            logger.info(f"Connexion MongoDB établie - Base: {db_name}")

        except Exception as e:
            # En cas d'erreur, logge le message et relance l'exception
            logger.error(f"Erreur connexion MongoDB: {e}")
            raise

    def get_articles_by_category(self, category_name):

        # Construction de la requête MongoDB :
        # - "$regex" pour une recherche insensible à la casse
        # - "^...$" pour une correspondance exacte (pas de sous-chaîne)
        query = {"category": {"$regex": f"^{category_name}$", "$options": "i"}}

        # Exécution de la requête et retour des résultats (sans le champ "_id")
        return list(self.collection.find(query, {"_id": 0}))

    def get_articles_by_subcategory(self, subcategory_name):

        # Construction de la requête MongoDB :
        # - "$regex" pour une recherche insensible à la casse dans le tableau "subcategories"
        query = {"subcategories": {"$regex": f"^{subcategory_name}$", "$options": "i"}}

        # Exécution de la requête et retour des résultats (sans le champ "_id")
        return list(self.collection.find(query, {"_id": 0}))

    def close(self):

        if hasattr(self, 'client'):
            self.client.close()

def display_articles(articles, search_type, search_term):

    print(f"\n--- Articles de la {search_type} '{search_term}' ---")
    if articles:
        for art in articles:
            print(f"- {art['title']} ({art['url']})")
    else:
        print(f"Aucun article trouvé pour cette {search_type}.")

def main():

    # Initialisation du fetcher
    fetcher = ArticleFetcher()

    print("=== Recherche d'articles ===")

    # Demande à l'utilisateur de choisir le type de recherche
    choix = input("Voulez-vous rechercher par (1) Catégorie ou (2) Sous-catégorie ? (1/2): ").strip()

    if choix == "1":
        # Recherche par catégorie
        categorie = input("Entrez le nom de la catégorie : ").strip()
        articles = fetcher.get_articles_by_category(categorie)
        display_articles(articles, "catégorie", categorie)

    elif choix == "2":
        # Recherche par sous-catégorie
        sous_categorie = input("Entrez le nom de la sous-catégorie : ").strip()
        articles = fetcher.get_articles_by_subcategory(sous_categorie)
        display_articles(articles, "sous-catégorie", sous_categorie)

    else:
        # Choix invalide
        print("Choix invalide. Veuillez relancer le script.")

    # Fermeture de la connexion à MongoDB
    fetcher.close()

if __name__ == "__main__":
    # Exécution de la fonction principale si le script est lancé directement
    main()
