import pymongo
from pymongo import MongoClient
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ArticleFetcher:
    def __init__(self, mongo_uri="mongodb://localhost:27017/", db_name="blogdumoderateur"):
        """
        Connexion à la base MongoDB
        """
        try:
            self.client = MongoClient(mongo_uri)
            self.db = self.client[db_name]
            self.collection = self.db.articles
            logger.info(f"Connexion MongoDB établie - Base: {db_name}")
        except Exception as e:
            logger.error(f"Erreur connexion MongoDB: {e}")
            raise

    def get_articles_by_category(self, category_name):
        """
        Retourne tous les articles d'une catégorie
        """
        query = {"category": {"$regex": f"^{category_name}$", "$options": "i"}}
        return list(self.collection.find(query, {"_id": 0}))

    def get_articles_by_subcategory(self, subcategory_name):
        """
        Retourne tous les articles d'une sous-catégorie
        """
        query = {"subcategories": {"$regex": f"^{subcategory_name}$", "$options": "i"}}
        return list(self.collection.find(query, {"_id": 0}))

    def close(self):
        if hasattr(self, 'client'):
            self.client.close()

def main():
    fetcher = ArticleFetcher()

    print("=== Recherche d'articles ===")
    choix = input("Voulez-vous rechercher par (1) Catégorie ou (2) Sous-catégorie ? (1/2): ").strip()

    if choix == "1":
        categorie = input("Entrez le nom de la catégorie : ").strip()
        articles = fetcher.get_articles_by_category(categorie)
        print(f"\n--- Articles de la catégorie '{categorie}' ---")
        if articles:
            for art in articles:
                print(f"- {art['title']} ({art['url']})")
        else:
            print("Aucun article trouvé pour cette catégorie.")

    elif choix == "2":
        sous_categorie = input("Entrez le nom de la sous-catégorie : ").strip()
        articles = fetcher.get_articles_by_subcategory(sous_categorie)
        print(f"\n--- Articles de la sous-catégorie '{sous_categorie}' ---")
        if articles:
            for art in articles:
                print(f"- {art['title']} ({art['url']})")
        else:
            print("Aucun article trouvé pour cette sous-catégorie.")

    else:
        print("Choix invalide. Veuillez relancer le script.")

    fetcher.close()

if __name__ == "__main__":
    main()
