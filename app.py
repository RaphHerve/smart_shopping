#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Shopping Assistant - Application Flask CORRIGÉE SANS LXML
- Configuration Flask-Limiter corrigée
- Import modules corrigé
- BeautifulSoup avec html.parser uniquement
"""

import os
import sqlite3
import json
import logging
import smtplib
import schedule
import time
import requests
import re
from datetime import datetime, timedelta
from threading import Thread
from email.mime.text import MIMEText as MimeText
from email.mime.multipart import MIMEMultipart as MimeMultipart
from typing import List, Dict, Any, Optional
from functools import wraps

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, flash
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from fake_useragent import UserAgent
from dotenv import load_dotenv

# Import des modules corrigés - CORRECTION DU NOM
try:
    from real_jow_marmiton_scraper import unified_recipe_scraper
    SCRAPER_AVAILABLE = True
    print("✅ Scraper importé avec succès")
except ImportError as e:
    print(f"⚠️  Erreur import scraper: {e}")
    SCRAPER_AVAILABLE = False

try:
    from intelligent_quantity_manager import get_ingredient_manager, upgrade_database_schema
    QUANTITY_MANAGER_AVAILABLE = True
    print("✅ Gestionnaire quantités importé avec succès")
except ImportError as e:
    print(f"⚠️  Erreur import gestionnaire quantités: {e}")
    QUANTITY_MANAGER_AVAILABLE = False

# Chargement des variables d'environnement
load_dotenv()

# Configuration de l'application Flask
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'smart-shopping-secret-key-v2')
CORS(app)

# Configuration Rate Limiting CORRIGÉE
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Configuration Redis pour le cache - avec gestion d'erreur
try:
    import redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    CACHE_ENABLED = True
    print("✅ Redis connecté - Cache activé")
except Exception as e:
    CACHE_ENABLED = False
    print(f"⚠️  Redis non disponible - Cache désactivé: {e}")

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
    """Gestionnaire de base de données SQLite AMÉLIORÉ"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
        self.optimize_database()
    
    def init_database(self):
        """Initialise la structure de la base de données"""
        os.makedirs('logs', exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table shopping_list AMÉLIORÉE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shopping_list (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT DEFAULT 'Divers',
                    quantity INTEGER DEFAULT 1,
                    quantity_decimal REAL,
                    unit TEXT DEFAULT 'unité',
                    price REAL,
                    store TEXT,
                    checked BOOLEAN DEFAULT 0,
                    recipe_sources TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Autres tables existantes...
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS frequent_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    category TEXT,
                    usage_count INTEGER DEFAULT 1,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recipes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    source TEXT,
                    url TEXT,
                    ingredients TEXT,
                    servings INTEGER DEFAULT 4,
                    prep_time INTEGER DEFAULT 30,
                    difficulty TEXT DEFAULT 'Moyen',
                    image_url TEXT,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS jow_recipes_cache (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    data TEXT,
                    search_query TEXT,
                    source TEXT DEFAULT 'jow',
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tables pour analytics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    data TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("Base de données initialisée avec succès")
    
    def optimize_database(self):
        """Optimise les performances SQLite"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Optimisations SQLite
            optimizations = [
                "PRAGMA journal_mode = WAL",
                "PRAGMA synchronous = NORMAL", 
                "PRAGMA cache_size = 10000",
                "PRAGMA temp_store = memory",
                
                # Index pour performances
                "CREATE INDEX IF NOT EXISTS idx_shopping_checked ON shopping_list(checked)",
                "CREATE INDEX IF NOT EXISTS idx_shopping_name_lower ON shopping_list(LOWER(name))",
                "CREATE INDEX IF NOT EXISTS idx_frequent_usage ON frequent_items(usage_count DESC)",
                "CREATE INDEX IF NOT EXISTS idx_recipes_name ON recipes(name)",
                "CREATE INDEX IF NOT EXISTS idx_cache_query ON jow_recipes_cache(search_query)",
            ]
            
            for optimization in optimizations:
                try:
                    cursor.execute(optimization)
                except Exception as e:
                    logger.warning(f"Optimization failed: {optimization} - {e}")
            
            conn.commit()
            logger.info("✅ Base de données optimisée")

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Exécute une requête SELECT et retourne les résultats"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Exécute une requête INSERT/UPDATE/DELETE"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount

# Instance du gestionnaire de base de données
db = DatabaseManager(DB_PATH)

# Initialiser le gestionnaire d'ingrédients si disponible
if QUANTITY_MANAGER_AVAILABLE:
    try:
        ingredient_manager = get_ingredient_manager(DB_PATH)
        upgrade_database_schema(DB_PATH)
        print("✅ Gestionnaire d'ingrédients initialisé")
    except Exception as e:
        print(f"⚠️  Erreur initialisation gestionnaire: {e}")
        QUANTITY_MANAGER_AVAILABLE = False

# Décorateur pour le cache Redis
def cache_result(key_prefix: str, ttl: int = 3600):
    """Décorateur pour mettre en cache les résultats"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not CACHE_ENABLED:
                return func(*args, **kwargs)
            
            # Générer la clé de cache
            cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"
            
            # Vérifier le cache
            try:
                cached_result = redis_client.get(cache_key)
                if cached_result:
                    return json.loads(cached_result)
            except:
                pass
            
            # Exécuter la fonction et mettre en cache
            result = func(*args, **kwargs)
            
            try:
                redis_client.setex(cache_key, ttl, json.dumps(result, default=str))
            except:
                pass
            
            return result
        return wrapper
    return decorator

class ShoppingListManager:
    """Gestionnaire CORRIGÉ de la liste de courses"""
    
    def get_shopping_list(self) -> List[Dict]:
        """Récupère la liste de courses actuelle"""
        return db.execute_query('''
            SELECT * FROM shopping_list 
            ORDER BY checked ASC, category, name
        ''')
    
    def add_item(self, name: str, category: str = 'Divers', quantity: float = 1, unit: str = 'unité') -> Dict:
        """Ajoute un article avec gestion intelligente des quantités si disponible"""
        try:
            if QUANTITY_MANAGER_AVAILABLE:
                result = ingredient_manager.add_or_update_item(
                    name=name,
                    quantity=quantity,
                    unit=unit,
                    category=category
                )
                
                if result['success']:
                    # Mettre à jour les statistiques
                    self._update_frequent_items(name, category)
                    
                    # Analytics
                    self._track_analytics('add_item', {
                        'name': name,
                        'category': category,
                        'quantity': quantity,
                        'unit': unit,
                        'action': result.get('action', 'unknown')
                    })
                
                return result
            else:
                # Fallback simple sans consolidation
                item_id = db.execute_update('''
                    INSERT INTO shopping_list (name, category, quantity, quantity_decimal, unit)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, category, int(quantity) if quantity.is_integer() else quantity, quantity, unit))
                
                self._update_frequent_items(name, category)
                
                return {
                    'success': True,
                    'action': 'created',
                    'item_id': item_id,
                    'message': f'Article ajouté: {name}'
                }
            
        except Exception as e:
            logger.error(f"Erreur ajout article: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_item(self, item_id: int, **kwargs) -> bool:
        """Met à jour un article de la liste"""
        try:
            # Gestion spéciale pour les quantités si disponible
            if 'quantity' in kwargs and QUANTITY_MANAGER_AVAILABLE:
                quantity = kwargs.pop('quantity')
                unit = kwargs.pop('unit', None)
                
                result = ingredient_manager.update_item_quantity(item_id, quantity, unit)
                if not result['success']:
                    return False
            
            # Autres mises à jour
            if kwargs:
                allowed_fields = ['name', 'category', 'price', 'store', 'checked']
                updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
                
                if updates:
                    set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
                    values = list(updates.values()) + [item_id]
                    
                    rows_affected = db.execute_update(f'''
                        UPDATE shopping_list 
                        SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', tuple(values))
                    
                    return rows_affected > 0
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur mise à jour article: {e}")
            return False
    
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
            SELECT id FROM frequent_items WHERE LOWER(name) = LOWER(?)
        ''', (name,))
        
        if existing:
            db.execute_update('''
                UPDATE frequent_items 
                SET usage_count = usage_count + 1, last_used = CURRENT_TIMESTAMP
                WHERE LOWER(name) = LOWER(?)
            ''', (name,))
        else:
            db.execute_update('''
                INSERT INTO frequent_items (name, category)
                VALUES (?, ?)
            ''', (name, category))
    
    def _track_analytics(self, action: str, data: Dict):
        """Enregistre les analytics utilisateur"""
        try:
            db.execute_update('''
                INSERT INTO user_analytics (action, data)
                VALUES (?, ?)
            ''', (action, json.dumps(data)))
        except Exception as e:
            logger.warning(f"Erreur analytics: {e}")

class RecipeManager:
    """Gestionnaire des recettes AMÉLIORÉ"""
    
    @cache_result("recipes_all", 1800)  # Cache 30 minutes
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
                   url: str = None, servings: int = 4, prep_time: int = 30) -> int:
        """Ajoute une nouvelle recette"""
        ingredients_json = json.dumps(ingredients)
        
        recipe_id = db.execute_update('''
            INSERT INTO recipes (name, source, url, ingredients, servings, prep_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, source, url, ingredients_json, servings, prep_time))
        
        # Invalider le cache
        if CACHE_ENABLED:
            try:
                redis_client.delete("recipes_all:*")
            except:
                pass
        
        logger.info(f"Recette ajoutée: {name}")
        return recipe_id
    
    def add_recipe_to_shopping_list(self, recipe_id: int) -> Dict:
        """Ajoute les ingrédients d'une recette à la liste avec consolidation si disponible"""
        try:
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
            
            if QUANTITY_MANAGER_AVAILABLE:
                # Convertir en format attendu par le gestionnaire
                recipe_data = {
                    'name': recipe['name'],
                    'ingredients': [
                        {
                            'name': ing.strip(),
                            'quantity': 1,
                            'unit': 'unité'
                        } for ing in ingredients
                    ]
                }
                
                # Utiliser le gestionnaire intelligent
                result = ingredient_manager.add_recipe_ingredients(recipe_data)
                
                return {
                    'success': result['success'],
                    'recipe_name': result['recipe_name'],
                    'consolidated_count': result['consolidated_count'],
                    'created_count': result['created_count'],
                    'total_count': result['total_ingredients']
                }
            else:
                # Fallback simple
                added_count = 0
                for ingredient in ingredients:
                    try:
                        db.execute_update('''
                            INSERT INTO shopping_list (name, category, quantity, unit, recipe_sources)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (ingredient.strip(), 'Recettes', 1, 'unité', recipe['name']))
                        added_count += 1
                    except:
                        continue
                
                return {
                    'success': True,
                    'recipe_name': recipe['name'],
                    'consolidated_count': 0,
                    'created_count': added_count,
                    'total_count': len(ingredients)
                }
            
        except Exception as e:
            logger.error(f"Erreur ajout recette à la liste: {e}")
            return {'success': False, 'message': str(e)}

# Instances des gestionnaires
shopping_manager = ShoppingListManager()
recipe_manager = RecipeManager()

# ROUTES API CORRIGÉES

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
@limiter.limit("30 per minute")
def add_shopping_item():
    """API: Ajoute un article avec gestion intelligente des quantités"""
    try:
        data = request.get_json()
        name = data.get('name')
        category = data.get('category', 'Divers')
        quantity = float(data.get('quantity', 1))
        unit = data.get('unit', 'unité')
        
        if not name:
            return jsonify({'error': 'Le nom de l\'article est requis'}), 400
        
        result = shopping_manager.add_item(name, category, quantity, unit)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result.get('message', 'Article ajouté'),
                'action': result.get('action', 'created'),
                'item_id': result.get('item_id')
            })
        else:
            return jsonify({'error': result.get('error', 'Erreur inconnue')}), 500
        
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
            return jsonify({'error': 'Article non trouvé ou erreur mise à jour'}), 404
            
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

# ROUTES JOW CORRIGÉES AVEC GESTION D'ERREUR

@app.route('/api/jow/search-recipes', methods=['POST'])
@limiter.limit("10 per minute")
def search_jow_recipes():
    """API: Recherche RÉELLE de recettes si scraper disponible"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        limit = data.get('limit', 8)
        
        if not query.strip():
            return jsonify({'error': 'Query de recherche requise'}), 400
        
        if not SCRAPER_AVAILABLE:
            # Fallback simple si scraper indisponible
            fallback_recipes = [
                {
                    'id': f'fallback_{query}',
                    'name': f'Recette au {query}',
                    'servings': 4,
                    'prepTime': 30,
                    'ingredients': [
                        {'name': query, 'quantity': 300, 'unit': 'g'},
                        {'name': 'huile d\'olive', 'quantity': 2, 'unit': 'cuillère à soupe'}
                    ],
                    'source': 'fallback'
                }
            ]
            
            return jsonify({
                'success': True,
                'data': {
                    'recipes': fallback_recipes,
                    'count': len(fallback_recipes),
                    'query': query,
                    'source': 'fallback',
                    'cached_at': datetime.now().isoformat()
                }
            })
        
        # Vérifier le cache Redis d'abord
        cache_key = f"recipe_search:{query}:{limit}"
        if CACHE_ENABLED:
            try:
                cached_result = redis_client.get(cache_key)
                if cached_result:
                    logger.info(f"🎯 Cache hit pour '{query}'")
                    return jsonify(json.loads(cached_result))
            except:
                pass
        
        # Recherche RÉELLE avec le scraper unifié
        logger.info(f"🔍 Recherche réelle pour '{query}' (limite: {limit})")
        recipes = unified_recipe_scraper.search_recipes(query, limit)
        
        # Mettre en cache le résultat
        response_data = {
            'success': True,
            'data': {
                'recipes': recipes,
                'count': len(recipes),
                'query': query,
                'source': 'real_scraping',
                'cached_at': datetime.now().isoformat()
            }
        }
        
        if CACHE_ENABLED:
            try:
                redis_client.setex(cache_key, 1800, json.dumps(response_data, default=str))  # 30 min
            except:
                pass
        
        logger.info(f"✅ Trouvé {len(recipes)} recettes réelles pour '{query}'")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Erreur recherche Jow: {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur lors de la recherche',
            'details': str(e) if app.debug else None
        }), 500

@app.route('/api/intelligent/consolidate-and-add', methods=['POST'])
@limiter.limit("20 per minute")
def consolidate_and_add_recipe():
    """API: Ajoute une recette avec consolidation intelligente si disponible"""
    try:
        data = request.get_json()
        recipe = data.get('recipe')
        
        if not recipe or not recipe.get('ingredients'):
            return jsonify({
                'success': False,
                'error': 'Recette avec ingrédients requise'
            }), 400
        
        if QUANTITY_MANAGER_AVAILABLE:
            # Utiliser le gestionnaire intelligent
            result = ingredient_manager.add_recipe_ingredients(recipe)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'data': {
                        'recipe_name': result['recipe_name'],
                        'total_ingredients': result['total_ingredients'],
                        'consolidated_count': result['consolidated_count'],
                        'created_count': result['created_count'],
                        'actions': result['actions']
                    },
                    'message': f"Recette {result['recipe_name']} ajoutée avec {result['consolidated_count']} consolidations"
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Erreur lors de l\'ajout',
                    'details': result.get('errors', [])
                }), 500
        else:
            # Fallback simple
            added_count = 0
            for ingredient in recipe.get('ingredients', []):
                try:
                    db.execute_update('''
                        INSERT INTO shopping_list (name, category, quantity, unit, recipe_sources)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        ingredient.get('name', ''),
                        'Recettes',
                        ingredient.get('quantity', 1),
                        ingredient.get('unit', 'unité'),
                        recipe.get('name', 'Recette')
                    ))
                    added_count += 1
                except:
                    continue
            
            return jsonify({
                'success': True,
                'data': {
                    'recipe_name': recipe.get('name', 'Recette'),
                    'total_ingredients': len(recipe.get('ingredients', [])),
                    'consolidated_count': 0,
                    'created_count': added_count,
                    'actions': []
                },
                'message': f"Recette {recipe.get('name', '')} ajoutée ({added_count} ingrédients)"
            })
            
    except Exception as e:
        logger.error(f"Erreur consolidation et ajout: {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur lors de l\'ajout avec consolidation'
        }), 500

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
        prep_time = data.get('prep_time', 30)
        
        if not name or not ingredients:
            return jsonify({'error': 'Nom et ingrédients requis'}), 400
        
        recipe_id = recipe_manager.add_recipe(name, ingredients, source, servings=servings, prep_time=prep_time)
        return jsonify({'id': recipe_id, 'message': 'Recette ajoutée avec succès'})
        
    except Exception as e:
        logger.error(f"Erreur ajout recette: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes/<int:recipe_id>/add-to-list', methods=['POST'])
def add_recipe_to_list(recipe_id):
    """API: Ajoute les ingrédients d'une recette à la liste avec consolidation"""
    try:
        result = recipe_manager.add_recipe_to_shopping_list(recipe_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Erreur ajout recette à la liste: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/frequent-items', methods=['GET'])
def get_frequent_items():
    """API: Récupère les suggestions d'articles fréquents"""
    try:
        items = shopping_manager.get_suggestions()
        return jsonify(items)
    except Exception as e:
        logger.error(f"Erreur récupération suggestions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """API: Récupère les statistiques de l'application"""
    try:
        stats = {
            'shopping_list_items': len(db.execute_query('SELECT id FROM shopping_list WHERE checked = 0')),
            'completed_items': len(db.execute_query('SELECT id FROM shopping_list WHERE checked = 1')),
            'recipes': len(db.execute_query('SELECT id FROM recipes')),
            'frequent_items': len(db.execute_query('SELECT id FROM frequent_items')),
            'cache_status': 'enabled' if CACHE_ENABLED else 'disabled',
            'database_size': os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0,
            'scraping_sources': ['jow.fr', 'marmiton.org'] if SCRAPER_AVAILABLE else ['fallback'],
            'scraper_available': SCRAPER_AVAILABLE,
            'quantity_manager_available': QUANTITY_MANAGER_AVAILABLE
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Erreur récupération stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """API: Vérification de la santé de l'application"""
    try:
        # Test base de données
        db_status = 'ok'
        try:
            db.execute_query('SELECT 1')
        except Exception:
            db_status = 'error'
        
        # Test cache Redis
        cache_status = 'disabled'
        if CACHE_ENABLED:
            try:
                redis_client.ping()
                cache_status = 'ok'
            except:
                cache_status = 'error'
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0-fixed',
            'database': db_status,
            'cache': cache_status,
            'scraping': 'real' if SCRAPER_AVAILABLE else 'fallback',
            'features': {
                'intelligent_quantities': QUANTITY_MANAGER_AVAILABLE,
                'real_scraping': SCRAPER_AVAILABLE,
                'consolidation': QUANTITY_MANAGER_AVAILABLE,
                'caching': CACHE_ENABLED
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# Gestion des erreurs globales
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint non trouvé'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erreur interne du serveur'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Trop de requêtes, veuillez patienter'}), 429

if __name__ == '__main__':
    try:
        logger.info("🚀 Démarrage Smart Shopping Assistant v2.0 SANS LXML")
        logger.info(f"✅ Scraper réel: {'Activé' if SCRAPER_AVAILABLE else 'Désactivé (fallback)'}")
        logger.info(f"✅ Gestion quantités: {'Activée' if QUANTITY_MANAGER_AVAILABLE else 'Désactivée (fallback)'}")
        logger.info(f"✅ Cache Redis: {'Activé' if CACHE_ENABLED else 'Désactivé'}")
        
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
