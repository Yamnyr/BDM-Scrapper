import requests
from bs4 import BeautifulSoup
import time
from config import logger, BASE_URL, USER_AGENT
from extractors import (
    extract_article_content,
    extract_summary,
    extract_table_of_contents,
    extract_images,
    extract_date,
    extract_author
)
from datetime import datetime  # Import nécessaire pour gérer les dates et heures

class BlogDuModerateurScraper:

    def __init__(self):
        """
        Initialise le scraper avec une session HTTP et un User-Agent personnalisé.
        """
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})

    def get_page_content(self, url):

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()  # Lève une exception si la requête échoue
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération de {url}: {e}")
            return None

    def get_categories_list(self):

        logger.info("Récupération de la liste des catégories...")
        soup = self.get_page_content(f"{BASE_URL}/liste-des-dossiers/")
        if not soup:
            return []

        categories = []
        tags_list = soup.find('ul', class_='tags-list')
        if tags_list:
            for link in tags_list.find_all('a'):
                category_url = link.get('href')
                category_name = link.get('title', link.text.strip())
                categories.append({'name': category_name, 'url': category_url})

        logger.info(f"Trouvé {len(categories)} catégories")
        return categories

    def get_articles_from_category(self, category_url, max_pages=5):

        articles_urls = []
        for page in range(1, max_pages + 1):
            page_url = category_url if page == 1 else f"{category_url}page/{page}/"
            logger.info(f"Scraping page {page}: {page_url}")
            soup = self.get_page_content(page_url)
            if not soup:
                break

            articles = soup.find_all('article')
            if not articles:
                logger.info(f"Aucun article trouvé sur la page {page}")
                break

            for article in articles:
                link_element = article.find('a')
                if link_element and link_element.get('href'):
                    article_url = link_element['href']
                    if article_url not in articles_urls:
                        articles_urls.append(article_url)

            time.sleep(1)  # Pause pour éviter de surcharger le serveur

        logger.info(f"Trouvé {len(articles_urls)} articles dans la catégorie")
        return articles_urls

    def scrape_article(self, article_url):
        logger.info(f"Scraping article: {article_url}")
        soup = self.get_page_content(article_url)
        if not soup:
            return None

        # Extraction du titre
        title_element = soup.select_one('h1.entry-title, h1.post-title, h1, .entry-title, .post-title')
        title = title_element.get_text(strip=True) if title_element else ""

        # Extraction de l'image principale (thumbnail)
        thumbnail_url = ""
        thumbnail_selectors = ['.post-thumbnail img', '.entry-image img', '.featured-image img', 'meta[property="og:image"]']
        for selector in thumbnail_selectors:
            if selector.startswith('meta'):
                element = soup.select_one(selector)
                if element:
                    thumbnail_url = element.get('content', '')
                    break
            else:
                element = soup.select_one(selector)
                if element:
                    thumbnail_url = element.get('src') or element.get('data-src') or element.get('data-lazy-src')
                    if thumbnail_url:
                        break

        # Construction de l'URL absolue pour le thumbnail
        if thumbnail_url:
            if thumbnail_url.startswith('//'):
                thumbnail_url = 'https:' + thumbnail_url
            elif thumbnail_url.startswith('/'):
                thumbnail_url = BASE_URL + thumbnail_url

        # Extraction de la catégorie et des sous-catégories
        category = ""
        subcategories = []
        meta_section = soup.select_one('#section-meta, .meta-container')
        if meta_section:
            tags_list = meta_section.select('.tags-list a.post-tags')
            if tags_list:
                category = tags_list[0].get_text(strip=True)
                for tag_link in tags_list[1:]:
                    subcategory = tag_link.get_text(strip=True)
                    if subcategory and subcategory not in subcategories:
                        subcategories.append(subcategory)

        # Fallback pour la catégorie si non trouvée dans la meta-section
        if not category:
            category_selectors = ['.favtag', '.post-category', '.entry-category', '.category']
            for selector in category_selectors:
                cat_element = soup.select_one(selector)
                if cat_element:
                    category = cat_element.get_text(strip=True)
                    break

        subcategory_string = ", ".join(subcategories) if subcategories else ""

        # Construction du dictionnaire de données de l'article
        article_data = {
            'url': article_url,
            'title': title,
            'thumbnail': thumbnail_url,
            'table_of_contents': extract_table_of_contents(soup),
            'category': category,
            'subcategory': subcategory_string,
            'subcategories': subcategories,
            'summary': extract_summary(soup),
            'publication_date': extract_date(soup),
            'author': extract_author(soup),
            'content': extract_article_content(soup),
            'images': extract_images(soup),
            'scraped_at': datetime.now().isoformat()  # Date et heure du scraping
        }

        return article_data

    def run_scraper(self, max_categories=3, max_pages_per_category=2, max_articles_per_category=10):
        logger.info("Début du scraping du Blog du Modérateur")
        categories = self.get_categories_list()
        if not categories:
            logger.error("Impossible de récupérer les catégories")
            return

        processed_categories = 0
        total_articles_scraped = 0

        for category in categories[:max_categories]:
            logger.info(f"Traitement catégorie: {category['name']}")
            article_urls = self.get_articles_from_category(category['url'], max_pages=max_pages_per_category)
            article_urls = article_urls[:max_articles_per_category]

            articles_scraped = 0
            for article_url in article_urls:
                try:
                    article_data = self.scrape_article(article_url)
                    if article_data and article_data['title']:
                        article_data['source_category'] = category['name']
                        yield article_data  # Utilisation de yield pour générer les articles un par un
                        articles_scraped += 1
                        total_articles_scraped += 1
                    time.sleep(2)  # Pause entre chaque article
                except Exception as e:
                    logger.error(f"Erreur scraping article {article_url}: {e}")
                    continue

            logger.info(f"Catégorie {category['name']} terminée: {articles_scraped} articles")
            processed_categories += 1
            time.sleep(3)  # Pause entre chaque catégorie

        logger.info(f"Scraping terminé: {total_articles_scraped} articles dans {processed_categories} catégories")
