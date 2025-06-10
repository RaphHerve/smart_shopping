#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Shopping - Module d'extension intelligent
Fonctionnalités avancées de gestion des recettes et consolidation
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

class IngredientManager:
    """Gestionnaire intelligent des ingrédients avec détection de doublons"""
    
    def __init__(self):
        self.ingredients = {}
        self.recipes = {}
        
    def normalize_ingredient_name(self, name: str) -> str:
        """Normalise le nom d'un ingrédient pour détecter les doublons"""
        name = name.lower().strip()
        # Suppression des accents
        accents = {
            'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
            'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
            'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
            'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
            'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
            'ç': 'c', 'ñ': 'n'
        }
        
        for accent, normal in accents.items():
            name = name.replace(accent, normal)
        
        # Suppression de la ponctuation et espaces multiples
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', ' ', name)
        
        return name.strip()
    
    def convert_to_standard_unit(self, quantity: float, unit: str) -> Dict[str, Any]:
        """Convertit les unités en unité standard"""
        conversions = {
            # Poids
            'kg': {'factor': 1000, 'standard': 'g'},
            'g': {'factor': 1, 'standard': 'g'},
            'mg': {'factor': 0.001, 'standard': 'g'},
            
            # Volume
            'l': {'factor': 1000, 'standard': 'ml'},
            'ml': {'factor': 1, 'standard': 'ml'},
            'cl': {'factor': 10, 'standard': 'ml'},
            'dl': {'factor': 100, 'standard': 'ml'},
            
            # Cuisine
            'cuillère à soupe': {'factor': 15, 'standard': 'ml'},
            'cuillère à café': {'factor': 5, 'standard': 'ml'},
            'c. à soupe': {'factor': 15, 'standard': 'ml'},
            'c. à café': {'factor': 5, 'standard': 'ml'},
            'tasse': {'factor': 250, 'standard': 'ml'},
            'verre': {'factor': 200, 'standard': 'ml'},
            
            # Unités
            'pièce': {'factor': 1, 'standard': 'unité'},
            'unité': {'factor': 1, 'standard': 'unité'},
            'tranche': {'factor': 1, 'standard': 'unité'},
            'gousse': {'factor': 1, 'standard': 'unité'}
        }
        
        unit_lower = unit.lower().strip()
        if unit_lower in conversions:
            conv = conversions[unit_lower]
            return {
                'quantity': quantity * conv['factor'],
                'unit': conv['standard']
            }
        
        return {'quantity': quantity, 'unit': unit}
    
    def add_ingredient(self, name: str, quantity: float, unit: str, recipe_id: str, recipe_name: str):
        """Ajoute un ingrédient avec gestion intelligente des doublons"""
        normalized_name = self.normalize_ingredient_name(name)
        converted = self.convert_to_standard_unit(quantity, unit)
        
        if normalized_name not in self.ingredients:
            self.ingredients[normalized_name] = {
                'originalName': name,
                'normalizedName': normalized_name,
                'totalQuantity': 0,
                'unit': converted['unit'],
                'recipes': [],
                'recipeCount': 0
            }
        
        ingredient = self.ingredients[normalized_name]
        ingredient['totalQuantity'] += converted['quantity']
        
        # Ajouter la recette si pas déjà présente
        recipe_info = {
            'recipeId': recipe_id,
            'recipeName': recipe_name,
            'quantity': converted['quantity'],
            'unit': converted['unit']
        }
        
        if not any(r['recipeId'] == recipe_id for r in ingredient['recipes']):
            ingredient['recipes'].append(recipe_info)
            ingredient['recipeCount'] = len(ingredient['recipes'])
    
    def consolidate_shopping_list(self) -> Dict[str, Any]:
        """Génère la liste de courses consolidée"""
        consolidated = {}
        
        for normalized_name, ingredient in self.ingredients.items():
            recipe_names = [r['recipeName'] for r in ingredient['recipes']]
            
            consolidated[normalized_name] = {
                'name': ingredient['originalName'],
                'quantity': round(ingredient['totalQuantity'], 2),
                'unit': ingredient['unit'],
                'recipeCount': ingredient['recipeCount'],
                'recipes': recipe_names,
                'isConsolidated': ingredient['recipeCount'] > 1,
                'details': f"Présent dans {ingredient['recipeCount']} recette(s): {', '.join(recipe_names)}" if ingredient['recipeCount'] > 1 else f"Recette: {recipe_names[0]}"
            }
        
        return consolidated

