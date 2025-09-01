#!/usr/bin/env python3
"""
Script de lancement de l'application Flask
"""

from app import app

if __name__ == '__main__':
    print("🚀 Démarrage de l'application de recherche d'articles...")
    print("📊 Interface disponible sur: http://localhost:5000")
    print("🔍 API disponible sur: http://localhost:5000/api/search")
    print("💾 Assurez-vous que MongoDB est démarré avec la base 'blogdumoderateur'")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
