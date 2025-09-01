import requests
from bs4 import BeautifulSoup
import pymongo
from pymongo import MongoClient
import re
from datetime import datetime
import time
from urllib.parse import urljoin, urlparse
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BlogDuModerateurScraper:
    def __init__(self, mongo_uri="mongodb://localhost:27017/", db_name="blogdumoderateur"):
        """
        Initialise le scraper avec connexion MongoDB
        """
        self.base_url = "https://www.blogdumoderateur.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Connexion MongoDB
        try:
            self.client = MongoClient(mongo_uri)
            self.db = self.client[db_name]
            self.collection = self.db.articles
            # Création d'un index sur le titre pour optimiser les recherches
            self.collection.create_index([("title", 1)], unique=True)
            logger.info(f"Connexion MongoDB établie - Base: {db_name}")
        except Exception as e:
            logger.error(f"Erreur connexion MongoDB: {e}")
            raise

    def get_page_content(self, url):
        """
        Récupère le contenu d'une page avec gestion d'erreurs
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération de {url}: {e}")
            return None

    def get_categories_list(self):
        """
        Récupère la liste des catégories depuis la page des dossiers
        """
        logger.info("Récupération de la liste des catégories...")
        soup = self.get_page_content(f"{self.base_url}/liste-des-dossiers/")
        
        if not soup:
            return []
        
        categories = []
        tags_list = soup.find('ul', class_='tags-list')
        
        if tags_list:
            for link in tags_list.find_all('a'):
                category_url = link.get('href')
                category_name = link.get('title', link.text.strip())
                categories.append({
                    'name': category_name,
                    'url': category_url
                })
        
        logger.info(f"Trouvé {len(categories)} catégories")
        return categories

    def extract_categories_and_subcategories(self, soup):
        """
        Extrait la catégorie principale et les sous-catégories depuis les métadonnées
        """
        main_category = ""
        subcategories = []
        
        # Recherche de la section meta contenant les catégories
        meta_section = soup.find('div', {'id': 'section-meta'}) or soup.find('div', class_='article-terms')
        
        if meta_section:
            # Récupération de la catégorie principale depuis .cats-list ou data-cat
            cats_list = meta_section.find('div', class_='cats-list')
            if cats_list:
                cat_span = cats_list.find('span', class_='cat')
                if cat_span and cat_span.get('data-cat'):
                    main_category = cat_span.get('data-cat').title()
            
            # Récupération des sous-catégories depuis les tags-list
            tags_list = meta_section.find('ul', class_='tags-list')
            if tags_list:
                for li in tags_list.find_all('li'):
                    link = li.find('a', class_='post-tags')
                    if link:
                        tag_name = link.get('title', link.text.strip())
                        tag_slug = link.get('data-tag', '')
                        
                        # Ne pas inclure la catégorie principale dans les sous-catégories
                        if tag_name.lower() != main_category.lower():
                            subcategories.append({
                                'name': tag_name,
                                'slug': tag_slug
                            })
        
        # Fallback pour la catégorie principale si pas trouvée
        if not main_category:
            fallback_selectors = ['.favtag', '.post-category', '.entry-category', '.category']
            for selector in fallback_selectors:
                cat_element = soup.select_one(selector)
                if cat_element:
                    main_category = cat_element.get_text(strip=True)
                    break
        
        return main_category, subcategories

    def get_articles_from_category(self, category_url, max_pages=5):
        """
        Récupère tous les articles d'une catégorie avec pagination
        """
        articles_urls = []
        
        for page in range(1, max_pages + 1):
            if page == 1:
                page_url = category_url
            else:
                page_url = f"{category_url}page/{page}/"
            
            logger.info(f"Scraping page {page}: {page_url}")
            soup = self.get_page_content(page_url)
            
            if not soup:
                break
            
            # Recherche des articles dans la page
            articles = soup.find_all('article')
            
            if not articles:
                logger.info(f"Aucun article trouvé sur la page {page}")
                break
            
            for article in articles:
                # Recherche du lien vers l'article complet
                link_element = article.find('a')
                if link_element and link_element.get('href'):
                    article_url = link_element['href']
                    if article_url not in articles_urls:
                        articles_urls.append(article_url)
            
            # Petite pause entre les requêtes
            time.sleep(1)
        
        logger.info(f"Trouvé {len(articles_urls)} articles dans la catégorie")
        return articles_urls

    def extract_article_content(self, soup):
        content_selectors = [
            '.entry-content',
            '.post-content',
            'article .content',
            'main article',
            '.article-content'
        ]
    
        content = ""
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                # Suppression des éléments indésirables AVANT l'extraction
                for unwanted in content_element.find_all([
                    'script', 'style', 'aside', '.related-posts', '.social-share',
                    '.social-catchphrase',  # Supprime la phrase "Suivez l'actualité du digital"
                    'noscript',  # Supprime les balises noscript
                    '.sharing-button',  # Supprime les boutons de partage
                    '.comments-section',  # Supprime les sections de commentaires
                    '#section-meta'  # Supprime les métadonnées
                ]):
                    unwanted.decompose()
                
                # Suppression spécifique des boutons de formation (liens avec classe btn)
                for btn in content_element.find_all('a', class_=['btn', 'featured-link', 'external']):
                    btn.decompose()
                
                # Suppression de la section sommaire si elle existe (car déjà extraite séparément)
                summary_section = content_element.find(class_='summary-section')
                if summary_section:
                    summary_section.decompose()
                
                # Extraction du contenu avec gestion de tous les types d'éléments
                content_parts = []
                
                # Récupération de tous les éléments de contenu dans l'ordre
                content_elements = content_element.find_all([
                    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                    'ul', 'ol', 'li', 'blockquote', 'div'
                ])
                
                for element in content_elements:
                    text = ""
                    
                    if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        # Pour les titres, on ajoute un préfixe pour les identifier
                        text = f"\n## {element.get_text(strip=True)}\n"
                    
                    elif element.name == 'p':
                        # Paragraphes normaux
                        text = element.get_text(strip=True)
                    
                    elif element.name in ['ul', 'ol']:
                        # Pour les listes, on traite les éléments li
                        list_items = []
                        for li in element.find_all('li', recursive=False):
                            li_text = li.get_text(strip=True)
                            if li_text and len(li_text) > 5:  # Ignore les items trop courts
                                list_items.append(f"• {li_text}")
                        
                        if list_items:
                            text = '\n'.join(list_items)
                    
                    elif element.name == 'li' and element.parent.name not in ['ul', 'ol']:
                        # Li orphelin (cas rare)
                        li_text = element.get_text(strip=True)
                        if li_text:
                            text = f"• {li_text}"
                    
                    elif element.name == 'blockquote':
                        # Citations
                        quote_text = element.get_text(strip=True)
                        if quote_text:
                            text = f'"{quote_text}"'
                    
                    elif element.name == 'div':
                        # Divs seulement si elles contiennent du texte direct (pas d'autres éléments)
                        if not element.find(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'div']):
                            div_text = element.get_text(strip=True)
                            if div_text and len(div_text) > 10:
                                text = div_text
                    
                    # Ajout du texte s'il est significatif
                    if text and len(text.strip()) > 3:
                        # Nettoyage des espaces multiples et caractères indésirables
                        text = re.sub(r'\s+', ' ', text.strip())
                        text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
                        
                        # Éviter les doublons
                        if text not in content_parts:
                            content_parts.append(text)
                
                # Assemblage final du contenu
                if content_parts:
                    content = '\n\n'.join(content_parts)
                    break
        
            # Nettoyage final
            content = re.sub(r'\n{3,}', '\n\n', content)  # Max 2 retours à la ligne consécutifs
            content = re.sub(r'[ \t]+', ' ', content)      # Supprime les espaces multiples
    
        return content.strip()

    def extract_summary(self, soup):
        """
        Extrait le sommaire de l'article
        """
        summary_selectors = [
            '.entry-excerpt',
            '.post-excerpt',
            '.article-excerpt',
            '.summary',
            'meta[name="description"]',
            'meta[property="og:description"]'
        ]
        
        for selector in summary_selectors:
            if selector.startswith('meta'):
                element = soup.select_one(selector)
                if element:
                    return element.get('content', '').strip()
            else:
                element = soup.select_one(selector)
                if element:
                    return element.get_text(strip=True)
        
        # Si pas de résumé dédié, prendre le premier paragraphe
        first_para = soup.select_one('.entry-content p, .post-content p, article p')
        if first_para:
            text = first_para.get_text(strip=True)
            if len(text) > 50:
                return text[:300] + "..." if len(text) > 300 else text
        
        return ""

    def extract_table_of_contents(self, soup):
        """
        Extrait le sommaire/table des matières spécifiquement du Blog du Modérateur
        Gère les cas avec <ol> et <ul>
        """
        # Recherche du sommaire spécifique à BDM
        summary_section = soup.select_one('.summary-section')
        
        if summary_section:
            # Recherche de la liste (ordonnée ou non-ordonnée) dans le sommaire
            summary_list = summary_section.select_one('.summary-inner')
            
            if summary_list:
                toc_items = []
                # Recherche des éléments <li> peu importe si c'est dans <ol> ou <ul>
                for li in summary_list.find_all('li'):
                    link = li.find('a')
                    if link:
                        # Récupération du texte du lien
                        title = link.get_text(strip=True)
                        # Nettoyage des caractères spéciaux HTML
                        title = title.replace('&nbsp;', ' ').replace('&amp;', '&')
                        if title:  # Ne pas ajouter les titres vides
                            toc_items.append(title)
                
                return toc_items
        
        # Fallback: autres sélecteurs possibles
        fallback_selectors = [
            '.table-of-contents ol li a, .table-of-contents ul li a',
            '.toc ol li a, .toc ul li a',
            '.wp-block-table-of-contents ol li a, .wp-block-table-of-contents ul li a'
        ]
        
        for selector in fallback_selectors:
            links = soup.select(selector)
            if links:
                toc_items = []
                for link in links:
                    title = link.get_text(strip=True).replace('&nbsp;', ' ').replace('&amp;', '&')
                    if title:
                        toc_items.append(title)
                return toc_items
        
        return []

    def extract_images(self, soup):
        """
        Extrait uniquement les images présentes dans le contenu de l'article
        """
        images = {}
        
        # Recherche spécifiquement dans le contenu de l'article
        content_selectors = [
            '.entry-content',
            '.post-content',
            'article .content',
            'main article',
            '.article-content'
        ]
        
        content_area = None
        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                break
        
        # Si aucune zone de contenu n'est trouvée, ne pas extraire d'images
        if not content_area:
            logger.warning("Aucune zone de contenu trouvée pour l'extraction des images")
            return images
        
        # Suppression des éléments indésirables avant extraction des images
        # (même logique que dans extract_article_content)
        for unwanted in content_area.find_all([
            'aside', '.related-posts', '.social-share',
            '.social-catchphrase', '.expert', '.guest-data'
        ]):
            unwanted.decompose()
        
        # Extraction des images uniquement dans la zone de contenu nettoyée
        img_elements = content_area.find_all('img')
        
        for i, img in enumerate(img_elements, 1):
            img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            
            if img_url:
                # URL absolue
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = self.base_url + img_url
                
                # Description de l'image
                description = (
                    img.get('alt') or 
                    img.get('title') or 
                    img.get('data-caption') or
                    ""
                ).strip()
                
                # Recherche de légende dans les éléments parents (figcaption)
                if not description:
                    # Recherche dans la figure parente
                    figure_parent = img.find_parent('figure')
                    if figure_parent:
                        caption = figure_parent.find('figcaption')
                        if caption:
                            description = caption.get_text(strip=True)
                    else:
                        # Recherche dans les parents directs pour d'autres types de légendes
                        parent = img.find_parent()
                        if parent:
                            caption = parent.find('figcaption')
                            if caption:
                                description = caption.get_text(strip=True)
                
                # Filtrage des images trop petites (probablement des icônes ou éléments décoratifs)
                width = img.get('width')
                height = img.get('height')
                
                # Ne garder que les images significatives (largeur > 200px si spécifiée)
                if width and width.isdigit() and int(width) < 200:
                    continue
                
                images[f"image_{i}"] = {
                    "url": img_url,
                    "description": description,
                    "alt": img.get('alt', ''),
                    "width": width,
                    "height": height
                }
        
        return images

    def extract_date(self, soup):
        """
        Extrait et formate la date de publication
        """
        date_selectors = [
            'time[datetime]',
            '.entry-date',
            '.post-date',
            '.published',
            'meta[property="article:published_time"]'
        ]
        
        for selector in date_selectors:
            date_element = soup.select_one(selector)
            if date_element:
                # Récupération de la date
                date_str = date_element.get('datetime') or date_element.get('content')
                if not date_str and hasattr(date_element, 'get_text'):
                    date_str = date_element.get_text(strip=True)
                
                if date_str:
                    try:
                        # Tentative de parsing de différents formats
                        for fmt in ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d', '%d/%m/%Y', '%d %B %Y']:
                            try:
                                if 'T' in date_str:
                                    # Format ISO avec timezone
                                    date_str = date_str.split('T')[0]
                                
                                # Nettoyage de la chaîne
                                date_str = re.sub(r'[^\d\-/\s\w]', '', date_str).strip()
                                
                                # Conversion des mois français si nécessaire
                                month_mapping = {
                                    'janvier': '01', 'février': '02', 'mars': '03',
                                    'avril': '04', 'mai': '05', 'juin': '06',
                                    'juillet': '07', 'août': '08', 'septembre': '09',
                                    'octobre': '10', 'novembre': '11', 'décembre': '12'
                                }
                                
                                for fr_month, num_month in month_mapping.items():
                                    if fr_month in date_str.lower():
                                        date_str = date_str.lower().replace(fr_month, num_month)
                                
                                parsed_date = datetime.strptime(date_str, fmt)
                                return parsed_date.strftime('%Y-%m-%d')
                            except ValueError:
                                continue
                    except:
                        pass
        
        return ""

    def extract_author(self, soup):
        """
        Extrait l'auteur de l'article
        """
        author_selectors = [
            '.entry-author',
            '.post-author',
            '.author',
            'meta[name="author"]',
            '.byline',
            '[rel="author"]'
        ]
        
        for selector in author_selectors:
            if selector.startswith('meta'):
                element = soup.select_one(selector)
                if element:
                    return element.get('content', '').strip()
            else:
                element = soup.select_one(selector)
                if element:
                    author_text = element.get_text(strip=True)
                    # Nettoyage du texte auteur
                    author_text = re.sub(r'^(par|by|author:)\s*', '', author_text, flags=re.I)
                    return author_text
        
        return ""

    def scrape_article(self, article_url):
        """
        Scrape un article complet
        """
        logger.info(f"Scraping article: {article_url}")
        
        soup = self.get_page_content(article_url)
        if not soup:
            return None
        
        # Extraction des données
        title_element = soup.select_one('h1.entry-title, h1.post-title, h1, .entry-title, .post-title')
        title = title_element.get_text(strip=True) if title_element else ""
        
        # Image principale (thumbnail)
        thumbnail_url = ""
        thumbnail_selectors = [
            '.post-thumbnail img',
            '.entry-image img',
            '.featured-image img',
            'meta[property="og:image"]'
        ]
        
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
        
        # URL absolue pour thumbnail
        if thumbnail_url:
            if thumbnail_url.startswith('//'):
                thumbnail_url = 'https:' + thumbnail_url
            elif thumbnail_url.startswith('/'):
                thumbnail_url = self.base_url + thumbnail_url
        
        # Extraction de la catégorie et sous-catégories depuis la section meta
        category = ""
        subcategories = []
        
        # Recherche dans la section meta pour les tags
        meta_section = soup.select_one('#section-meta, .meta-container')
        if meta_section:
            # Recherche de la liste des tags
            tags_list = meta_section.select('.tags-list a.post-tags')
            
            if tags_list:
                # Le premier tag devient la catégorie principale
                category = tags_list[0].get_text(strip=True)
                
                # Les tags suivants deviennent les sous-catégories
                for tag_link in tags_list[1:]:
                    subcategory = tag_link.get_text(strip=True)
                    if subcategory and subcategory not in subcategories:
                        subcategories.append(subcategory)
        
        # Fallback pour la catégorie si pas trouvée dans meta
        if not category:
            category_selectors = ['.favtag', '.post-category', '.entry-category', '.category']
            for selector in category_selectors:
                cat_element = soup.select_one(selector)
                if cat_element:
                    category = cat_element.get_text(strip=True)
                    break
        
        # Conversion de la liste des sous-catégories en chaîne (optionnel)
        subcategory_string = ", ".join(subcategories) if subcategories else ""
        
        article_data = {
            'url': article_url,
            'title': title,
            'thumbnail': thumbnail_url,
            'table_of_contents': self.extract_table_of_contents(soup),
            'category': category,
            'subcategory': subcategory_string,  # Chaîne des sous-catégories séparées par virgules
            'subcategories': subcategories,  # Liste des sous-catégories (optionnel)
            'summary': self.extract_summary(soup),
            'publication_date': self.extract_date(soup),
            'author': self.extract_author(soup),
            'content': self.extract_article_content(soup),
            'images': self.extract_images(soup),
            'scraped_at': datetime.now().isoformat()
        }
        
        return article_data

    def save_article(self, article_data):
        """
        Sauvegarde un article en base MongoDB
        """
        try:
            # Vérification si l'article existe déjà par titre
            existing = self.collection.find_one({'title': article_data['title']})
            
            if existing:
                logger.info(f"Article déjà existant (même titre): {article_data['title']}")
                return False
            else:
                # Insertion du nouvel article
                self.collection.insert_one(article_data)
                logger.info(f"Nouvel article sauvegardé: {article_data['title']}")
                return True
                
        except pymongo.errors.DuplicateKeyError:
            logger.warning(f"Tentative d'insertion d'un article avec un titre dupliqué: {article_data['title']}")
            return False
        except Exception as e:
            logger.error(f"Erreur sauvegarde: {e}")
            return False

    def run_scraper(self, max_categories=3, max_pages_per_category=2, max_articles_per_category=10):
        """
        Lance le scraping complet
        """
        logger.info("Début du scraping du Blog du Modérateur")
        
        # Récupération des catégories
        categories = self.get_categories_list()
        
        if not categories:
            logger.error("Impossible de récupérer les catégories")
            return
        
        processed_categories = 0
        total_articles_scraped = 0
        
        for category in categories[:max_categories]:
            logger.info(f"Traitement catégorie: {category['name']}")
            
            # Récupération des articles de la catégorie
            article_urls = self.get_articles_from_category(
                category['url'], 
                max_pages=max_pages_per_category
            )
            
            # Limitation du nombre d'articles par catégorie
            article_urls = article_urls[:max_articles_per_category]
            
            # Scraping de chaque article
            articles_scraped = 0
            for article_url in article_urls:
                try:
                    article_data = self.scrape_article(article_url)
                    
                    if article_data and article_data['title']:
                        # Ajout de la catégorie source
                        article_data['source_category'] = category['name']
                        
                        # Sauvegarde
                        if self.save_article(article_data):
                            articles_scraped += 1
                            total_articles_scraped += 1
                        
                        # Pause entre articles
                        time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Erreur scraping article {article_url}: {e}")
                    continue
            
            logger.info(f"Catégorie {category['name']} terminée: {articles_scraped} articles")
            processed_categories += 1
            
            # Pause entre catégories
            time.sleep(3)
        
        logger.info(f"Scraping terminé: {total_articles_scraped} articles dans {processed_categories} catégories")

    def close(self):
        """
        Ferme les connexions
        """
        if hasattr(self, 'client'):
            self.client.close()
        self.session.close()


def main():
    """
    Fonction principale
    """
    # Configuration - ajustez selon vos besoins
    MONGO_URI = "mongodb://localhost:27017/"  # Changez si nécessaire
    DB_NAME = "blogdumoderateur"
    
    try:
        # Initialisation du scraper
        scraper = BlogDuModerateurScraper(MONGO_URI, DB_NAME)
        
        # Lancement du scraping
        # Paramètres ajustables:
        # - max_categories: nombre de catégories à traiter
        # - max_pages_per_category: nombre de pages par catégorie
        # - max_articles_per_category: nombre max d'articles par catégorie
        scraper.run_scraper(
            max_categories=5, 
            max_pages_per_category=3, 
            max_articles_per_category=15
        )
        
    except KeyboardInterrupt:
        logger.info("Scraping interrompu par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
    finally:
        scraper.close()
        logger.info("Fermeture du scraper")


if __name__ == "__main__":
    main()