class JowAPIIntegration:
    """Intégration avec l'API Jow (simulation pour l'instant)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = 'https://api.jow.fr'  # URL hypothétique
        
    def search_recipes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche de recettes (version simulation)"""
        # Pour l'instant, retourner des données simulées
        # À remplacer par de vrais appels API quand disponible
        
        mock_recipes = [
            {
                'id': 'jow_recipe_1',
                'name': f'Recette {query} #1',
                'servings': 4,
                'prepTime': 30,
                'ingredients': [
                    {'name': f'{query} principal', 'quantity': 500, 'unit': 'g'},
                    {'name': 'oignon', 'quantity': 1, 'unit': 'unité'},
                    {'name': 'ail', 'quantity': 2, 'unit': 'gousse'},
                    {'name': 'huile olive', 'quantity': 2, 'unit': 'cuillère à soupe'}
                ],
                'source': 'jow'
            },
            {
                'id': 'jow_recipe_2',
                'name': f'Salade de {query}',
                'servings': 2,
                'prepTime': 15,
                'ingredients': [
                    {'name': query, 'quantity': 300, 'unit': 'g'},
                    {'name': 'tomates cerises', 'quantity': 200, 'unit': 'g'},
                    {'name': 'mozzarella', 'quantity': 125, 'unit': 'g'},
                    {'name': 'basilic', 'quantity': 10, 'unit': 'g'}
                ],
                'source': 'jow'
            },
            {
                'id': 'jow_recipe_3',
                'name': f'Gratin de {query}',
                'servings': 6,
                'prepTime': 45,
                'ingredients': [
                    {'name': query, 'quantity': 800, 'unit': 'g'},
                    {'name': 'crème fraîche', 'quantity': 200, 'unit': 'ml'},
                    {'name': 'gruyère', 'quantity': 150, 'unit': 'g'},
                    {'name': 'muscade', 'quantity': 1, 'unit': 'pincée'}
                ],
                'source': 'jow'
            }
        ]
        
        # Filtrer par requête et limiter
        filtered_recipes = [r for r in mock_recipes if query.lower() in r['name'].lower()]
        return filtered_recipes[:limit]

