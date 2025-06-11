#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Correction Smart Shopping - Intégration vraie API Jow + consolidation
"""

import sqlite3
import json
import re
from typing import List, Dict, Any

def fix_shopping_list_schema():
    """Corrige le schéma de la base pour supporter les quantités"""
    try:
        conn = sqlite3.connect('smart_shopping.db')
        cursor = conn.cursor()
        
        # Vérifier si la colonne quantity_decimal existe
        cursor.execute("PRAGMA table_info(shopping_list)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'quantity_decimal' not in columns:
            print("🔧 Ajout colonne quantity_decimal...")
            cursor.execute('ALTER TABLE shopping_list ADD COLUMN quantity_decimal REAL DEFAULT 1.0')
        
        if 'unit' not in columns:
            print("🔧 Ajout colonne unit...")
            cursor.execute('ALTER TABLE shopping_list ADD COLUMN unit TEXT DEFAULT "unité"')
        
        if 'recipe_source' not in columns:
            print("🔧 Ajout colonne recipe_source...")
            cursor.execute('ALTER TABLE shopping_list ADD COLUMN recipe_source TEXT')
        
        conn.commit()
        conn.close()
        print("✅ Schéma base de données corrigé")
        
    except Exception as e:
        print(f"❌ Erreur correction schéma: {e}")

def clean_duplicate_items():
    """Nettoie les doublons existants en consolidant"""
    try:
        conn = sqlite3.connect('smart_shopping.db')
        cursor = conn.cursor()
        
        # Récupérer tous les articles non cochés
        cursor.execute("""
            SELECT id, name, category, quantity, quantity_decimal, unit, checked
            FROM shopping_list 
            WHERE checked = 0
            ORDER BY name, category
        """)
        
        items = cursor.fetchall()
        
        # Grouper par nom normalisé
        grouped_items = {}
        for item in items:
            id_, name, category, quantity, quantity_decimal, unit, checked = item
            
            # Normaliser le nom
            normalized_name = normalize_ingredient_name(name)
            
            if normalized_name not in grouped_items:
                grouped_items[normalized_name] = {
                    'items': [],
                    'total_quantity': 0.0,
                    'unit': unit or 'unité',
                    'category': category,
                    'original_name': name
                }
            
            grouped_items[normalized_name]['items'].append(id_)
            grouped_items[normalized_name]['total_quantity'] += quantity_decimal or quantity or 1.0
        
        # Supprimer les doublons et créer un item consolidé
        for normalized_name, group in grouped_items.items():
            if len(group['items']) > 1:
                print(f"🔄 Consolidation: {group['original_name']} ({len(group['items'])} items -> {group['total_quantity']} {group['unit']})")
                
                # Supprimer tous les items du groupe
                placeholders = ','.join(['?' for _ in group['items']])
                cursor.execute(f"DELETE FROM shopping_list WHERE id IN ({placeholders})", group['items'])
                
                # Créer un nouvel item consolidé
                cursor.execute("""
                    INSERT INTO shopping_list (name, category, quantity, quantity_decimal, unit, recipe_source)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    group['original_name'],
                    group['category'],
                    int(group['total_quantity']),
                    group['total_quantity'],
                    group['unit'],
                    'Consolidé'
                ))
        
        conn.commit()
        conn.close()
        print("✅ Doublons nettoyés et consolidés")
        
    except Exception as e:
        print(f"❌ Erreur nettoyage doublons: {e}")

def normalize_ingredient_name(name: str) -> str:
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
        'pates': 'pates',
        'spaghettis': 'pates',
        'spaghetti': 'pates',
        'tagliatelles': 'pates',
        'penne': 'pates',
        'fusilli': 'pates',
        'macaroni': 'pates',
        'tomates': 'tomate',
        'pommes de terre': 'pomme de terre',
        'patates': 'pomme de terre',
        'oeufs': 'oeuf',
        'oignon': 'oignon',
        'oignons': 'oignon',
        'lardons fumes': 'lardons',
        'lardons': 'lardons',
        'parmesan rape': 'parmesan',
        'parmesan': 'parmesan'
    }
    
    for variant, canonical in replacements.items():
        if variant in name:
            name = name.replace(variant, canonical)
    
    return name.strip()

