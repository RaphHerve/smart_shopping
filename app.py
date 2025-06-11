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

# ===== NOUVELLES ROUTES JOW =====

@app.route('/api/jow/search-recipes', methods=['POST'])
def search_jow_recipes():
    """API: Recherche de recettes sur Jow"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        limit = data.get('limit', 10)
        
        if not query.strip():
            return jsonify({'error': 'Query de recherche requise'}), 400
        
        # Recherche via le service Jow
        recipes = jow_service.search_recipes(query, limit)
        
        return jsonify({
            'success': True,
            'data': {
                'recipes': recipes,
                'count': len(recipes),
                'query': query
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur recherche Jow: {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur lors de la recherche sur Jow',
            'details': str(e) if app.debug else None
        }), 500

@app.route('/api/jow/recipe/<recipe_id>', methods=['GET'])
def get_jow_recipe_details(recipe_id):
    """API: Récupère les détails d'une recette Jow"""
    try:
        recipe = jow_service.get_recipe_details(recipe_id)
        
        if recipe:
            return jsonify({
                'success': True,
                'data': recipe
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Recette non trouvée'
            }), 404
            
    except Exception as e:
        logger.error(f"Erreur détails recette Jow {recipe_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur lors de la récupération des détails'
        }), 500

@app.route('/api/intelligent/consolidate-and-add', methods=['POST'])
def consolidate_and_add_recipe():
    """API: Ajoute une recette avec consolidation intelligente"""
    try:
        data = request.get_json()
        recipe = data.get('recipe')
        existing_list = data.get('existingList', [])
        
        if not recipe or not recipe.get('ingredients'):
            return jsonify({
                'success': False,
                'error': 'Recette avec ingrédients requise'
            }), 400
        
        # Préparer les articles à ajouter
        items_to_add = []
        for ingredient in recipe['ingredients']:
            items_to_add.append({
                'name': ingredient['name'],
                'quantity': ingredient.get('quantity', 1),
                'unit': ingredient.get('unit', 'unité'),
                'recipe_id': recipe['id'],
                'recipe_name': recipe['name']
            })
        
        # Ajouter avec consolidation
        result = shopping_manager.add_multiple_items_with_consolidation(items_to_add, existing_list)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'data': result,
                'message': f"Recette {recipe['name']} ajoutée avec consolidation intelligente"
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Erreur lors de la consolidation')
            }), 500
            
    except Exception as e:
        logger.error(f"Erreur consolidation et ajout: {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur lors de l\'ajout avec consolidation'
        }), 500