class IntelligentSuggestionEngine:
    """Moteur de suggestions intelligentes"""
    
    def __init__(self):
        self.seasonal_ingredients = self._init_seasonal_data()
        self.nutritional_alternatives = self._init_nutritional_data()
        
    def _init_seasonal_data(self) -> Dict[int, List[str]]:
        """Initialise les données saisonnières"""
        return {
            1: ['chou', 'poireau', 'carotte', 'pomme', 'orange', 'endive'],
            2: ['chou', 'endive', 'carotte', 'pomme', 'orange', 'brocoli'],
            3: ['épinard', 'radis', 'carotte', 'pomme', 'asperge'],
            4: ['asperge', 'radis', 'épinard', 'fraise', 'petit pois'],
            5: ['asperge', 'radis', 'épinard', 'fraise', 'petit pois', 'artichaut'],
            6: ['tomate', 'courgette', 'aubergine', 'fraise', 'cerise', 'abricot'],
            7: ['tomate', 'courgette', 'aubergine', 'pêche', 'abricot', 'melon'],
            8: ['tomate', 'courgette', 'aubergine', 'pêche', 'melon', 'prune'],
            9: ['potiron', 'champignon', 'raisin', 'pomme', 'poire'],
            10: ['potiron', 'champignon', 'châtaigne', 'pomme', 'poire'],
            11: ['chou', 'poireau', 'carotte', 'pomme', 'poire', 'clémentine'],
            12: ['chou', 'poireau', 'carotte', 'pomme', 'orange', 'mandarine']
        }
    
    def _init_nutritional_data(self) -> Dict[str, List[str]]:
        """Initialise les alternatives nutritionnelles"""
        return {
            'pomme': ['poire', 'pêche', 'abricot'],
            'tomate': ['poivron rouge', 'aubergine', 'courgette'],
            'carotte': ['betterave', 'panais', 'navet'],
            'épinard': ['roquette', 'mâche', 'cresson'],
            'lait': ['lait d\'amande', 'lait de soja', 'lait d\'avoine'],
            'beurre': ['huile olive', 'margarine', 'huile coco'],
            'sucre': ['miel', 'sirop érable', 'sucre coco']
        }
    
    def generate_suggestions(self, ingredient: Dict[str, str], context: Dict[str, Any] = None) -> List[Dict[str, str]]:
        """Génère des suggestions intelligentes"""
        suggestions = []
        ingredient_name = ingredient.get('normalizedName', '').lower()
        current_month = datetime.now().month
        
        # Suggestions saisonnières
        seasonal_items = self.seasonal_ingredients.get(current_month, [])
        for item in seasonal_items:
            if item in ingredient_name or ingredient_name in item:
                suggestions.append({
                    'type': 'seasonal',
                    'suggestion': item,
                    'reason': 'Produit de saison - meilleur goût et prix'
                })
        
        # Suggestions nutritionnelles
        for base_ingredient, alternatives in self.nutritional_alternatives.items():
            if base_ingredient in ingredient_name:
                for alt in alternatives[:2]:  # Limiter à 2 alternatives
                    suggestions.append({
                        'type': 'nutritional',
                        'suggestion': alt,
                        'reason': f'Alternative nutritionnelle à {base_ingredient}'
                    })
        
        # Suggestions économiques (simulation)
        if context and context.get('budget') == 'économique':
            suggestions.append({
                'type': 'economic',
                'suggestion': f'Version économique {ingredient_name}',
                'reason': 'Option moins chère disponible'
            })
        
        return suggestions[:5]  # Limiter à 5 suggestions

def test_intelligent_system():
    """Fonction de test du système intelligent"""
    print("🧪 Test du système intelligent Smart Shopping")
    
    # Test du gestionnaire d'ingrédients
    manager = IngredientManager()
    
    # Ajouter des ingrédients de différentes recettes
    manager.add_ingredient('pâtes', 400, 'g', 'recipe1', 'Carbonara')
    manager.add_ingredient('Pâtes spaghetti', 300, 'g', 'recipe2', 'Bolognaise')
    manager.add_ingredient('lait', 0.5, 'l', 'recipe3', 'Béchamel')
    manager.add_ingredient('Lait entier', 200, 'ml', 'recipe4', 'Crêpes')
    
    # Consolidation
    consolidated = manager.consolidate_shopping_list()
    
    print(f"✅ {len(consolidated)} ingrédients consolidés")
    for name, item in consolidated.items():
        if item['isConsolidated']:
            print(f"  🔄 {item['name']}: {item['quantity']} {item['unit']} (consolidé de {item['recipeCount']} recettes)")
        else:
            print(f"  📝 {item['name']}: {item['quantity']} {item['unit']}")
    
    # Test API Jow
    jow_api = JowAPIIntegration()
    recipes = jow_api.search_recipes('pâtes', 2)
    print(f"✅ {len(recipes)} recettes trouvées via API Jow")
    
    # Test suggestions
    suggestion_engine = IntelligentSuggestionEngine()
    suggestions = suggestion_engine.generate_suggestions({'normalizedName': 'tomate'})
    print(f"✅ {len(suggestions)} suggestions générées")
    
    print("🎉 Tous les tests passés !")

if __name__ == '__main__':
    test_intelligent_system()
