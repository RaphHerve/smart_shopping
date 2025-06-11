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
        
        # Normalisation des variantes courantes
        replacements = {
            'pates': 'pâtes',
            'spaghettis': 'pâtes',
            'spaghetti': 'pâtes',
            'tagliatelles': 'pâtes',
            'penne': 'pâtes',
            'fusilli': 'pâtes',
            'macaroni': 'pâtes',
            'tomates': 'tomate',
            'pommes de terre': 'pomme de terre',
            'patates': 'pomme de terre',
            'oeufs': 'œuf',
            'oignon': 'oignon',
            'oignons': 'oignon'
        }
        
        for variant, canonical in replacements.items():
            if variant in name:
                name = name.replace(variant, canonical)
        
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
            
            # Mesures cuisine
            'cuillère à soupe': {'factor': 15, 'standard': 'ml'},
            'cuillère à café': {'factor': 5, 'standard': 'ml'},
            'c. à soupe': {'factor': 15, 'standard': 'ml'},
            'c. à café': {'factor': 5, 'standard': 'ml'},
            'cuilleres a soupe': {'factor': 15, 'standard': 'ml'},
            'cuilleres a cafe': {'factor': 5, 'standard': 'ml'},
            'tasse': {'factor': 250, 'standard': 'ml'},
            'verre': {'factor': 200, 'standard': 'ml'},
            
            # Unités
            'pièce': {'factor': 1, 'standard': 'unité'},
            'piece': {'factor': 1, 'standard': 'unité'},
            'unité': {'factor': 1, 'standard': 'unité'},
            'unite': {'factor': 1, 'standard': 'unité'},
            'tranche': {'factor': 1, 'standard': 'unité'},
            'gousse': {'factor': 1, 'standard': 'unité'},
            'branche': {'factor': 1, 'standard': 'unité'},
            'pincée': {'factor': 1, 'standard': 'unité'},
            'pincee': {'factor': 1, 'standard': 'unité'}
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
        
        # Vérifier si cette recette n'est pas déjà ajoutée
        if not any(r['recipeId'] == recipe_id for r in ingredient['recipes']):
            ingredient['recipes'].append(recipe_info)
            ingredient['recipeCount'] = len(ingredient['recipes'])
        else:
            # Si la recette existe déjà, additionner les quantités
            for recipe in ingredient['recipes']:
                if recipe['recipeId'] == recipe_id:
                    recipe['quantity'] += converted['quantity']
                    break
    
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
                'details': self._format_recipe_details(ingredient['recipeCount'], recipe_names)
            }
        
        return consolidated
    
    def _format_recipe_details(self, recipe_count: int, recipe_names: List[str]) -> str:
        """Formate les détails des recettes pour l'affichage"""
        if recipe_count > 1:
            return f"Présent dans {recipe_count} recettes: {', '.join(recipe_names)}"
        else:
            return f"Recette: {recipe_names[0]}" if recipe_names else "Recette inconnue"

