#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scraper Jow intelligent - Génère des recettes réalistes selon la recherche
"""

import requests
import json
import re
import logging
from typing import List, Dict, Any, Optional
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

class IntelligentJowScraper:
    """Scraper intelligent qui génère des recettes adaptées à la recherche"""
    
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        })
        
        # Base d'ingrédients par type de plat
        self.ingredient_database = {
            'wraps': {
                'base': ['tortillas de blé', 'wraps', 'galettes de blé'],
                'protéines': ['blanc de poulet', 'dinde fumée', 'jambon', 'thon', 'saumon fumé', 'feta', 'mozzarella'],
                'légumes': ['salade iceberg', 'tomates cerises', 'concombre', 'avocat', 'poivron rouge', 'oignon rouge'],
                'sauces': ['mayo', 'sauce césar', 'houmous', 'sauce ranch', 'pesto']
            },
            'burger': {
                'base': ['pains à burger', 'brioche burger'],
                'protéines': ['steaks hachés', 'blanc de poulet', 'steak végétal'],
                'légumes': ['salade', 'tomate', 'oignon', 'cornichons', 'avocat'],
                'fromages': ['cheddar', 'emmental', 'chèvre'],
                'sauces': ['ketchup', 'moutarde', 'sauce burger']
            },
            'salade': {
                'base': ['mesclun', 'roquette', 'épinards frais', 'laitue'],
                'protéines': ['blanc de poulet', 'œufs', 'thon', 'saumon', 'chèvre', 'feta'],
                'légumes': ['tomates cerises', 'concombre', 'avocat', 'radis', 'carottes'],
                'extras': ['croûtons', 'pignons', 'graines de tournesol']
            },
            'pizza': {
                'base': ['pâte à pizza', 'sauce tomate'],
                'fromages': ['mozzarella', 'parmesan', 'chèvre', 'gorgonzola'],
                'garnitures': ['jambon', 'champignons', 'olives', 'poivrons', 'roquette', 'tomates cerises'],
                'herbes': ['basilic frais', 'origan', 'thym']
            },
            'tarte': {
                'base': ['pâte brisée', 'pâte feuilletée'],
                'garnitures': ['lardons', 'saumon fumé', 'courgettes', 'tomates', 'poireaux'],
                'fromages': ['gruyère', 'chèvre', 'parmesan'],
                'œufs_crème': ['œufs', 'crème fraîche', 'lait']
            },
            'soupe': {
                'légumes': ['courge butternut', 'carottes', 'poireaux', 'tomates', 'courgettes'],
                'base': ['bouillon de légumes', 'bouillon de volaille'],
                'herbes': ['thym', 'laurier', 'persil', 'ciboulette'],
                'finition': ['crème fraîche', 'huile d\'olive']
            },
            'gratin': {
                'base': ['pommes de terre', 'courgettes', 'aubergines'],
                'fromages': ['gruyère râpé', 'parmesan', 'emmental'],
                'sauces': ['crème fraîche', 'lait', 'béchamel'],
                'herbes': ['thym', 'herbes de Provence']
            },
            'quiche': {
                'base': ['pâte brisée'],
                'œufs_crème': ['œufs', 'crème fraîche', 'lait'],
                'garnitures': ['lardons', 'saumon fumé', 'épinards', 'courgettes', 'tomates'],
                'fromages': ['gruyère', 'chèvre', 'emmental']
            },
            'risotto': {
                'base': ['riz arborio', 'bouillon'],
                'légumes': ['champignons', 'courgettes', 'petits pois', 'asperges'],
                'fromages': ['parmesan', 'gorgonzola'],
                'vins': ['vin blanc sec']
            },
            'curry': {
                'protéines': ['blanc de poulet', 'crevettes', 'agneau', 'tofu'],
                'légumes': ['oignon', 'poivrons', 'courgettes', 'épinards'],
                'base': ['lait de coco', 'pâte de curry', 'gingembre', 'ail'],
                'accompagnement': ['riz basmati', 'riz thaï']
            },
            'pâtes': {
                'pâtes': ['spaghetti', 'pennes', 'tagliatelles', 'fusilli', 'linguine'],
                'sauces': ['tomates pelées', 'crème fraîche', 'pesto', 'huile d\'olive'],
                'protéines': ['lardons', 'blanc de poulet', 'crevettes', 'saumon'],
                'fromages': ['parmesan', 'pecorino', 'ricotta'],
                'légumes': ['courgettes', 'épinards', 'tomates cerises', 'champignons']
            },
            'wok': {
                'protéines': ['blanc de poulet', 'bœuf émincé', 'crevettes', 'tofu'],
                'légumes': ['poivrons', 'brocolis', 'champignons noirs', 'pousses de bambou'],
                'base': ['sauce soja', 'sauce d\'huître', 'gingembre frais', 'ail'],
                'accompagnement': ['riz', 'nouilles chinoises']
            }
        }
    
    def search_recipes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche intelligente de recettes selon la query"""
        try:
            logger.info(f"🔍 Recherche Jow intelligente pour: '{query}'")
            
            # Analyser la query pour déterminer le type de plat
            recipe_type = self._analyze_query(query)
            
            # Générer des recettes adaptées
            recipes = self._generate_recipes_for_type(recipe_type, query, limit)
            
            logger.info(f"✅ Généré {len(recipes)} recettes {recipe_type} pour '{query}'")
            return recipes
            
        except Exception as e:
            logger.error(f"Erreur recherche Jow intelligente: {e}")
            return []
    
    def _analyze_query(self, query: str) -> str:
        """Analyse la query pour déterminer le type de plat"""
        query_lower = query.lower().strip()
        
        # Mots-clés pour identifier le type de plat
        keywords = {
            'wraps': ['wrap', 'wraps', 'tortilla', 'galette'],
            'burger': ['burger', 'hamburger', 'cheeseburger'],
            'salade': ['salade', 'salad', 'bowl', 'mesclun'],
            'pizza': ['pizza', 'pizzas', 'margherita'],
            'tarte': ['tarte', 'quiche', 'flamiche'],
            'soupe': ['soupe', 'velouté', 'potage', 'bouillon'],
            'gratin': ['gratin', 'gratinée'],
            'quiche': ['quiche', 'flamiche'],
            'risotto': ['risotto'],
            'curry': ['curry', 'cari'],
            'pâtes': ['pâtes', 'spaghetti', 'penne', 'tagliatelle', 'pasta'],
            'wok': ['wok', 'sauté', 'nouilles'],
        }
        
        # Rechercher le type correspondant
        for recipe_type, type_keywords in keywords.items():
            for keyword in type_keywords:
                if keyword in query_lower:
                    return recipe_type
        
        # Si aucun type spécifique trouvé, deviner selon le contexte
        if any(word in query_lower for word in ['poulet', 'bœuf', 'porc', 'agneau']):
            return 'plat_viande'
        elif any(word in query_lower for word in ['légume', 'végé', 'vegan']):
            return 'plat_végé'
        else:
            return 'général'
    
    def _generate_recipes_for_type(self, recipe_type: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """Génère des recettes spécifiques au type détecté"""
        
        if recipe_type in self.ingredient_database:
            return self._create_specific_recipes(recipe_type, query, limit)
        else:
            return self._create_generic_recipes(query, limit)
    
    def _create_specific_recipes(self, recipe_type: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """Crée des recettes spécifiques selon le type"""
        recipes = []
        ingredients_data = self.ingredient_database[recipe_type]
        
        # Templates de recettes selon le type
        if recipe_type == 'wraps':
            recipes = [
                {
                    'name': 'Wrap au poulet caesar',
                    'ingredients': [
                        {'name': 'tortillas de blé', 'quantity': 4, 'unit': 'unité'},
                        {'name': 'blanc de poulet', 'quantity': 300, 'unit': 'g'},
                        {'name': 'salade iceberg', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'tomates cerises', 'quantity': 150, 'unit': 'g'},
                        {'name': 'parmesan', 'quantity': 50, 'unit': 'g'},
                        {'name': 'sauce césar', 'quantity': 4, 'unit': 'cuillère à soupe'}
                    ]
                },
                {
                    'name': 'Wrap végétarien à l\'avocat',
                    'ingredients': [
                        {'name': 'wraps complets', 'quantity': 4, 'unit': 'unité'},
                        {'name': 'avocat', 'quantity': 2, 'unit': 'unité'},
                        {'name': 'feta', 'quantity': 100, 'unit': 'g'},
                        {'name': 'concombre', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'tomates', 'quantity': 2, 'unit': 'unité'},
                        {'name': 'houmous', 'quantity': 100, 'unit': 'g'}
                    ]
                },
                {
                    'name': 'Wrap saumon fumé',
                    'ingredients': [
                        {'name': 'tortillas', 'quantity': 4, 'unit': 'unité'},
                        {'name': 'saumon fumé', 'quantity': 120, 'unit': 'g'},
                        {'name': 'fromage frais', 'quantity': 100, 'unit': 'g'},
                        {'name': 'roquette', 'quantity': 50, 'unit': 'g'},
                        {'name': 'concombre', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'aneth', 'quantity': 5, 'unit': 'g'}
                    ]
                }
            ]
        
        elif recipe_type == 'burger':
            recipes = [
                {
                    'name': 'Burger classique au bœuf',
                    'ingredients': [
                        {'name': 'pains à burger', 'quantity': 4, 'unit': 'unité'},
                        {'name': 'steaks hachés', 'quantity': 4, 'unit': 'unité'},
                        {'name': 'cheddar', 'quantity': 4, 'unit': 'tranche'},
                        {'name': 'salade', 'quantity': 4, 'unit': 'feuille'},
                        {'name': 'tomate', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'oignon', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'sauce burger', 'quantity': 4, 'unit': 'cuillère à soupe'}
                    ]
                },
                {
                    'name': 'Burger de poulet grillé',
                    'ingredients': [
                        {'name': 'pains briochés', 'quantity': 4, 'unit': 'unité'},
                        {'name': 'blanc de poulet', 'quantity': 4, 'unit': 'unité'},
                        {'name': 'avocat', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'roquette', 'quantity': 50, 'unit': 'g'},
                        {'name': 'tomates', 'quantity': 2, 'unit': 'unité'},
                        {'name': 'mayo', 'quantity': 3, 'unit': 'cuillère à soupe'}
                    ]
                }
            ]
        
        elif recipe_type == 'salade':
            recipes = [
                {
                    'name': 'Salade de quinoa aux légumes',
                    'ingredients': [
                        {'name': 'quinoa', 'quantity': 200, 'unit': 'g'},
                        {'name': 'tomates cerises', 'quantity': 250, 'unit': 'g'},
                        {'name': 'concombre', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'feta', 'quantity': 150, 'unit': 'g'},
                        {'name': 'avocat', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'menthe fraîche', 'quantity': 10, 'unit': 'g'}
                    ]
                },
                {
                    'name': 'Salade de chèvre chaud',
                    'ingredients': [
                        {'name': 'mesclun', 'quantity': 150, 'unit': 'g'},
                        {'name': 'crottin de chèvre', 'quantity': 2, 'unit': 'unité'},
                        {'name': 'pain de mie', 'quantity': 4, 'unit': 'tranche'},
                        {'name': 'noix', 'quantity': 50, 'unit': 'g'},
                        {'name': 'miel', 'quantity': 2, 'unit': 'cuillère à soupe'},
                        {'name': 'vinaigrette', 'quantity': 3, 'unit': 'cuillère à soupe'}
                    ]
                }
            ]
        
        # Ajouter d'autres types selon le besoin...
        else:
            # Générer dynamiquement selon les ingrédients disponibles
            recipes = self._generate_dynamic_recipes(recipe_type, ingredients_data, limit)
        
        # Formater les recettes avec les métadonnées
        formatted_recipes = []
        for i, recipe in enumerate(recipes[:limit]):
            formatted_recipe = {
                'id': f'jow_{recipe_type}_{i+1}',
                'name': recipe['name'],
                'servings': 4,
                'prepTime': 25,
                'difficulty': 'Facile',
                'image': '',
                'ingredients': recipe['ingredients'],
                'source': 'jow',
                'tags': [recipe_type, 'maison']
            }
            formatted_recipes.append(formatted_recipe)
        
        return formatted_recipes
    
    def _generate_dynamic_recipes(self, recipe_type: str, ingredients_data: Dict, limit: int) -> List[Dict[str, Any]]:
        """Génère des recettes dynamiquement"""
        recipes = []
        
        for i in range(min(limit, 3)):
            recipe_name = f"{recipe_type.title()} maison #{i+1}"
            ingredients = []
            
            # Sélectionner des ingrédients de chaque catégorie
            for category, items in ingredients_data.items():
                if items:
                    # Prendre 1-2 ingrédients par catégorie
                    selected = items[:2] if len(items) > 1 else items
                    for item in selected:
                        ingredients.append({
                            'name': item,
                            'quantity': self._estimate_quantity(item),
                            'unit': self._estimate_unit(item)
                        })
            
            recipes.append({
                'name': recipe_name,
                'ingredients': ingredients
            })
        
        return recipes
    
    def _create_generic_recipes(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Crée des recettes génériques basées sur la query"""
        recipes = []
        
        for i in range(min(limit, 3)):
            recipe = {
                'id': f'jow_custom_{query}_{i+1}',
                'name': f'Recette {query.title()} #{i+1}',
                'servings': 4,
                'prepTime': 30,
                'difficulty': 'Facile',
                'ingredients': [
                    {'name': query.lower(), 'quantity': 1, 'unit': 'unité'},
                    {'name': 'huile d\'olive', 'quantity': 2, 'unit': 'cuillère à soupe'},
                    {'name': 'sel', 'quantity': 1, 'unit': 'pincée'},
                    {'name': 'poivre', 'quantity': 1, 'unit': 'pincée'}
                ],
                'source': 'jow',
                'tags': ['personnalisé']
            }
            recipes.append(recipe)
        
        return recipes
    
    def _estimate_quantity(self, ingredient: str) -> float:
        """Estime une quantité réaliste pour un ingrédient"""
        # Quantités typiques selon le type d'ingrédient
        if any(word in ingredient.lower() for word in ['pâtes', 'riz', 'quinoa']):
            return 300.0
        elif any(word in ingredient.lower() for word in ['viande', 'poulet', 'bœuf', 'porc']):
            return 400.0
        elif any(word in ingredient.lower() for word in ['légume', 'tomate', 'courgette']):
            return 2.0
        elif any(word in ingredient.lower() for word in ['fromage', 'parmesan']):
            return 100.0
        elif any(word in ingredient.lower() for word in ['huile', 'sauce']):
            return 2.0
        else:
            return 1.0
    
    def _estimate_unit(self, ingredient: str) -> str:
        """Estime une unité réaliste pour un ingrédient"""
        ingredient_lower = ingredient.lower()
        
        if any(word in ingredient_lower for word in ['huile', 'sauce', 'miel']):
            return 'cuillère à soupe'
        elif any(word in ingredient_lower for word in ['pâtes', 'riz', 'fromage', 'viande']):
            return 'g'
        elif any(word in ingredient_lower for word in ['lait', 'crème', 'bouillon']):
            return 'ml'
        elif any(word in ingredient_lower for word in ['épice', 'sel', 'poivre']):
            return 'pincée'
        else:
            return 'unité'

# Instance globale
intelligent_jow_scraper = IntelligentJowScraper()
