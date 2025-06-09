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
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, flash
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
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
            
            # Table des notifications
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL, -- 'price_error', 'promotion', 'suggestion'
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    sent BOOLEAN DEFAULT 0,
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
    """Gestionnaire des recettes avec intégration Jow"""
    
    def get_recipes(self) -> List[Dict]:
        """Récupère toutes les recettes"""
        recipes = db.execute_query('''
            SELECT * FROM recipes ORDER BY created_at DESC
        ''')
        
        # Parse les ingrédients JSON
        for recipe in recipes:
            if recipe['ingredients']:
                recipe['ingredients'] = json.loads(recipe['ingredients'])
        
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
    
    def add_recipe_to_shopping_list(self, recipe_id: int, servings_multiplier: float = 1.0) -> Dict:
        """Ajoute les ingrédients d'une recette à la liste de courses"""
        recipe = db.execute_query('''
            SELECT * FROM recipes WHERE id = ?
        ''', (recipe_id,))
        
        if not recipe:
            return {'success': False, 'message': 'Recette non trouvée'}
        
        recipe = recipe[0]
        ingredients = json.loads(recipe['ingredients'])
        
        shopping_manager = ShoppingListManager()
        added_count = 0
        
        for ingredient in ingredients:
            # Simple parsing des ingrédients (à améliorer selon le format)
            ingredient_name = ingredient.strip()
            shopping_manager.add_item(ingredient_name, 'Recettes')
            added_count += 1
        
        return {
            'success': True,
            'recipe_name': recipe['name'],
            'added_count': added_count
        }
    
    def fetch_jow_recipes(self, query: str = '') -> List[Dict]:
        """Récupère des recettes depuis l'API Jow (simulé)"""
        # NOTE: Implémentation simulée - remplacer par l'API réelle de Jow
        sample_recipes = [
            {
                'name': 'Pâtes à la carbonara',
                'source': 'Jow',
                'ingredients': ['pâtes', 'lardons', 'œufs', 'parmesan', 'crème fraîche'],
                'servings': 4
            },
            {
                'name': 'Salade César',
                'source': 'Jow',
                'ingredients': ['salade romaine', 'poulet', 'parmesan', 'croûtons', 'sauce césar'],
                'servings': 2
            }
        ]
        
        if query:
            sample_recipes = [r for r in sample_recipes if query.lower() in r['name'].lower()]
        
        return sample_recipes