class JowAPIIntegration:
    """Intégration avec l'API Jow"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = 'https://api.jow.fr'  # URL hypothétique
        
    def search_recipes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche de recettes (version simulation réaliste)"""
        # Base de données de recettes réalistes
        recipes_database = {
            'pâtes': [
                {
                    'id': 'jow_pates_carbonara_1',
                    'name': 'Pâtes à la carbonara authentique',
                    'servings': 4,
                    'prepTime': 20,
                    'ingredients': [
                        {'name': 'spaghetti', 'quantity': 400, 'unit': 'g'},
                        {'name': 'lardons fumés', 'quantity': 200, 'unit': 'g'},
                        {'name': 'œufs entiers', 'quantity': 3, 'unit': 'unité'},
                        {'name': 'parmesan râpé', 'quantity': 100, 'unit': 'g'},
                        {'name': 'poivre noir moulu', 'quantity': 1, 'unit': 'pincée'}
                    ],
                    'source': 'jow'
                },
                {
                    'id': 'jow_pates_bolognaise_1',
                    'name': 'Pâtes bolognaise traditionnelle',
                    'servings': 6,
                    'prepTime': 45,
                    'ingredients': [
                        {'name': 'tagliatelles', 'quantity': 500, 'unit': 'g'},
                        {'name': 'bœuf haché', 'quantity': 400, 'unit': 'g'},
                        {'name': 'tomates pelées', 'quantity': 400, 'unit': 'g'},
                        {'name': 'carotte', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'oignon', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'vin rouge', 'quantity': 100, 'unit': 'ml'},
                        {'name': 'huile d\'olive', 'quantity': 2, 'unit': 'cuillère à soupe'}
                    ],
                    'source': 'jow'
                },
                {
                    'id': 'jow_pates_pesto_1',
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
                    'id': 'jow_poulet_curry_1',
                    'name': 'Curry de poulet au lait de coco',
                    'servings': 4,
                    'prepTime': 35,
                    'ingredients': [
                        {'name': 'blanc de poulet', 'quantity': 600, 'unit': 'g'},
                        {'name': 'lait de coco', 'quantity': 400, 'unit': 'ml'},
                        {'name': 'curry en poudre', 'quantity': 2, 'unit': 'cuillère à soupe'},
                        {'name': 'oignon', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'tomates cerises', 'quantity': 200, 'unit': 'g'},
                        {'name': 'riz basmati', 'quantity': 300, 'unit': 'g'},
                        {'name': 'coriandre fraîche', 'quantity': 10, 'unit': 'g'}
                    ],
                    'source': 'jow'
                },
                {
                    'id': 'jow_poulet_roti_1',
                    'name': 'Poulet rôti aux légumes de saison',
                    'servings': 6,
                    'prepTime': 75,
                    'ingredients': [
                        {'name': 'poulet entier', 'quantity': 1.5, 'unit': 'kg'},
                        {'name': 'pommes de terre', 'quantity': 800, 'unit': 'g'},
                        {'name': 'carottes', 'quantity': 400, 'unit': 'g'},
                        {'name': 'thym frais', 'quantity': 3, 'unit': 'branche'},
                        {'name': 'huile d\'olive', 'quantity': 3, 'unit': 'cuillère à soupe'},
                        {'name': 'beurre', 'quantity': 30, 'unit': 'g'}
                    ],
                    'source': 'jow'
                }
            ],
            'salade': [
                {
                    'id': 'jow_salade_cesar_1',
                    'name': 'Salade César authentique',
                    'servings': 4,
                    'prepTime': 20,
                    'ingredients': [
                        {'name': 'laitue romaine', 'quantity': 2, 'unit': 'unité'},
                        {'name': 'blanc de poulet', 'quantity': 300, 'unit': 'g'},
                        {'name': 'parmesan', 'quantity': 80, 'unit': 'g'},
                        {'name': 'croutons', 'quantity': 100, 'unit': 'g'},
                        {'name': 'anchois', 'quantity': 6, 'unit': 'filet'},
                        {'name': 'mayonnaise', 'quantity': 4, 'unit': 'cuillère à soupe'},
                        {'name': 'citron', 'quantity': 0.5, 'unit': 'unité'}
                    ],
                    'source': 'jow'
                },
                {
                    'id': 'jow_salade_quinoa_1',
                    'name': 'Salade de quinoa aux légumes frais',
                    'servings': 4,
                    'prepTime': 25,
                    'ingredients': [
                        {'name': 'quinoa', 'quantity': 200, 'unit': 'g'},
                        {'name': 'concombre', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'tomates cerises', 'quantity': 250, 'unit': 'g'},
                        {'name': 'feta', 'quantity': 150, 'unit': 'g'},
                        {'name': 'avocat', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'menthe fraîche', 'quantity': 10, 'unit': 'g'},
                        {'name': 'huile d\'olive', 'quantity': 3, 'unit': 'cuillère à soupe'}
                    ],
                    'source': 'jow'
                }
            ],
            'soupe': [
                {
                    'id': 'jow_soupe_tomate_1',
                    'name': 'Soupe de tomates fraîches au basilic',
                    'servings': 4,
                    'prepTime': 30,
                    'ingredients': [
                        {'name': 'tomates mûres', 'quantity': 1, 'unit': 'kg'},
                        {'name': 'oignon', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'ail', 'quantity': 3, 'unit': 'gousse'},
                        {'name': 'basilic frais', 'quantity': 20, 'unit': 'g'},
                        {'name': 'bouillon de légumes', 'quantity': 500, 'unit': 'ml'},
                        {'name': 'crème fraîche', 'quantity': 100, 'unit': 'ml'}
                    ],
                    'source': 'jow'
                }
            ],
            'dessert': [
                {
                    'id': 'jow_tiramisu_1',
                    'name': 'Tiramisu traditionnel italien',
                    'servings': 8,
                    'prepTime': 30,
                    'ingredients': [
                        {'name': 'mascarpone', 'quantity': 500, 'unit': 'g'},
                        {'name': 'œufs', 'quantity': 6, 'unit': 'unité'},
                        {'name': 'sucre', 'quantity': 150, 'unit': 'g'},
                        {'name': 'biscuits boudoirs', 'quantity': 300, 'unit': 'g'},
                        {'name': 'café fort', 'quantity': 300, 'unit': 'ml'},
                        {'name': 'cacao en poudre', 'quantity': 2, 'unit': 'cuillère à soupe'},
                        {'name': 'amaretto', 'quantity': 50, 'unit': 'ml'}
                    ],
                    'source': 'jow'
                }
            ]
        }
        
        # Recherche intelligente dans la base
        results = []
        query_lower = query.lower().strip()
        
        # Recherche directe par catégorie
        for category, category_recipes in recipes_database.items():
            if query_lower in category:
                results.extend(category_recipes)
        
        # Recherche dans les noms de recettes
        if not results:
            for category_recipes in recipes_database.values():
                for recipe in category_recipes:
                    if query_lower in recipe['name'].lower():
                        results.append(recipe)
        
        # Recherche dans les ingrédients
        if not results:
            for category_recipes in recipes_database.values():
                for recipe in category_recipes:
                    for ingredient in recipe['ingredients']:
                        if query_lower in ingredient['name'].lower():
                            if recipe not in results:
                                results.append(recipe)
                            break
        
        # Si toujours pas de résultats, prendre quelques recettes populaires
        if not results:
            popular_recipes = []
            for category_recipes in recipes_database.values():
                popular_recipes.extend(category_recipes[:1])  # Une par catégorie
            results = popular_recipes[:3]
        
        return results[:limit]

