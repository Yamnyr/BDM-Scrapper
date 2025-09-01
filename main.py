from scraper import BlogDuModerateurScraper
from mongo_utils import get_mongo_connection
from config import logger

def main():
    try:
        client, collection = get_mongo_connection()
        scraper = BlogDuModerateurScraper()
        for article_data in scraper.run_scraper(max_categories=5, max_pages_per_category=3, max_articles_per_category=15):
            try:
                existing = collection.find_one({'title': article_data['title']})
                if not existing:
                    collection.insert_one(article_data)
                    logger.info(f"Nouvel article sauvegardé: {article_data['title']}")
                else:
                    logger.info(f"Article déjà existant: {article_data['title']}")
            except Exception as e:
                logger.error(f"Erreur sauvegarde: {e}")
    except KeyboardInterrupt:
        logger.info("Scraping interrompu par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
    finally:
        if 'client' in locals():
            client.close()
        logger.info("Fermeture du scraper")

if __name__ == "__main__":
    main()