def create_real_jow_service():
    """Crée le fichier service Jow réel"""
    jow_service_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service Jow réel utilisant l'API jow-api
"""

import logging
from typing import List, Dict, Any, Optional
from jow_api import JowAPI

logger = logging.getLogger(__name__)

class RealJowAPIService:
    """Service d'intégration avec la vraie API Jow"""
    
    def __init__(self):
        self.jow_api = JowAPI()
        logger.info("Service Jow réel initialisé")
    
    def search_recipes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche de recettes sur la vraie API Jow"""
        try:
            # Recherche avec l'API réelle
            results = self.jow_api.search_recipes(query, limit=limit)
            
            # Formater les résultats pour Smart Shopping
            formatted_recipes = []
            for recipe in results:
                formatted_recipe = self._format_jow_recipe(recipe)
                if formatted_recipe:
                    formatted_recipes.append(formatted_recipe)
            
            logger.info(f"Trouvé {len(formatted_recipes)} recettes Jow pour '{query}'")
            return formatted_recipes
            
        except Exception as e:
            logger.error(f"Erreur API Jow réelle: {e}")
            # Fallback vers données simulées
            return self._get_fallback_recipes(query, limit)
    
    def get_recipe_details(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les détails d'une recette"""
        try:
            recipe = self.jow_api.get_recipe(recipe_id)
            return self._format_jow_recipe(recipe) if recipe else None
        except Exception as e:
            logger.error(f"Erreur récupération recette {recipe_id}: {e}")
            return None
    
    def _format_jow_recipe(self, jow_recipe: Dict) -> Dict[str, Any]:
        """Formate une recette Jow pour Smart Shopping"""
        try:
            ingredients = []
            
            # Parser les ingrédients de Jow
            for ingredient in jow_recipe.get('ingredients', []):
                quantity, unit, name = self._parse_ingredient_text(ingredient.get('name', ''))
                
                ingredients.append({
                    'name': name,
                    'quantity': quantity or 1,
                    'unit': unit or 'unité',
                    'originalText': ingredient.get('name', '')
                })
            
            return {
                'id': jow_recipe.get('id', f"jow_{jow_recipe.get('slug', 'unknown')}"),
                'name': jow_recipe.get('name', 'Recette sans nom'),
                'servings': jow_recipe.get('servings', 4),
                'prepTime': jow_recipe.get('prep_time', 30),
                'difficulty': jow_recipe.get('difficulty', 'Moyen'),
                'image': jow_recipe.get('image_url', ''),
                'ingredients': ingredients,
                'source': 'jow',
                'url': jow_recipe.get('url', '')
            }
        except Exception as e:
            logger.error(f"Erreur formatage recette: {e}")
            return None
    
    def _parse_ingredient_text(self, text: str) -> tuple:
        """Parse le texte d'un ingrédient pour extraire quantité, unité et nom"""
        if not text:
            return None, None, text
        
        import re
        
        # Patterns pour quantités
        patterns = [
            r'^(\\d+(?:[.,]\\d+)?)\\s*(g|kg|ml|l|cl|dl)\\s+(.+)$',
            r'^(\\d+(?:[.,]\\d+)?)\\s+(cuillères?\\s+à\\s+(?:soupe|café)|c\\.?\\s*à\\s*[sc]\\.?)\\s+(.+)$',
            r'^(\\d+(?:[.,]\\d+)?)\\s+(tasses?|verres?|pincées?)\\s+(.+)$',
            r'^(\\d+(?:[.,]\\d+)?)\\s+(.+)$',
            r'^(.+)'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, text.strip(), re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    try:
                        return float(groups[0].replace(',', '.')), groups[1].strip(), groups[2].strip()
                    except ValueError:
                        continue
                elif len(groups) == 2:
                    try:
                        return float(groups[0].replace(',', '.')), 'unité', groups[1].strip()
                    except ValueError:
                        continue
                else:
                    return None, 'unité', groups[0].strip()
        
        return None, 'unité', text
    
    def _get_fallback_recipes(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Recettes de fallback si API indisponible"""
        # Même base que dans smart_shopping_intelligent.py
        return []

# Instance globale
real_jow_service = RealJowAPIService()
'''
    
    with open('real_jow_service.py', 'w', encoding='utf-8') as f:
        f.write(jow_service_content)
    
    print("✅ Service Jow réel créé")

def update_app_py_for_real_jow():
    """Met à jour app.py pour utiliser la vraie API Jow"""
    try:
        # Lire le fichier app.py actuel
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remplacer l'import du service Jow
        content = content.replace(
            'jow_service = JowAPIService()',
            '''try:
    from real_jow_service import real_jow_service as jow_service
    print("✅ Service Jow RÉEL activé")
except ImportError:
    jow_service = JowAPIService()
    print("⚠️ Service Jow simulé (real_jow_service non disponible)")'''
        )
        
        # Modifier la fonction d'ajout avec consolidation pour gérer les quantités
        consolidation_fix = '''
    def add_multiple_items_with_consolidation(self, items: List[Dict], existing_list: List[Dict] = None) -> Dict[str, Any]:
        """Ajoute plusieurs articles avec consolidation intelligente et quantités réelles"""
        try:
            if existing_list is None:
                existing_list = self.get_shopping_list()
            
            # Normaliser et grouper tous les articles
            consolidated_items = {}
            
            # Traiter les articles existants
            for existing_item in existing_list:
                if not existing_item.get('checked', False):
                    normalized_name = self._normalize_name(existing_item['name'])
                    if normalized_name not in consolidated_items:
                        consolidated_items[normalized_name] = {
                            'name': existing_item['name'],
                            'quantity': existing_item.get('quantity_decimal', existing_item.get('quantity', 1)),
                            'unit': existing_item.get('unit', 'unité'),
                            'category': existing_item.get('category', 'Divers'),
                            'recipes': [],
                            'recipe_count': 0,
                            'is_existing': True,
                            'item_id': existing_item['id']
                        }
            
            # Traiter les nouveaux articles
            for item in items:
                normalized_name = self._normalize_name(item['name'])
                quantity = float(item.get('quantity', 1))
                unit = item.get('unit', 'unité')
                
                if normalized_name in consolidated_items:
                    # Consolidation : additionner les quantités
                    existing = consolidated_items[normalized_name]
                    
                    # Conversion d'unités si nécessaire
                    converted_qty = self._convert_units(quantity, unit, existing['unit'])
                    if converted_qty is not None:
                        existing['quantity'] += converted_qty
                        existing['recipe_count'] += 1
                        existing['recipes'].append(item.get('recipe_name', 'Recette'))
                    else:
                        # Unités incompatibles, créer un nouvel item
                        new_key = f"{normalized_name}_{unit}"
                        consolidated_items[new_key] = {
                            'name': f"{item['name']} ({unit})",
                            'quantity': quantity,
                            'unit': unit,
                            'category': 'Recettes',
                            'recipes': [item.get('recipe_name', 'Recette')],
                            'recipe_count': 1,
                            'is_existing': False
                        }
                else:
                    # Nouvel ingrédient
                    consolidated_items[normalized_name] = {
                        'name': item['name'],
                        'quantity': quantity,
                        'unit': unit,
                        'category': 'Recettes',
                        'recipes': [item.get('recipe_name', 'Recette')],
                        'recipe_count': 1,
                        'is_existing': False
                    }
            
            # Mettre à jour la base de données
            added_count = 0
            consolidated_count = 0
            
            for normalized_name, item_data in consolidated_items.items():
                if item_data.get('is_existing', False):
                    # Mettre à jour l'item existant
                    if item_data['recipe_count'] > 0:  # A été modifié
                        self.update_item(
                            item_data['item_id'],
                            quantity=int(item_data['quantity']),
                            quantity_decimal=item_data['quantity'],
                            unit=item_data['unit'],
                            recipe_source=f"Consolidé ({item_data['recipe_count']} recettes)"
                        )
                        consolidated_count += 1
                else:
                    # Créer un nouvel item
                    self.add_item_with_details(
                        item_data['name'],
                        'Recettes',
                        int(item_data['quantity']),
                        item_data['quantity'],
                        item_data['unit'],
                        f"Recette: {', '.join(item_data['recipes'])}"
                    )
                    added_count += 1
                    
                    if item_data['recipe_count'] > 1:
                        consolidated_count += 1
            
            return {
                'success': True,
                'consolidatedItems': consolidated_count,
                'addedItems': added_count,
                'totalItems': len(consolidated_items)
            }
            
        except Exception as e:
            logger.error(f"Erreur consolidation: {e}")
            return {'success': False, 'error': str(e)}
    
    def add_item_with_details(self, name: str, category: str = 'Divers', 
                             quantity: int = 1, quantity_decimal: float = None, 
                             unit: str = 'unité', recipe_source: str = None) -> int:
        """Ajoute un article avec détails complets"""
        item_id = db.execute_update('''
            INSERT INTO shopping_list (name, category, quantity, quantity_decimal, unit, recipe_source)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, category, quantity, quantity_decimal or quantity, unit, recipe_source))
        
        self._update_frequent_items(name, category)
        logger.info(f"Article ajouté: {name} ({quantity_decimal or quantity} {unit})")
        return item_id
    
    def _normalize_name(self, name: str) -> str:
        """Normalise un nom d'ingrédient"""
        # Même logique que dans smart_shopping_intelligent.py
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
        
        # Normalisation des variantes
        replacements = {
            'pates': 'pates', 'spaghettis': 'pates', 'spaghetti': 'pates',
            'tagliatelles': 'pates', 'penne': 'pates', 'fusilli': 'pates',
            'lardons fumes': 'lardons', 'parmesan rape': 'parmesan',
            'oeufs': 'oeuf', 'tomates': 'tomate'
        }
        
        for variant, canonical in replacements.items():
            if variant in name:
                name = name.replace(variant, canonical)
        
        return name.strip()
    
    def _convert_units(self, quantity: float, from_unit: str, to_unit: str) -> float:
        """Convertit les unités si possible"""
        conversions = {
            ('kg', 'g'): 1000, ('g', 'kg'): 0.001,
            ('l', 'ml'): 1000, ('ml', 'l'): 0.001,
            ('cl', 'ml'): 10, ('ml', 'cl'): 0.1
        }
        
        key = (from_unit.lower(), to_unit.lower())
        if key in conversions:
            return quantity * conversions[key]
        
        # Unités identiques
        if from_unit.lower() == to_unit.lower():
            return quantity
        
        # Unités incompatibles
        return None
'''
        
        # Injecter la correction dans la classe ShoppingListManager
        if 'def add_multiple_items_with_consolidation(' in content:
            # Remplacer la méthode existante
            import re
            pattern = r'def add_multiple_items_with_consolidation\(.*?\n        except Exception as e:\n            logger\.error\(.*?\n            return \{\'success\': False, \'error\': str\(e\)\}'
            content = re.sub(pattern, consolidation_fix.strip(), content, flags=re.DOTALL)
        else:
            # Ajouter la méthode à la classe
            content = content.replace(
                'class ShoppingListManager:',
                f'class ShoppingListManager:{consolidation_fix}'
            )
        
        # Sauvegarder le fichier modifié
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ app.py mis à jour pour vraie API Jow")
        
    except Exception as e:
        print(f"❌ Erreur mise à jour app.py: {e}")

def main():
    """Fonction principale de correction"""
    print("🔧 Correction Smart Shopping - API Jow réelle + consolidation")
    print("=" * 60)
    
    # 1. Corriger le schéma de la base
    fix_shopping_list_schema()
    
    # 2. Nettoyer les doublons existants
    clean_duplicate_items()
    
    # 3. Créer le service Jow réel
    create_real_jow_service()
    
    # 4. Mettre à jour app.py
    update_app_py_for_real_jow()
    
    print("\n🎉 Correction terminée !")
    print("📋 Prochaines étapes :")
    print("   1. pip install jow-api")
    print("   2. sudo systemctl restart smart-shopping")
    print("   3. Tester la recherche Jow")

if __name__ == '__main__':
    main()