class IntelligentSuggestionEngine:
    """Moteur de suggestions intelligentes"""
    
    def __init__(self):
        self.seasonal_ingredients = self._init_seasonal_data()
        self.nutritional_alternatives = self._init_nutritional_data()
        self.price_categories = self._init_price_categories()
        
    def _init_seasonal_data(self) -> Dict[int, List[str]]:
        """Initialise les données saisonnières par mois"""
        return {
            1: ['chou', 'poireau', 'carotte', 'pomme', 'orange', 'endive', 'épinard'],
            2: ['chou', 'endive', 'carotte', 'pomme', 'orange', 'brocoli', 'poireau'],
            3: ['épinard', 'radis', 'carotte', 'pomme', 'asperge', 'artichaut'],
            4: ['asperge', 'radis', 'épinard', 'fraise', 'petit pois', 'artichaut'],
            5: ['asperge', 'radis', 'épinard', 'fraise', 'petit pois', 'artichaut', 'rhubarbe'],
            6: ['tomate', 'courgette', 'aubergine', 'fraise', 'cerise', 'abricot', 'concombre'],
            7: ['tomate', 'courgette', 'aubergine', 'pêche', 'abricot', 'melon', 'basilic'],
            8: ['tomate', 'courgette', 'aubergine', 'pêche', 'melon', 'prune', 'maïs'],
            9: ['potiron', 'champignon', 'raisin', 'pomme', 'poire', 'figue'],
            10: ['potiron', 'champignon', 'châtaigne', 'pomme', 'poire', 'coing'],
            11: ['chou', 'poireau', 'carotte', 'pomme', 'poire', 'clémentine', 'épinard'],
            12: ['chou', 'poireau', 'carotte', 'pomme', 'orange', 'mandarine', 'endive']
        }
    
    def _init_nutritional_data(self) -> Dict[str, List[str]]:
        """Initialise les alternatives nutritionnelles"""
        return {
            'pomme': ['poire', 'pêche', 'abricot', 'prune'],
            'tomate': ['poivron rouge', 'aubergine', 'courgette'],
            'carotte': ['betterave', 'panais', 'navet'],
            'épinard': ['roquette', 'mâche', 'cresson', 'blette'],
            'lait': ['lait d\'amande', 'lait de soja', 'lait d\'avoine'],
            'beurre': ['huile olive', 'margarine', 'huile coco'],
            'sucre': ['miel', 'sirop érable', 'sucre coco'],
            'pâtes': ['riz', 'quinoa', 'boulgour'],
            'bœuf': ['porc', 'agneau', 'dinde'],
            'poulet': ['dinde', 'lapin', 'porc'],
            'fromage': ['yaourt grec', 'ricotta', 'cottage cheese']
        }
    
    def _init_price_categories(self) -> Dict[str, str]:
        """Initialise les catégories de prix"""
        return {
            'économique': ['marque distributeur', 'premiers prix', 'promotion'],
            'moyen': ['marque nationale', 'qualité standard'],
            'premium': ['bio', 'label rouge', 'artisanal', 'terroir']
        }
    
    def generate_suggestions(self, ingredient: Dict[str, str], context: Dict[str, Any] = None) -> List[Dict[str, str]]:
        """Génère des suggestions intelligentes pour un ingrédient"""
        suggestions = []
        ingredient_name = ingredient.get('normalizedName', '').lower()
        current_month = datetime.now().month
        context = context or {}
        
        # Suggestions saisonnières
        seasonal_items = self.seasonal_ingredients.get(current_month, [])
        for item in seasonal_items:
            if self._is_similar_ingredient(ingredient_name, item):
                suggestions.append({
                    'type': 'seasonal',
                    'suggestion': item,
                    'reason': f'Produit de saison ({self._get_month_name(current_month)})'
                })
        
        # Suggestions nutritionnelles
        for base_ingredient, alternatives in self.nutritional_alternatives.items():
            if base_ingredient in ingredient_name or ingredient_name in base_ingredient:
                for alt in alternatives[:2]:  # Limiter à 2 alternatives
                    suggestions.append({
                        'type': 'nutritional',
                        'suggestion': alt,
                        'reason': f'Alternative nutritionnelle à {base_ingredient}'
                    })
        
        # Suggestions économiques
        budget = context.get('budget', 'moyen')
        if budget == 'économique':
            suggestions.append({
                'type': 'economic',
                'suggestion': f'{ingredient_name} marque distributeur',
                'reason': 'Option économique (30-40% moins cher)'
            })
        
        # Suggestions selon les préférences
        preferences = context.get('preferences', [])
        if 'bio' in preferences:
            suggestions.append({
                'type': 'preference',
                'suggestion': f'{ingredient_name} bio',
                'reason': 'Version bio selon vos préférences'
            })
        
        if 'local' in preferences:
            suggestions.append({
                'type': 'preference',
                'suggestion': f'{ingredient_name} local',
                'reason': 'Produit local selon vos préférences'
            })
        
        return suggestions[:5]  # Limiter à 5 suggestions
    
    def _is_similar_ingredient(self, ingredient1: str, ingredient2: str) -> bool:
        """Vérifie si deux ingrédients sont similaires"""
        # Catégories d'ingrédients similaires
        categories = {
            'légumes': ['tomate', 'carotte', 'courgette', 'aubergine', 'poivron', 'épinard', 'salade'],
            'fruits': ['pomme', 'poire', 'orange', 'banane', 'fraise', 'pêche', 'abricot'],
            'viandes': ['bœuf', 'porc', 'agneau', 'poulet', 'dinde'],
            'poissons': ['saumon', 'thon', 'cabillaud', 'dorade'],
            'céréales': ['riz', 'pâtes', 'blé', 'quinoa', 'avoine']
        }
        
        for category_items in categories.values():
            if ingredient1 in category_items and ingredient2 in category_items:
                return True
        
        return False
    
    def _get_month_name(self, month: int) -> str:
        """Retourne le nom du mois"""
        months = {
            1: 'janvier', 2: 'février', 3: 'mars', 4: 'avril',
            5: 'mai', 6: 'juin', 7: 'juillet', 8: 'août',
            9: 'septembre', 10: 'octobre', 11: 'novembre', 12: 'décembre'
        }
        return months.get(month, 'mois inconnu')

