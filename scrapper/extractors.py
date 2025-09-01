from bs4 import BeautifulSoup
from datetime import datetime
import re
from config import logger, BASE_URL

def extract_article_content(soup):

    content_selectors = [
        '.entry-content',
        '.post-content',
        'article .content',
        'main article',
        '.article-content'
    ]
    content = ""

    # Parcourt les sélecteurs possibles pour trouver la zone de contenu
    for selector in content_selectors:
        content_element = soup.select_one(selector)
        if content_element:
            # Suppression des éléments indésirables (scripts, publicités, partages sociaux, etc.)
            for unwanted in content_element.find_all([
                'script', 'style', 'aside', '.related-posts', '.social-share',
                '.social-catchphrase', 'noscript', '.sharing-button', '.comments-section', '#section-meta'
            ]):
                unwanted.decompose()

            # Suppression des boutons de type "formation" ou liens externes
            for btn in content_element.find_all('a', class_=['btn', 'featured-link', 'external']):
                btn.decompose()

            content_parts = []

            # Extraction des éléments de contenu (titres, paragraphes, listes, etc.)
            for element in content_element.find_all([
                'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'ul', 'ol', 'li', 'blockquote', 'div'
            ]):
                text = ""

                # Gestion des titres (h1 à h6)
                if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    text = f"\n## {element.get_text(strip=True)}\n"

                # Gestion des paragraphes
                elif element.name == 'p':
                    text = element.get_text(strip=True)

                # Gestion des listes (ul, ol)
                elif element.name in ['ul', 'ol']:
                    list_items = [
                        f"• {li.get_text(strip=True)}"
                        for li in element.find_all('li', recursive=False)
                        if len(li.get_text(strip=True)) > 5
                    ]
                    text = '\n'.join(list_items) if list_items else ""

                # Gestion des éléments de liste orphelins
                elif element.name == 'li' and element.parent.name not in ['ul', 'ol']:
                    text = f"• {element.get_text(strip=True)}" if element.get_text(strip=True) else ""

                # Gestion des citations (blockquote)
                elif element.name == 'blockquote':
                    text = f'"{element.get_text(strip=True)}"' if element.get_text(strip=True) else ""

                # Gestion des divs contenant du texte direct
                elif element.name == 'div':
                    if not element.find(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'div']):
                        div_text = element.get_text(strip=True)
                        text = div_text if div_text and len(div_text) > 10 else ""

                # Ajout du texte extrait s'il est significatif
                if text and len(text.strip()) > 3:
                    text = re.sub(r'\s+', ' ', text.strip())
                    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
                    if text not in content_parts:
                        content_parts.append(text)

            # Assemblage du contenu final
            if content_parts:
                content = '\n\n'.join(content_parts)
                break

    # Nettoyage final du contenu
    content = re.sub(r'\n{3,}', '\n\n', content)  # Limite à 2 sauts de ligne consécutifs
    content = re.sub(r'[ \t]+', ' ', content)      # Supprime les espaces multiples
    return content.strip()

def extract_summary(soup):

    summary_selectors = [
        '.entry-excerpt',
        '.post-excerpt',
        '.article-excerpt',
        '.summary',
        'meta[name="description"]',
        'meta[property="og:description"]'
    ]

    # Recherche du résumé dans les sélecteurs définis
    for selector in summary_selectors:
        if selector.startswith('meta'):
            element = soup.select_one(selector)
            if element:
                return element.get('content', '').strip()
        else:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)

    # Fallback : utilise le premier paragraphe si aucun résumé n'est trouvé
    first_para = soup.select_one('.entry-content p, .post-content p, article p')
    if first_para:
        text = first_para.get_text(strip=True)
        return text[:300] + "..." if len(text) > 300 else text

    return ""

def extract_table_of_contents(soup):

    # Recherche du sommaire spécifique au Blog du Modérateur
    summary_section = soup.select_one('.summary-section')
    if summary_section:
        summary_list = summary_section.select_one('.summary-inner')
        if summary_list:
            toc_items = []
            for li in summary_list.find_all('li'):
                link = li.find('a')
                if link:
                    title = link.get_text(strip=True).replace('&nbsp;', ' ').replace('&amp;', '&')
                    if title:
                        toc_items.append(title)
            return toc_items

    # Fallback : recherche dans d'autres sélecteurs possibles
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

def extract_images(soup):

    images = {}
    content_selectors = [
        '.entry-content',
        '.post-content',
        'article .content',
        'main article',
        '.article-content'
    ]

    # Recherche de la zone de contenu principale
    content_area = None
    for selector in content_selectors:
        content_area = soup.select_one(selector)
        if content_area:
            break

    if not content_area:
        logger.warning("Aucune zone de contenu trouvée pour l'extraction des images")
        return images

    # Suppression des éléments indésirables avant extraction des images
    for unwanted in content_area.find_all([
        'aside', '.related-posts', '.social-share',
        '.social-catchphrase', '.expert', '.guest-data'
    ]):
        unwanted.decompose()

    # Extraction des images dans la zone de contenu
    img_elements = content_area.find_all('img')
    for i, img in enumerate(img_elements, 1):
        img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
        if img_url:
            # Construction de l'URL absolue de l'image
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif img_url.startswith('/'):
                img_url = BASE_URL + img_url

            # Extraction de la description de l'image
            description = (
                img.get('alt') or
                img.get('title') or
                img.get('data-caption') or
                ""
            ).strip()

            # Recherche de légende dans les éléments parents (figcaption)
            if not description:
                figure_parent = img.find_parent('figure')
                if figure_parent:
                    caption = figure_parent.find('figcaption')
                    if caption:
                        description = caption.get_text(strip=True)

            # Filtrage des images trop petites (icônes, éléments décoratifs)
            width = img.get('width')
            height = img.get('height')
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

def extract_date(soup):

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
            date_str = date_element.get('datetime') or date_element.get('content')
            if not date_str and hasattr(date_element, 'get_text'):
                date_str = date_element.get_text(strip=True)

            if date_str:
                try:
                    # Tentative de parsing avec différents formats de date
                    for fmt in ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d', '%d/%m/%Y', '%d %B %Y']:
                        try:
                            if 'T' in date_str:
                                date_str = date_str.split('T')[0]

                            # Nettoyage de la chaîne de date
                            date_str = re.sub(r'[^\d\-/\s\w]', '', date_str).strip()

                            # Conversion des mois en français vers des numéros
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
                except Exception:
                    pass

    return ""

def extract_author(soup):
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
                # Nettoyage du texte (suppression de "par", "by", etc.)
                author_text = re.sub(r'^(par|by|author:)\s*', '', author_text, flags=re.I)
                return author_text

    return ""
