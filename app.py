#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Shopping Assistant - Application Flask principale
Développé pour Raspberry Pi avec toutes les fonctionnalités avancées
"""

import os
import sqlite3
import json
import logging
import smtplib
import schedule
import time
from datetime import datetime, timedelta
from threading import Thread
from email.mime.text import MIMEText as MimeText
from email.mime.multipart import MIMEMultipart as MimeMultipart
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, flash
from flask_cors import CORS
from fake_useragent import UserAgent
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Configuration de l'application Flask
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'smart-shopping-secret-key')
CORS(app)

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/smart_shopping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration de la base de données
DB_PATH = os.getenv('DB_PATH', 'smart_shopping.db')

# Configuration email
GMAIL_EMAIL = os.getenv('GMAIL_EMAIL')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')

# User agent pour le scraping
ua = UserAgent()

class DatabaseManager:
    """Gestionnaire de base de données SQLite"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialise la structure de la base de données"""
        # Créer le répertoire logs s'il n'existe pas
        os.makedirs('logs', exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table des articles de la liste de courses
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shopping_list (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT DEFAULT 'Divers',
                    quantity INTEGER DEFAULT 1,
                    price REAL,
                    store TEXT,
                    checked BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Table des articles fréquents pour suggestions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS frequent_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    category TEXT,
                    usage_count INTEGER DEFAULT 1,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Table des recettes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recipes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    source TEXT,
                    url TEXT,
                    ingredients TEXT, -- JSON array
                    servings INTEGER DEFAULT 4,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Table des alertes de prix
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT NOT NULL,
                    store TEXT NOT NULL,
                    url TEXT,
                    original_price REAL,
                    current_price REAL,
                    discount_percentage REAL,
                    is_error BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notified BOOLEAN DEFAULT 0
                )
            ''')
            
            # Table des promotions locales
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS local_promotions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    original_price REAL,
                    promo_price REAL,
                    discount_percentage REAL,
                    valid_until DATE,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("Base de données initialisée avec succès")

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Exécute une requête SELECT et retourne les résultats"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Exécute une requête INSERT/UPDATE/DELETE et retourne l'ID ou le nombre de lignes affectées"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount

# Instance du gestionnaire de base de données
db = DatabaseManager(DB_PATH)

class ShoppingListManager:
    """Gestionnaire de la liste de courses avec suggestions intelligentes"""
    
    def get_shopping_list(self) -> List[Dict]:
        """Récupère la liste de courses actuelle"""
        return db.execute_query('''
            SELECT * FROM shopping_list 
            ORDER BY checked ASC, category, name
        ''')
    
    def add_item(self, name: str, category: str = 'Divers', quantity: int = 1) -> int:
        """Ajoute un article à la liste de courses"""
        item_id = db.execute_update('''
            INSERT INTO shopping_list (name, category, quantity)
            VALUES (?, ?, ?)
        ''', (name, category, quantity))
        
        # Mise à jour des statistiques pour les suggestions
        self._update_frequent_items(name, category)
        
        logger.info(f"Article ajouté: {name} (catégorie: {category})")
        return item_id
    
    def update_item(self, item_id: int, **kwargs) -> bool:
        """Met à jour un article de la liste"""
        allowed_fields = ['name', 'category', 'quantity', 'price', 'store', 'checked']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [item_id]
        
        rows_affected = db.execute_update(f'''
            UPDATE shopping_list 
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', tuple(values))
        
        return rows_affected > 0
    
    def remove_item(self, item_id: int) -> bool:
        """Supprime un article de la liste"""
        rows_affected = db.execute_update('''
            DELETE FROM shopping_list WHERE id = ?
        ''', (item_id,))
        
        return rows_affected > 0
    
    def get_suggestions(self, limit: int = 10) -> List[Dict]:
        """Récupère les suggestions basées sur les articles fréquents"""
        return db.execute_query('''
            SELECT name, category, usage_count
            FROM frequent_items
            WHERE name NOT IN (
                SELECT name FROM shopping_list WHERE checked = 0
            )
            ORDER BY usage_count DESC, last_used DESC
            LIMIT ?
        ''', (limit,))
    
    def _update_frequent_items(self, name: str, category: str):
        """Met à jour les statistiques des articles fréquents"""
        existing = db.execute_query('''
            SELECT id FROM frequent_items WHERE name = ?
        ''', (name,))
        
        if existing:
            db.execute_update('''
                UPDATE frequent_items 
                SET usage_count = usage_count + 1, last_used = CURRENT_TIMESTAMP
                WHERE name = ?
            ''', (name,))
        else:
            db.execute_update('''
                INSERT INTO frequent_items (name, category)
                VALUES (?, ?)
            ''', (name, category))

class RecipeManager:
    """Gestionnaire des recettes"""
    
    def get_recipes(self) -> List[Dict]:
        """Récupère toutes les recettes"""
        recipes = db.execute_query('''
            SELECT * FROM recipes ORDER BY created_at DESC
        ''')
        
        # Parse les ingrédients JSON
        for recipe in recipes:
            if recipe['ingredients']:
                try:
                    recipe['ingredients'] = json.loads(recipe['ingredients'])
                except:
                    recipe['ingredients'] = []
        
        return recipes
    
    def add_recipe(self, name: str, ingredients: List[str], source: str = 'Personnalisée', 
                   url: str = None, servings: int = 4) -> int:
        """Ajoute une nouvelle recette"""
        ingredients_json = json.dumps(ingredients)
        
        recipe_id = db.execute_update('''
            INSERT INTO recipes (name, source, url, ingredients, servings)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, source, url, ingredients_json, servings))
        
        logger.info(f"Recette ajoutée: {name}")
        return recipe_id
    
    def add_recipe_to_shopping_list(self, recipe_id: int) -> Dict:
        """Ajoute les ingrédients d'une recette à la liste de courses"""
        recipe = db.execute_query('''
            SELECT * FROM recipes WHERE id = ?
        ''', (recipe_id,))
        
        if not recipe:
            return {'success': False, 'message': 'Recette non trouvée'}
        
        recipe = recipe[0]
        try:
            ingredients = json.loads(recipe['ingredients'])
        except:
            ingredients = []
        
        shopping_manager = ShoppingListManager()
        added_count = 0
        
        for ingredient in ingredients:
            ingredient_name = ingredient.strip()
            shopping_manager.add_item(ingredient_name, 'Recettes')
            added_count += 1
        
        return {
            'success': True,
            'recipe_name': recipe['name'],
            'added_count': added_count
        }

class NotificationManager:
    """Gestionnaire des notifications email"""
    
    def send_email_notification(self, subject: str, body: str, recipient: str = None) -> bool:
        """Envoie une notification email"""
        if not GMAIL_EMAIL or not GMAIL_APP_PASSWORD:
            logger.warning("Configuration email manquante")
            return False
        
        recipient = recipient or GMAIL_EMAIL
        
        try:
            msg = MimeMultipart()
            msg['From'] = GMAIL_EMAIL
            msg['To'] = recipient
            msg['Subject'] = subject
            
            msg.attach(MimeText(body, 'html'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            text = msg.as_string()
            server.sendmail(GMAIL_EMAIL, recipient, text)
            server.quit()
            
            logger.info(f"Email envoyé: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")
            return False

# Instances des gestionnaires
shopping_manager = ShoppingListManager()
recipe_manager = RecipeManager()
notification_manager = NotificationManager()

# Routes API Flask

@app.route('/')
def index():
    """Page d'accueil de l'application"""
    return render_template('index.html')

@app.route('/api/shopping-list', methods=['GET'])
def get_shopping_list():
    """API: Récupère la liste de courses"""
    try:
        items = shopping_manager.get_shopping_list()
        return jsonify(items)
    except Exception as e:
        logger.error(f"Erreur récupération liste: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/shopping-list', methods=['POST'])
def add_shopping_item():
    """API: Ajoute un article à la liste de courses"""
    try:
        data = request.get_json()
        name = data.get('name')
        category = data.get('category', 'Divers')
        quantity = data.get('quantity', 1)
        
        if not name:
            return jsonify({'error': 'Le nom de l\'article est requis'}), 400
        
        item_id = shopping_manager.add_item(name, category, quantity)
        return jsonify({'id': item_id, 'message': 'Article ajouté avec succès'})
        
    except Exception as e:
        logger.error(f"Erreur ajout article: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/shopping-list/<int:item_id>', methods=['PUT'])
def update_shopping_item(item_id):
    """API: Met à jour un article de la liste"""
    try:
        data = request.get_json()
        success = shopping_manager.update_item(item_id, **data)
        
        if success:
            return jsonify({'message': 'Article mis à jour avec succès'})
        else:
            return jsonify({'error': 'Article non trouvé'}), 404
            
    except Exception as e:
        logger.error(f"Erreur mise à jour article: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/shopping-list/<int:item_id>', methods=['DELETE'])
def delete_shopping_item(item_id):
    """API: Supprime un article de la liste"""
    try:
        success = shopping_manager.remove_item(item_id)
        
        if success:
            return jsonify({'message': 'Article supprimé avec succès'})
        else:
            return jsonify({'error': 'Article non trouvé'}), 404
            
    except Exception as e:
        logger.error(f"Erreur suppression article: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/frequent-items', methods=['GET'])
def get_frequent_items():
    """API: Récupère les suggestions d'articles fréquents"""
    try:
        suggestions = shopping_manager.get_suggestions()
        return jsonify(suggestions)
    except Exception as e:
        logger.error(f"Erreur récupération suggestions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    """API: Récupère toutes les recettes"""
    try:
        recipes = recipe_manager.get_recipes()
        return jsonify(recipes)
    except Exception as e:
        logger.error(f"Erreur récupération recettes: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes', methods=['POST'])
def add_recipe():
    """API: Ajoute une nouvelle recette"""
    try:
        data = request.get_json()
        name = data.get('name')
        ingredients = data.get('ingredients', [])
        source = data.get('source', 'Personnalisée')
        servings = data.get('servings', 4)
        
        if not name or not ingredients:
            return jsonify({'error': 'Nom et ingrédients requis'}), 400
        
        recipe_id = recipe_manager.add_recipe(name, ingredients, source, servings=servings)
        return jsonify({'id': recipe_id, 'message': 'Recette ajoutée avec succès'})
        
    except Exception as e:
        logger.error(f"Erreur ajout recette: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes/<int:recipe_id>/add-to-list', methods=['POST'])
def add_recipe_to_list(recipe_id):
    """API: Ajoute les ingrédients d'une recette à la liste de courses"""
    try:
        result = recipe_manager.add_recipe_to_shopping_list(recipe_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Erreur ajout recette à la liste: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """API: Récupère les statistiques de l'application"""
    try:
        stats = {
            'shopping_list_items': len(db.execute_query('SELECT id FROM shopping_list WHERE checked = 0')),
            'completed_items': len(db.execute_query('SELECT id FROM shopping_list WHERE checked = 1')),
            'recipes': len(db.execute_query('SELECT id FROM recipes')),
            'price_alerts': 0,
            'active_promotions': 0,
            'frequent_items': len(db.execute_query('SELECT id FROM frequent_items'))
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Erreur récupération stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/send-test-email', methods=['POST'])
def send_test_email():
    """API: Envoie un email de test"""
    try:
        success = notification_manager.send_email_notification(
            "Test Smart Shopping",
            "<h2>Email de test</h2><p>Votre configuration email fonctionne correctement!</p>"
        )
        
        if success:
            return jsonify({'message': 'Email de test envoyé avec succès'})
        else:
            return jsonify({'error': 'Échec envoi email - vérifiez la configuration'}), 500
            
    except Exception as e:
        logger.error(f"Erreur test email: {e}")
        return jsonify({'error': str(e)}), 500

# Gestion des erreurs globales
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint non trouvé'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erreur interne du serveur'}), 500

if __name__ == '__main__':
    try:
        logger.info("🚀 Démarrage Smart Shopping Assistant")
        logger.info("🌐 Application accessible sur http://192.168.1.177")
        
        # Mode développement ou production
        if os.getenv('FLASK_ENV') == 'development':
            app.run(host='0.0.0.0', port=5000, debug=True)
        else:
            app.run(host='0.0.0.0', port=5000, debug=False)
            
    except KeyboardInterrupt:
        logger.info("👋 Arrêt de l'application")
    except Exception as e:
        logger.error(f"💥 Erreur fatale: {e}")
        raise