def test_intelligent_system():
    """Fonction de test du système intelligent"""
    print("🧪 Test du système intelligent Smart Shopping")
    print("=" * 50)
    
    # Test du gestionnaire d'ingrédients
    print("1. Test du gestionnaire d'ingrédients")
    manager = IngredientManager()
    
    # Ajouter des ingrédients de différentes recettes avec des variantes
    test_ingredients = [
        ('pâtes spaghetti', 400, 'g', 'recipe1', 'Carbonara'),
        ('spaghetti', 300, 'g', 'recipe2', 'Bolognaise'),
        ('pâtes', 200, 'g', 'recipe3', 'Pesto'),
        ('lait entier', 500, 'ml', 'recipe4', 'Béchamel'),
        ('lait', 200, 'ml', 'recipe5', 'Crêpes'),
        ('tomates', 400, 'g', 'recipe6', 'Sauce'),
        ('tomate', 200, 'g', 'recipe7', 'Salade')
    ]
    
    for name, qty, unit, recipe_id, recipe_name in test_ingredients:
        manager.add_ingredient(name, qty, unit, recipe_id, recipe_name)
    
    # Consolidation
    consolidated = manager.consolidate_shopping_list()
    
    print(f"✅ {len(consolidated)} ingrédients uniques après consolidation")
    for name, item in consolidated.items():
        if item['isConsolidated']:
            print(f"  🔄 {item['name']}: {item['quantity']} {item['unit']} "
                  f"(consolidé de {item['recipeCount']} recettes)")
        else:
            print(f"  📝 {item['name']}: {item['quantity']} {item['unit']}")
    
    print("\n2. Test de l'API Jow (simulation)")
    jow_api = JowAPIIntegration()
    recipes = jow_api.search_recipes('pâtes', 3)
    print(f"✅ {len(recipes)} recettes trouvées pour 'pâtes'")
    for recipe in recipes:
        print(f"  📖 {recipe['name']} ({recipe['servings']} portions, {recipe['prepTime']} min)")
    
    print("\n3. Test du moteur de suggestions")
    suggestion_engine = IntelligentSuggestionEngine()
    suggestions = suggestion_engine.generate_suggestions(
        {'normalizedName': 'tomate'}, 
        {'budget': 'économique', 'preferences': ['bio']}
    )
    print(f"✅ {len(suggestions)} suggestions générées pour 'tomate'")
    for suggestion in suggestions:
        print(f"  💡 {suggestion['suggestion']} ({suggestion['reason']})")
    
    print("\n🎉 Tous les tests sont passés avec succès !")
    return True

if __name__ == '__main__':
    test_intelligent_system()