class PriceMonitor:
    """Moniteur de prix avec détection d'erreurs Amazon"""
    
    def __init__(self):
        self.setup_selenium()
    
    def setup_selenium(self):
        """Configure le driver Selenium pour le scraping"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument(f'--user-agent={ua.random}')
            
            # Essayer de créer le driver (optionnel si pas de Chrome installé)
            self.driver = webdriver.Chrome(options=chrome_options)
        except WebDriverException:
            logger.warning("Chrome WebDriver non disponible - utilisation de requests uniquement")
            self.driver = None
    
    def check_amazon_prices(self, search_terms: List[str]) -> List[Dict]:
        """Vérifie les prix Amazon pour détecter les erreurs de prix"""
        alerts = []
        
        for term in search_terms:
            try:
                # Simulation d'une vérification Amazon (à adapter avec l'API réelle)
                # En production, utiliser l'API Amazon ou du scraping respectueux
                
                # Exemple de détection d'erreur de prix simulée
                if 'iphone' in term.lower():
                    alerts.append({
                        'product_name': f'iPhone 15 Pro - {term}',
                        'store': 'Amazon',
                        'original_price': 1229.0,
                        'current_price': 122.9,  # Prix suspect
                        'discount_percentage': 90.0,
                        'url': f'https://amazon.fr/search?k={term}',
                        'is_error': True
                    })
                
                time.sleep(1)  # Respecter les limites de taux
                
            except Exception as e:
                logger.error(f"Erreur lors de la vérification Amazon pour {term}: {e}")
        
        # Sauvegarder les alertes
        for alert in alerts:
            if alert['is_error']:
                self._save_price_alert(alert)
        
        return alerts
    
    def check_local_promotions(self) -> List[Dict]:
        """Vérifie les promotions chez Carrefour, Leclerc, Lidl"""
        promotions = []
        stores = {
            'Carrefour': 'https://www.carrefour.fr/promotions',
            'Leclerc': 'https://www.leclerc.com/promotions',
            'Lidl': 'https://www.lidl.fr/promotions'
        }
        
        for store, url in stores.items():
            try:
                # Simulation de scraping de promotions
                # En production, adapter selon la structure réelle des sites
                
                sample_promotions = [
                    {
                        'store': store,
                        'product_name': 'Lait demi-écrémé 1L',
                        'original_price': 1.20,
                        'promo_price': 0.99,
                        'discount_percentage': 17.5,
                        'category': 'Produits laitiers',
                        'valid_until': (datetime.now() + timedelta(days=7)).date()
                    },
                    {
                        'store': store,
                        'product_name': 'Pain de mie complet',
                        'original_price': 2.50,
                        'promo_price': 1.99,
                        'discount_percentage': 20.4,
                        'category': 'Boulangerie',
                        'valid_until': (datetime.now() + timedelta(days=5)).date()
                    }
                ]
                
                promotions.extend(sample_promotions)
                
            except Exception as e:
                logger.error(f"Erreur lors de la vérification des promotions {store}: {e}")
        
        # Sauvegarder les nouvelles promotions
        for promo in promotions:
            self._save_promotion(promo)
        
        return promotions
    
    def _save_price_alert(self, alert: Dict):
        """Sauvegarde une alerte de prix"""
        db.execute_update('''
            INSERT INTO price_alerts 
            (product_name, store, url, original_price, current_price, discount_percentage, is_error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert['product_name'], alert['store'], alert.get('url'), 
            alert['original_price'], alert['current_price'], 
            alert['discount_percentage'], alert['is_error']
        ))
    
    def _save_promotion(self, promo: Dict):
        """Sauvegarde une promotion locale"""
        # Vérifier si la promotion existe déjà
        existing = db.execute_query('''
            SELECT id FROM local_promotions 
            WHERE store = ? AND product_name = ? AND promo_price = ?
        ''', (promo['store'], promo['product_name'], promo['promo_price']))
        
        if not existing:
            db.execute_update('''
                INSERT INTO local_promotions 
                (store, product_name, original_price, promo_price, discount_percentage, category, valid_until)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                promo['store'], promo['product_name'], promo['original_price'],
                promo['promo_price'], promo['discount_percentage'], 
                promo['category'], promo['valid_until']
            ))

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
    
    def send_price_alert(self, alerts: List[Dict]):
        """Envoie les alertes de prix par email"""
        if not alerts:
            return
        
        subject = f"🚨 {len(alerts)} alertes de prix détectées!"
        
        body = """
        <h2>Alertes de prix Smart Shopping</h2>
        <p>Nous avons détecté des prix suspects qui pourraient être des erreurs:</p>
        <ul>
        """
        
        for alert in alerts:
            if alert['is_error']:
                body += f"""
                <li>
                    <strong>{alert['product_name']}</strong><br>
                    Prix original: {alert['original_price']}€<br>
                    Prix actuel: {alert['current_price']}€<br>
                    Réduction: {alert['discount_percentage']:.1f}%<br>
                    Magasin: {alert['store']}<br>
                </li>
                """
        
        body += """
        </ul>
        <p>Vérifiez rapidement ces offres avant qu'elles ne soient corrigées!</p>
        <p><em>Smart Shopping Assistant - Raspberry Pi</em></p>
        """
        
        if self.send_email_notification(subject, body):
            # Marquer les alertes comme notifiées
            for alert in alerts:
                db.execute_update('''
                    UPDATE price_alerts SET notified = 1 
                    WHERE product_name = ? AND store = ?
                ''', (alert['product_name'], alert['store']))
    
    def send_promotions_summary(self, promotions: List[Dict]):
        """Envoie un résumé des promotions locales"""
        if not promotions:
            return
        
        subject = f"🛒 {len(promotions)} nouvelles promotions disponibles!"
        
        body = """
        <h2>Promotions locales Smart Shopping</h2>
        <p>Nouvelles promotions détectées dans vos magasins préférés:</p>
        """
        
        # Grouper par magasin
        by_store = {}
        for promo in promotions:
            store = promo['store']
            if store not in by_store:
                by_store[store] = []
            by_store[store].append(promo)
        
        for store, store_promos in by_store.items():
            body += f"<h3>{store}</h3><ul>"
            for promo in store_promos:
                body += f"""
                <li>
                    <strong>{promo['product_name']}</strong><br>
                    {promo['original_price']}€ → {promo['promo_price']}€ 
                    (-{promo['discount_percentage']:.1f}%)<br>
                    Valable jusqu'au {promo['valid_until']}
                </li>
                """
            body += "</ul>"
        
        body += """
        <p><em>Smart Shopping Assistant - Raspberry Pi</em></p>
        """
        
        self.send_email_notification(subject, body)

# Instances des gestionnaires
shopping_manager = ShoppingListManager()
recipe_manager = RecipeManager()
price_monitor = PriceMonitor()
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

@app.route('/api/recipes/search-jow', methods=['GET'])
def search_jow_recipes():
    """API: Recherche des recettes Jow"""
    try:
        query = request.args.get('q', '')
        recipes = recipe_manager.fetch_jow_recipes(query)
        return jsonify(recipes)
    except Exception as e:
        logger.error(f"Erreur recherche recettes Jow: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/price-alerts', methods=['GET'])
def get_price_alerts():
    """API: Récupère les alertes de prix"""
    try:
        alerts = db.execute_query('''
            SELECT * FROM price_alerts 
            WHERE is_error = 1 
            ORDER BY created_at DESC LIMIT 50
        ''')
        return jsonify(alerts)
    except Exception as e:
        logger.error(f"Erreur récupération alertes: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/promotions', methods=['GET'])
def get_promotions():
    """API: Récupère les promotions locales"""
    try:
        promotions = db.execute_query('''
            SELECT * FROM local_promotions 
            WHERE valid_until >= date('now')
            ORDER BY discount_percentage DESC, created_at DESC
        ''')
        return jsonify(promotions)
    except Exception as e:
        logger.error(f"Erreur récupération promotions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-prices', methods=['POST'])
def manual_price_check():
    """API: Lance une vérification manuelle des prix"""
    try:
        data = request.get_json()
        search_terms = data.get('terms', [])
        
        if not search_terms:
            # Utiliser les articles de la liste de courses
            items = shopping_manager.get_shopping_list()
            search_terms = [item['name'] for item in items if not item['checked']]
        
        alerts = price_monitor.check_amazon_prices(search_terms)
        
        # Envoyer les alertes par email si demandé
        if alerts and data.get('notify', False):
            notification_manager.send_price_alert(alerts)
        
        return jsonify({
            'alerts_found': len(alerts),
            'alerts': alerts,
            'message': f'Vérification terminée: {len(alerts)} alertes trouvées'
        })
        
    except Exception as e:
        logger.error(f"Erreur vérification prix: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-promotions', methods=['POST'])
def manual_promotion_check():
    """API: Lance une vérification manuelle des promotions"""
    try:
        promotions = price_monitor.check_local_promotions()
        
        # Envoyer le résumé par email si demandé
        data = request.get_json() or {}
        if promotions and data.get('notify', False):
            notification_manager.send_promotions_summary(promotions)
        
        return jsonify({
            'promotions_found': len(promotions),
            'promotions': promotions,
            'message': f'Vérification terminée: {len(promotions)} promotions trouvées'
        })
        
    except Exception as e:
        logger.error(f"Erreur vérification promotions: {e}")
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

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """API: Récupère les statistiques de l'application"""
    try:
        stats = {
            'shopping_list_items': len(db.execute_query('SELECT id FROM shopping_list WHERE checked = 0')),
            'completed_items': len(db.execute_query('SELECT id FROM shopping_list WHERE checked = 1')),
            'recipes': len(db.execute_query('SELECT id FROM recipes')),
            'price_alerts': len(db.execute_query('SELECT id FROM price_alerts WHERE is_error = 1')),
            'active_promotions': len(db.execute_query("SELECT id FROM local_promotions WHERE valid_until >= date('now')")),
            'frequent_items': len(db.execute_query('SELECT id FROM frequent_items')),
            'last_price_check': db.execute_query('SELECT MAX(created_at) as last_check FROM price_alerts'),
            'last_promotion_check': db.execute_query('SELECT MAX(created_at) as last_check FROM local_promotions')
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Erreur récupération stats: {e}")
        return jsonify({'error': str(e)}), 500

# Tâches automatisées avec schedule

def scheduled_price_check():
    """Vérification automatique des prix (toutes les 2 heures)"""
    logger.info("Lancement vérification automatique des prix")
    try:
        # Récupérer les articles de la liste de courses
        items = shopping_manager.get_shopping_list()
        search_terms = [item['name'] for item in items if not item['checked']]
        
        if search_terms:
            alerts = price_monitor.check_amazon_prices(search_terms)
            if alerts:
                notification_manager.send_price_alert(alerts)
                logger.info(f"Vérification prix terminée: {len(alerts)} alertes envoyées")
        
    except Exception as e:
        logger.error(f"Erreur vérification automatique prix: {e}")

def scheduled_promotion_check():
    """Vérification automatique des promotions (tous les jours à 8h)"""
    logger.info("Lancement vérification automatique des promotions")
    try:
        promotions = price_monitor.check_local_promotions()
        if promotions:
            notification_manager.send_promotions_summary(promotions)
            logger.info(f"Vérification promotions terminée: {len(promotions)} promotions trouvées")
        
    except Exception as e:
        logger.error(f"Erreur vérification automatique promotions: {e}")

def scheduled_cleanup():
    """Nettoyage automatique de la base de données (tous les dimanches)"""
    logger.info("Lancement nettoyage automatique")
    try:
        # Supprimer les alertes anciennes (plus de 30 jours)
        db.execute_update('''
            DELETE FROM price_alerts 
            WHERE created_at < date('now', '-30 days')
        ''')
        
        # Supprimer les promotions expirées
        db.execute_update('''
            DELETE FROM local_promotions 
            WHERE valid_until < date('now', '-7 days')
        ''')
        
        # Supprimer les articles cochés anciens (plus de 7 jours)
        db.execute_update('''
            DELETE FROM shopping_list 
            WHERE checked = 1 AND updated_at < date('now', '-7 days')
        ''')
        
        logger.info("Nettoyage automatique terminé")
        
    except Exception as e:
        logger.error(f"Erreur nettoyage automatique: {e}")

# Configuration des tâches planifiées
schedule.every(2).hours.do(scheduled_price_check)
schedule.every().day.at("08:00").do(scheduled_promotion_check)
schedule.every().sunday.at("02:00").do(scheduled_cleanup)

def run_scheduler():
    """Lance le planificateur en arrière-plan"""
    while True:
        schedule.run_pending()
        time.sleep(60)  # Vérifier toutes les minutes

# Gestion des erreurs globales

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint non trouvé'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erreur interne du serveur'}), 500