@app.route('/api/intelligent/consolidate', methods=['POST'])
def consolidate_ingredients():
    """API: Consolidation intelligente des ingrédients (pour compatibilité)"""
    try:
        data = request.get_json()
        recipes = data.get('recipes', [])
        
        from smart_shopping_intelligent import IngredientManager
        manager = IngredientManager()
        
        # Traiter chaque recette
        for recipe in recipes:
            for ingredient in recipe.get('ingredients', []):
                manager.add_ingredient(
                    ingredient['name'],
                    ingredient.get('quantity', 1),
                    ingredient.get('unit', 'unité'),
                    recipe['id'],
                    recipe['name']
                )
        
        consolidated_list = manager.consolidate_shopping_list()
        
        return jsonify({
            'success': True,
            'data': {
                'items': list(consolidated_list.values()),
                'totalItems': len(consolidated_list),
                'consolidatedItems': sum(1 for item in consolidated_list.values() if item.get('recipeCount', 0) > 1)
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur consolidation: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/intelligent/suggestions', methods=['POST'])
def get_intelligent_suggestions():
    """API: Suggestions intelligentes pour un ingrédient"""
    try:
        data = request.get_json()
        ingredient = data.get('ingredient', '')
        
        from smart_shopping_intelligent import IntelligentSuggestionEngine
        suggestion_engine = IntelligentSuggestionEngine()
        
        suggestions = suggestion_engine.generate_suggestions(
            {'normalizedName': ingredient},
            data.get('context', {})
        )
        
        return jsonify({
            'success': True,
            'data': {'suggestions': suggestions}
        })
        
    except Exception as e:
        logger.error(f"Erreur suggestions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
            'frequent_items': len(db.execute_query('SELECT id FROM frequent_items')),
            'jow_recipes_cached': len(db.execute_query('SELECT id FROM jow_recipes_cache')),
            'jow_api_status': 'connected' if JOW_API_KEY else 'simulation'
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
            "<h2>Email de test</h2><p>Votre configuration email fonctionne correctement!</p><p>Smart Shopping v2.0 avec intégration Jow</p>"
        )
        
        if success:
            return jsonify({'message': 'Email de test envoyé avec succès'})
        else:
            return jsonify({'error': 'Échec envoi email - vérifiez la configuration'}), 500
            
    except Exception as e:
        logger.error(f"Erreur test email: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-prices', methods=['POST'])
def check_prices():
    """API: Vérification manuelle des prix (placeholder)"""
    try:
        # TODO: Implémenter la vraie vérification des prix
        return jsonify({
            'success': True,
            'message': 'Vérification des prix lancée',
            'alerts_found': 0
        })
    except Exception as e:
        logger.error(f"Erreur vérification prix: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-promotions', methods=['POST'])
def check_promotions():
    """API: Vérification manuelle des promotions (placeholder)"""
    try:
        # TODO: Implémenter la vraie vérification des promotions
        return jsonify({
            'success': True,
            'message': 'Vérification des promotions lancée',
            'promotions_found': 0
        })
    except Exception as e:
        logger.error(f"Erreur vérification promotions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/price-alerts', methods=['GET'])
def get_price_alerts():
    """API: Récupère les alertes de prix"""
    try:
        alerts = db.execute_query('''
            SELECT * FROM price_alerts 
            ORDER BY created_at DESC 
            LIMIT 20
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
            ORDER BY created_at DESC 
            LIMIT 20
        ''')
        return jsonify(promotions)
    except Exception as e:
        logger.error(f"Erreur récupération promotions: {e}")
        return jsonify({'error': str(e)}), 500

# ===== ROUTES DE SANTÉ ET DEBUG =====

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
        
        # Test API Jow
        jow_status = 'simulation'
        if JOW_API_KEY:
            jow_status = 'configured'
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0',
            'database': db_status,
            'jow_api': jow_status,
            'email_config': 'ok' if GMAIL_EMAIL and GMAIL_APP_PASSWORD else 'missing'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/debug/jow-test', methods=['POST'])
def debug_jow_test():
    """API: Test de l'API Jow pour debug"""
    try:
        data = request.get_json()
        query = data.get('query', 'pâtes')
        
        recipes = jow_service.search_recipes(query, 3)
        
        return jsonify({
            'success': True,
            'query': query,
            'recipes_found': len(recipes),
            'api_key_configured': bool(JOW_API_KEY),
            'recipes': recipes
        })
    except Exception as e:
        logger.error(f"Erreur test Jow: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Gestion des erreurs globales
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint non trouvé'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erreur interne du serveur'}), 500

# Fonction pour initialiser les données de test
def init_sample_data():
    """Initialise quelques données d'exemple si la base est vide"""
    try:
        # Vérifier si on a déjà des données
        existing_recipes = db.execute_query('SELECT COUNT(*) as count FROM recipes')[0]['count']
        
        if existing_recipes == 0:
            logger.info("Initialisation des données d'exemple")
            
            # Ajouter quelques recettes d'exemple
            sample_recipes = [
                {
                    'name': 'Pâtes Carbonara',
                    'ingredients': ['pâtes spaghetti', 'lardons', 'œufs', 'parmesan', 'crème fraîche'],
                    'source': 'Personnalisée'
                },
                {
                    'name': 'Salade César',
                    'ingredients': ['salade romaine', 'poulet', 'parmesan', 'croutons', 'sauce césar'],
                    'source': 'Personnalisée'
                },
                {
                    'name': 'Risotto aux champignons',
                    'ingredients': ['riz arborio', 'champignons', 'bouillon', 'vin blanc', 'parmesan'],
                    'source': 'Personnalisée'
                }
            ]
            
            for recipe_data in sample_recipes:
                recipe_manager.add_recipe(
                    recipe_data['name'],
                    recipe_data['ingredients'],
                    recipe_data['source']
                )
            
            # Ajouter quelques articles fréquents
            frequent_items = [
                ('Pain', 'Boulangerie'),
                ('Lait', 'Produits laitiers'),
                ('Œufs', 'Produits laitiers'),
                ('Tomates', 'Fruits et légumes'),
                ('Pommes', 'Fruits et légumes')
            ]
            
            for name, category in frequent_items:
                db.execute_update('''
                    INSERT OR IGNORE INTO frequent_items (name, category, usage_count)
                    VALUES (?, ?, ?)
                ''', (name, category, 5))
            
            logger.info("Données d'exemple initialisées")
            
    except Exception as e:
        logger.error(f"Erreur initialisation données: {e}")

if __name__ == '__main__':
    try:
        logger.info("🚀 Démarrage Smart Shopping Assistant v2.0 avec Jow")
        
        # Initialiser les données d'exemple si nécessaire
        init_sample_data()
        
        logger.info("🌐 Application accessible sur http://192.168.1.177")
        logger.info(f"🔗 API Jow: {'Configurée' if JOW_API_KEY else 'Mode simulation'}")
        
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
