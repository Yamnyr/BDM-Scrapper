from flask import render_template, request, jsonify
from bson import ObjectId
import re

def convert_video_links(content):
    """Convertit les liens vidéo en balises HTML video"""
    if not content:
        return content
    
    video_pattern = r'(https?://[^\s]+\.(?:mp4|webm|ogg|mov|avi)(?:\?[^\s]*)?)'
    
    def replace_video_link(match):
        video_url = match.group(1)
        return f'''<video controls class="w-full max-w-2xl mx-auto my-4 rounded-lg shadow-lg">
    <source src="{video_url}" type="video/mp4">
    Votre navigateur ne supporte pas la lecture de vidéos.
    <a href="{video_url}" target="_blank" class="text-pink-500 hover:text-pink-400">Télécharger la vidéo</a>
</video>'''
    
    return re.sub(video_pattern, replace_video_link, content)

def convert_markdown_titles(content):
    """Convertit les titres Markdown (##) en balises HTML"""
    if not content:
        return content
    
    # Conversion des titres de niveau 2 (##)
    content = re.sub(r'^## (.+)$', r'<h2 class="text-2xl font-bold text-gray-100 mt-8 mb-4 border-l-4 border-pink-500 pl-4">\1</h2>', content, flags=re.MULTILINE)
    
    # Conversion des titres de niveau 3 (###)
    content = re.sub(r'^### (.+)$', r'<h3 class="text-xl font-semibold text-gray-200 mt-6 mb-3">\1</h3>', content, flags=re.MULTILINE)
    
    # Conversion des titres de niveau 1 (#) si présents
    content = re.sub(r'^# (.+)$', r'<h1 class="text-3xl font-bold text-gray-100 mt-8 mb-6 border-b-2 border-pink-500 pb-2">\1</h1>', content, flags=re.MULTILINE)
    
    return content

def process_content(content):
    """Traite le contenu pour convertir les vidéos et les titres Markdown"""
    if not content:
        return content
    
    # D'abord les titres Markdown, puis les vidéos
    content = convert_markdown_titles(content)
    content = convert_video_links(content)
    
    return content

def init_routes(app, searcher):
    """Initialise toutes les routes de l'application"""
    
    app.jinja_env.filters['process_content'] = process_content
    
    @app.route('/')
    def index():
        """Page d'accueil avec formulaire de recherche"""
        # Récupération des valeurs pour les listes déroulantes
        authors = searcher.get_unique_values('author')
        categories = searcher.get_unique_values('category')
        subcategories = searcher.get_unique_subcategories()
        stats = searcher.get_stats()
        
        return render_template('index.html', 
                             authors=authors, 
                             categories=categories,
                             subcategories=subcategories,
                             stats=stats)

    @app.route('/search', methods=['POST'])
    def search():
        """Endpoint de recherche"""
        filters = {
            'title': request.form.get('title', '').strip(),
            'author': request.form.get('author', '').strip(),
            'category': request.form.get('category', '').strip(),
            'subcategory': request.form.get('subcategory', '').strip(),
            'date_start': request.form.get('date_start', '').strip(),
            'date_end': request.form.get('date_end', '').strip()
        }
        
        # Suppression des filtres vides
        filters = {k: v for k, v in filters.items() if v}
        
        articles = searcher.search_articles(filters)
        
        return render_template('results.html', 
                             articles=articles, 
                             filters=filters,
                             total_results=len(articles))

    @app.route('/article/<article_id>')
    def article_detail(article_id):
        """Page de détail d'un article"""
        try:
            article = searcher.collection.find_one({'_id': ObjectId(article_id)})
            if article:
                article['_id'] = str(article['_id'])
                return render_template('article_detail.html', article=article)
            else:
                return "Article non trouvé", 404
        except Exception as e:
            return f"Erreur: {e}", 500

    @app.route('/api/search', methods=['GET'])
    def api_search():
        """API de recherche (format JSON)"""
        filters = {
            'title': request.args.get('title', '').strip(),
            'author': request.args.get('author', '').strip(),
            'category': request.args.get('category', '').strip(),
            'subcategory': request.args.get('subcategory', '').strip(),
            'date_start': request.args.get('date_start', '').strip(),
            'date_end': request.args.get('date_end', '').strip()
        }
        
        # Suppression des filtres vides
        filters = {k: v for k, v in filters.items() if v}
        
        articles = searcher.search_articles(filters)
        
        return jsonify({
            'success': True,
            'total_results': len(articles),
            'filters': filters,
            'articles': articles
        })
