from scraper import BlogDuModerateurScraper
from mongo_utils import get_mongo_connection
from config import logger

def main():
    try:
        # Initialisation de la connexion MongoDB
        client, collection = get_mongo_connection()

        # Initialisation du scraper
        scraper = BlogDuModerateurScraper()

        # Lancement du scraping avec les paramètres suivants :
        # - max_categories : Nombre maximum de catégories à traiter
        # - max_pages_per_category : Nombre maximum de pages par catégorie
        # - max_articles_per_category : Nombre maximum d'articles par catégorie
        for article_data in scraper.run_scraper(
            max_categories=5,
            max_pages_per_category=3,
            max_articles_per_category=15
        ):
            try:
                # Vérification si l'article existe déjà en base (par titre)
                existing = collection.find_one({'title': article_data['title']})

                if not existing:
                    # Insertion du nouvel article en base
                    collection.insert_one(article_data)
                    logger.info(f"Nouvel article sauvegardé: {article_data['title']}")
                else:
                    logger.info(f"Article déjà existant: {article_data['title']}")

            except Exception as e:
                # En cas d'erreur lors de la sauvegarde, logge le message
                logger.error(f"Erreur sauvegarde: {e}")

    except KeyboardInterrupt:
        # Gestion de l'interruption par l'utilisateur (Ctrl+C)
        logger.info("Scraping interrompu par l'utilisateur")

    except Exception as e:
        # Gestion des erreurs inattendues
        logger.error(f"Erreur fatale: {e}")

    finally:
        # Fermeture des connexions (MongoDB et session HTTP)
        if 'client' in locals():
            client.close()
        logger.info("Fermeture du scraper")

if __name__ == "__main__":
    # Exécution de la fonction principale si le script est lancé directement
    main()