@app.before_first_request
def startup():
    """Initialisation au démarrage de l'application"""
    logger.info("🚀 Démarrage Smart Shopping Assistant")
    
    # Lancer le planificateur en arrière-plan
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Planificateur de tâches démarré")
    
    # Vérifier la configuration email
    if not GMAIL_EMAIL or not GMAIL_APP_PASSWORD:
        logger.warning("⚠️  Configuration email manquante - les notifications seront désactivées")
    else:
        logger.info("✅ Configuration email détectée")
    
    # Exemple d'ajout de données de test (optionnel)
    if len(shopping_manager.get_shopping_list()) == 0:
        logger.info("Ajout de données de test...")
        shopping_manager.add_item("Lait", "Produits laitiers")
        shopping_manager.add_item("Pain", "Boulangerie")
        shopping_manager.add_item("Pommes", "Fruits et légumes")
        
        # Ajouter quelques recettes d'exemple
        recipe_manager.add_recipe(
            "Pancakes faciles",
            ["farine", "œufs", "lait", "sucre", "levure", "beurre"],
            "Personnalisée"
        )
        
        logger.info("Données de test ajoutées")

if __name__ == '__main__':
    try:
        # Configuration pour la production sur Raspberry Pi
        if os.getenv('FLASK_ENV') == 'production':
            logger.info("🔄 Mode production - utiliser Gunicorn pour le déploiement")
            # En production, l'app sera lancée par Gunicorn via systemd
        else:
            # Mode développement
            logger.info("🔧 Mode développement")
            app.run(host='0.0.0.0', port=5000, debug=True)
            
    except KeyboardInterrupt:
        logger.info("👋 Arrêt de l'application")
    except Exception as e:
        logger.error(f"💥 Erreur fatale: {e}")
        raise
