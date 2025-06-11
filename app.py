#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Shopping Assistant - Application Flask principale avec intégration Jow
Développé pour Raspberry Pi avec toutes les fonctionnalités avancées
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

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, flash
from flask_cors import CORS
from fake_useragent import UserAgent
from dotenv import load_dotenv

# Import du module intelligent
from smart_shopping_intelligent import IngredientManager, JowAPIIntegration, IntelligentSuggestionEngine

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

# Configuration Jow
JOW_API_KEY = os.getenv('JOW_API_KEY')
JOW_BASE_URL = os.getenv('JOW_BASE_URL', 'https://api.jow.fr')

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
            
            # Table pour les recettes Jow en cache
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS jow_recipes_cache (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    data TEXT, -- JSON complet de la recette
                    search_query TEXT,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

class JowAPIService:
    """Service d'intégration avec l'API Jow réelle"""
    
    def __init__(self):
        self.api_key = JOW_API_KEY
        self.base_url = JOW_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Smart-Shopping-Assistant/2.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        if self.api_key:
            self.session.headers['Authorization'] = f'Bearer {self.api_key}'
    
    def search_recipes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche de recettes sur l'API Jow réelle"""
        try:
            # Vérifier d'abord le cache
            cached_results = self._get_cached_recipes(query, limit)
            if cached_results:
                logger.info(f"Recettes trouvées en cache pour '{query}'")
                return cached_results
            
            # Si pas de clé API, utiliser les données de simulation réalistes
            if not self.api_key:
                logger.warning("Pas de clé API Jow configurée, utilisation des données simulées")
                return self._get_realistic_mock_recipes(query, limit)
            
            # Appel à la vraie API Jow
            params = {
                'q': query,
                'limit': limit,
                'type': 'recipe'
            }
            
            response = self.session.get(f'{self.base_url}/search', params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            recipes = self._format_jow_response(data.get('recipes', []))
            
            # Mettre en cache les résultats
            self._cache_recipes(recipes, query)
            
            logger.info(f"Trouvé {len(recipes)} recettes Jow pour '{query}'")
            return recipes
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur API Jow: {e}")
            # Fallback vers données simulées
            return self._get_realistic_mock_recipes(query, limit)
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la recherche Jow: {e}")
            return []
    
    def get_recipe_details(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les détails complets d'une recette"""
        try:
            if not self.api_key:
                return self._get_mock_recipe_details(recipe_id)
            
            response = self.session.get(f'{self.base_url}/recipes/{recipe_id}', timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return self._format_single_recipe(data)
            
        except Exception as e:
            logger.error(f"Erreur récupération recette {recipe_id}: {e}")
            return None
    
    def _get_cached_recipes(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Récupère les recettes en cache"""
        try:
            # Cache valide pendant 1 heure
            cache_limit = datetime.now() - timedelta(hours=1)
            
            cached_recipes = db.execute_query('''
                SELECT data FROM jow_recipes_cache 
                WHERE search_query = ? AND cached_at > ?
                LIMIT ?
            ''', (query.lower(), cache_limit.isoformat(), limit))
            
            if cached_recipes:
                return [json.loads(recipe['data']) for recipe in cached_recipes]
            
            return []
        except Exception as e:
            logger.error(f"Erreur lecture cache: {e}")
            return []
    
    def _cache_recipes(self, recipes: List[Dict[str, Any]], query: str):
        """Met en cache les recettes"""
        try:
            for recipe in recipes:
                db.execute_update('''
                    INSERT OR REPLACE INTO jow_recipes_cache (id, name, data, search_query)
                    VALUES (?, ?, ?, ?)
                ''', (recipe['id'], recipe['name'], json.dumps(recipe), query.lower()))
        except Exception as e:
            logger.error(f"Erreur cache recettes: {e}")
    
    def _format_jow_response(self, jow_recipes: List[Dict]) -> List[Dict[str, Any]]:
        """Formate la réponse de l'API Jow au format Smart Shopping"""
        formatted_recipes = []
        
        for recipe_data in jow_recipes:
            try:
                formatted_recipe = {
                    'id': recipe_data.get('id', f"jow_{recipe_data.get('slug', 'unknown')}"),
                    'name': recipe_data.get('title', recipe_data.get('name', 'Recette sans nom')),
                    'servings': recipe_data.get('servings', recipe_data.get('portions', 4)),
                    'prepTime': recipe_data.get('prep_time', recipe_data.get('preparation_time', 30)),
                    'cookTime': recipe_data.get('cook_time', recipe_data.get('cooking_time')),
                    'difficulty': recipe_data.get('difficulty', 'Moyen'),
                    'image': recipe_data.get('image', recipe_data.get('photo')),
                    'description': recipe_data.get('description', ''),
                    'ingredients': self._format_ingredients(recipe_data.get('ingredients', [])),
                    'instructions': recipe_data.get('instructions', recipe_data.get('steps', [])),
                    'tags': recipe_data.get('tags', []),
                    'nutrition': recipe_data.get('nutrition', {}),
                    'source': 'jow',
                    'url': recipe_data.get('url', ''),
                    'originalData': recipe_data
                }
                formatted_recipes.append(formatted_recipe)
            except Exception as e:
                logger.error(f"Erreur formatage recette {recipe_data}: {e}")
                continue
        
        return formatted_recipes
    
    def _format_single_recipe(self, recipe_data: Dict) -> Dict[str, Any]:
        """Formate une recette unique"""
        return self._format_jow_response([recipe_data])[0] if recipe_data else None
    
    def _format_ingredients(self, jow_ingredients: List[Dict]) -> List[Dict[str, Any]]:
        """Formate les ingrédients de Jow"""
        formatted_ingredients = []
        
        for ingredient in jow_ingredients:
            try:
                # Extraction intelligente de la quantité et unité depuis le texte Jow
                raw_text = ingredient.get('text', ingredient.get('name', ''))
                quantity, unit, name = self._parse_ingredient_text(raw_text)
                
                formatted_ingredient = {
                    'name': name or ingredient.get('name', raw_text),
                    'quantity': quantity or ingredient.get('quantity', 1),
                    'unit': unit or ingredient.get('unit', 'unité'),
                    'optional': ingredient.get('optional', False),
                    'category': ingredient.get('category', ''),
                    'originalText': raw_text
                }
                formatted_ingredients.append(formatted_ingredient)
            except Exception as e:
                logger.error(f"Erreur formatage ingrédient {ingredient}: {e}")
                continue
        
        return formatted_ingredients
    
    def _parse_ingredient_text(self, text: str) -> tuple:
        """Parse le texte d'un ingrédient pour extraire quantité, unité et nom"""
        if not text:
            return None, None, text
        
        # Patterns courants pour les quantités
        patterns = [
            r'^(\d+(?:[.,]\d+)?)\s*(g|kg|ml|l|cl|dl)\s+(.+)$',  # 500g farine
            r'^(\d+(?:[.,]\d+)?)\s+(cuillères?\s+à\s+(?:soupe|café)|c\.?\s*à\s*[sc]\.?)\s+(.+)$',  # 2 cuillères à soupe
            r'^(\d+(?:[.,]\d+)?)\s+(tasses?|verres?|pincées?)\s+(.+)$',  # 1 tasse
            r'^(\d+(?:[.,]\d+)?)\s+(.+)$',  # 3 oeufs
            r'^(.+)',  # Juste le nom
        ]
        
        for pattern in patterns:
            match = re.match(pattern, text.strip(), re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    try:
                        quantity = float(groups[0].replace(',', '.'))
                        unit = groups[1].strip()
                        name = groups[2].strip()
                        return quantity, unit, name
                    except (ValueError, IndexError):
                        continue
                elif len(groups) == 2:
                    try:
                        quantity = float(groups[0].replace(',', '.'))
                        name = groups[1].strip()
                        return quantity, 'unité', name
                    except (ValueError, IndexError):
                        continue
                else:
                    return None, 'unité', groups[0].strip()
        
        return None, 'unité', text
    
    def _get_realistic_mock_recipes(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Données simulées réalistes basées sur de vraies recettes populaires"""
        mock_recipes_db = {
            'pâtes': [
                {
                    'id': 'jow_pates_carbonara',
                    'name': 'Pâtes à la carbonara authentique',
                    'servings': 4,
                    'prepTime': 20,
                    'ingredients': [
                        {'name': 'spaghetti', 'quantity': 400, 'unit': 'g'},
                        {'name': 'lardons fumés', 'quantity': 200, 'unit': 'g'},
                        {'name': 'œufs entiers', 'quantity': 3, 'unit': 'unité'},
                        {'name': 'parmesan râpé', 'quantity': 100, 'unit': 'g'},
                        {'name': 'poivre noir', 'quantity': 1, 'unit': 'pincée'}
                    ],
                    'source': 'jow'
                },
                {
                    'id': 'jow_pates_bolognaise',
                    'name': 'Pâtes bolognaise traditionnelle',
                    'servings': 6,
                    'prepTime': 45,
                    'ingredients': [
                        {'name': 'tagliatelles', 'quantity': 500, 'unit': 'g'},
                        {'name': 'bœuf haché', 'quantity': 400, 'unit': 'g'},
                        {'name': 'tomates pelées', 'quantity': 400, 'unit': 'g'},
                        {'name': 'carotte', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'oignon', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'vin rouge', 'quantity': 100, 'unit': 'ml'}
                    ],
                    'source': 'jow'
                },
                {
                    'id': 'jow_pates_pesto',
                    'name': 'Pâtes au pesto maison',
                    'servings': 4,
                    'prepTime': 15,
                    'ingredients': [
                        {'name': 'penne', 'quantity': 400, 'unit': 'g'},
                        {'name': 'basilic frais', 'quantity': 50, 'unit': 'g'},
                        {'name': 'pignons de pin', 'quantity': 30, 'unit': 'g'},
                        {'name': 'parmesan', 'quantity': 80, 'unit': 'g'},
                        {'name': 'huile d\'olive', 'quantity': 80, 'unit': 'ml'},
                        {'name': 'ail', 'quantity': 2, 'unit': 'gousse'}
                    ],
                    'source': 'jow'
                }
            ],
            'poulet': [
                {
                    'id': 'jow_poulet_curry',
                    'name': 'Curry de poulet au lait de coco',
                    'servings': 4,
                    'prepTime': 35,
                    'ingredients': [
                        {'name': 'blanc de poulet', 'quantity': 600, 'unit': 'g'},
                        {'name': 'lait de coco', 'quantity': 400, 'unit': 'ml'},
                        {'name': 'curry en poudre', 'quantity': 2, 'unit': 'cuillère à soupe'},
                        {'name': 'oignon', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'tomates cerises', 'quantity': 200, 'unit': 'g'},
                        {'name': 'riz basmati', 'quantity': 300, 'unit': 'g'}
                    ],
                    'source': 'jow'
                },
                {
                    'id': 'jow_poulet_roti',
                    'name': 'Poulet rôti aux légumes',
                    'servings': 6,
                    'prepTime': 60,
                    'ingredients': [
                        {'name': 'poulet entier', 'quantity': 1.5, 'unit': 'kg'},
                        {'name': 'pommes de terre', 'quantity': 800, 'unit': 'g'},
                        {'name': 'carottes', 'quantity': 400, 'unit': 'g'},
                        {'name': 'thym', 'quantity': 3, 'unit': 'branche'},
                        {'name': 'huile d\'olive', 'quantity': 3, 'unit': 'cuillère à soupe'}
                    ],
                    'source': 'jow'
                }
            ],
            'salade': [
                {
                    'id': 'jow_salade_cesar',
                    'name': 'Salade César authentique',
                    'servings': 4,
                    'prepTime': 20,
                    'ingredients': [
                        {'name': 'laitue romaine', 'quantity': 2, 'unit': 'unité'},
                        {'name': 'blanc de poulet', 'quantity': 300, 'unit': 'g'},
                        {'name': 'parmesan', 'quantity': 80, 'unit': 'g'},
                        {'name': 'croutons', 'quantity': 100, 'unit': 'g'},
                        {'name': 'anchois', 'quantity': 6, 'unit': 'filet'},
                        {'name': 'mayonnaise', 'quantity': 4, 'unit': 'cuillère à soupe'}
                    ],
                    'source': 'jow'
                },
                {
                    'id': 'jow_salade_quinoa',
                    'name': 'Salade de quinoa aux légumes',
                    'servings': 4,
                    'prepTime': 25,
                    'ingredients': [
                        {'name': 'quinoa', 'quantity': 200, 'unit': 'g'},
                        {'name': 'concombre', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'tomates cerises', 'quantity': 250, 'unit': 'g'},
                        {'name': 'feta', 'quantity': 150, 'unit': 'g'},
                        {'name': 'avocat', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'menthe fraîche', 'quantity': 10, 'unit': 'g'}
                    ],
                    'source': 'jow'
                }
            ]
        }
        
        # Recherche dans la base simulée
        results = []
        query_lower = query.lower()
        
        for category, category_recipes in mock_recipes_db.items():
            if query_lower in category or any(query_lower in recipe['name'].lower() for recipe in category_recipes):
                results.extend(category_recipes)
        
        # Si aucun résultat spécifique, prendre quelques recettes populaires
        if not results:
            all_recipes = []
            for category_recipes in mock_recipes_db.values():
                all_recipes.extend(category_recipes)
            results = all_recipes[:3]
        
        return results[:limit]
    
    def _get_mock_recipe_details(self, recipe_id: str) -> Dict[str, Any]:
        """Détails simulés d'une recette"""
        return {
            'id': recipe_id,
            'name': f'Recette détaillée {recipe_id}',
            'description': 'Description complète de la recette...',
            'instructions': [
                'Étape 1: Préparer les ingrédients',
                'Étape 2: Cuire selon les indications',
                'Étape 3: Servir chaud'
            ],
            'source': 'jow'
        }

# Instance du service Jow
jow_service = JowAPIService()

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
    
    def add_multiple_items_with_consolidation(self, items: List[Dict], existing_list: List[Dict] = None) -> Dict[str, Any]:
        """Ajoute plusieurs articles avec consolidation intelligente"""
        try:
            if existing_list is None:
                existing_list = self.get_shopping_list()
            
            # Utiliser le gestionnaire d'ingrédients pour la consolidation
            ingredient_manager = IngredientManager()
            
            # Ajouter les articles existants
            for existing_item in existing_list:
                if not existing_item.get('checked', False):  # Seulement les non cochés
                    ingredient_manager.add_ingredient(
                        existing_item['name'],
                        existing_item.get('quantity', 1),
                        'unité',
                        'existing',
                        'Liste existante'
                    )
            
            # Ajouter les nouveaux articles
            for item in items:
                ingredient_manager.add_ingredient(
                    item['name'],
                    item.get('quantity', 1),
                    item.get('unit', 'unité'),
                    item.get('recipe_id', 'new'),
                    item.get('recipe_name', 'Nouveau')
                )
            
            # Consolider
            consolidated_list = ingredient_manager.consolidate_shopping_list()
            
            # Compter les consolidations
            consolidated_items = sum(1 for item in consolidated_list.values() if item.get('recipeCount', 0) > 1)
            added_items = len(items)
            
            # Ajouter seulement les nouveaux articles consolidés à la base
            for normalized_name, item_data in consolidated_list.items():
                # Si c'est un nouvel article ou une consolidation
                if not any(existing['name'].lower().strip() == item_data['name'].lower().strip() 
                          for existing in existing_list if not existing.get('checked', False)):
                    self.add_item(
                        item_data['name'],
                        'Recettes',
                        int(item_data['quantity'])
                    )
            
            return {
                'success': True,
                'consolidatedItems': consolidated_items,
                'addedItems': added_items,
                'totalItems': len(consolidated_list)
            }
            
        except Exception as e:
            logger.error(f"Erreur consolidation: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_item(self, item_id: int, **kwargs) -> bool:
        """Met à jour un article de la liste"""
        allowed_fields = ['name', 'category', 'quantity',
