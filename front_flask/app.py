from flask import Flask
from models import ArticleSearcher
from routes import init_routes, process_content
from config import DEBUG, HOST, PORT

def create_app():
    """Factory function pour créer l'application Flask"""
    app = Flask(__name__)
    
    app.jinja_env.filters['process_content'] = process_content
    
    # Initialisation du searcher
    searcher = ArticleSearcher()
    
    # Initialisation des routes
    init_routes(app, searcher)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=DEBUG, host=HOST, port=PORT)
