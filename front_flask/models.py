from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from config import MONGO_URI, DB_NAME

class ArticleSearcher:
    def __init__(self, mongo_uri=MONGO_URI, db_name=DB_NAME):
        """Initialise la connexion MongoDB"""
        try:
            self.client = MongoClient(mongo_uri)
            self.db = self.client[db_name]
            self.collection = self.db.articles
            print(f"Connexion MongoDB établie - Base: {db_name}")
        except Exception as e:
            print(f"Erreur connexion MongoDB: {e}")
            raise

    def search_articles(self, filters):
        """
        Recherche des articles selon les critères fournis
        """
        query = {}
        
        # Recherche par titre (sous-chaîne)
        if filters.get('title'):
            query['title'] = {'$regex': filters['title'], '$options': 'i'}
        
        # Recherche par auteur
        if filters.get('author'):
            query['author'] = {'$regex': filters['author'], '$options': 'i'}
        
        # Recherche par catégorie
        if filters.get('category'):
            query['category'] = {'$regex': filters['category'], '$options': 'i'}
        
        # Recherche par sous-catégorie
        if filters.get('subcategory'):
            query['subcategory'] = {'$regex': filters['subcategory'], '$options': 'i'}
        
        # Recherche par plage de dates
        date_query = {}
        if filters.get('date_start'):
            try:
                start_date = datetime.strptime(filters['date_start'], '%Y-%m-%d').strftime('%Y-%m-%d')
                date_query['$gte'] = start_date
            except ValueError:
                pass
        
        if filters.get('date_end'):
            try:
                end_date = datetime.strptime(filters['date_end'], '%Y-%m-%d').strftime('%Y-%m-%d')
                date_query['$lte'] = end_date
            except ValueError:
                pass
        
        if date_query:
            query['publication_date'] = date_query
        
        # Exécution de la requête
        try:
            cursor = self.collection.find(query).sort('publication_date', -1)
            articles = list(cursor)
            
            # Conversion des ObjectId en string pour JSON
            for article in articles:
                article['_id'] = str(article['_id'])
            
            return articles
        except Exception as e:
            print(f"Erreur lors de la recherche: {e}")
            return []

    def get_unique_values(self, field):
        """Récupère les valeurs uniques d'un champ pour les filtres"""
        try:
            values = self.collection.distinct(field)
            return [v for v in values if v and v.strip()]
        except Exception as e:
            print(f"Erreur récupération valeurs uniques pour {field}: {e}")
            return []

    def get_unique_subcategories(self):
        """Récupère les sous-catégories uniques en séparant celles qui contiennent des virgules"""
        try:
            # Récupération de toutes les sous-catégories
            subcategories_raw = self.collection.distinct('subcategory')
            unique_subcategories = set()
            
            for subcategory in subcategories_raw:
                if subcategory and subcategory.strip():
                    if ',' in subcategory:
                        # Séparer par virgule et nettoyer chaque élément
                        parts = [part.strip() for part in subcategory.split(',')]
                        unique_subcategories.update(parts)
                    else:
                        unique_subcategories.add(subcategory.strip())
            
            # Retourner une liste triée en supprimant les valeurs vides
            return sorted([sub for sub in unique_subcategories if sub])
            
        except Exception as e:
            print(f"Erreur récupération sous-catégories uniques: {e}")
            return []

    def get_stats(self):
        """Récupère les statistiques de la base"""
        try:
            total_articles = self.collection.count_documents({})
            total_authors = len(self.get_unique_values('author'))
            total_categories = len(self.get_unique_values('category'))
            
            return {
                'total_articles': total_articles,
                'total_authors': total_authors,
                'total_categories': total_categories
            }
        except Exception as e:
            print(f"Erreur récupération statistiques: {e}")
            return {'total_articles': 0, 'total_authors': 0, 'total_categories': 0}
