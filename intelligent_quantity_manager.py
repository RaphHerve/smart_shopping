#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire Intelligent de Quantités - Smart Shopping
Évite les doublons et gère les quantités comme sur Jow
Remplace smart_shopping_intelligent.py
"""

import re
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher

class AdvancedIngredientManager:
    """Gestionnaire avancé avec gestion intelligente des quantités"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.similarity_threshold = 0.85
        self.unit_conversions = self._init_unit_conversions()
        self.ingredient_aliases = self._init_ingredient_aliases()
        
    def _init_unit_conversions(self) -> Dict[str, Dict[str, float]]:
        """Initialise les conversions d'unités"""
        return {
            # Poids vers grammes
            'g': {'g': 1, 'kg': 0.001, 'mg': 1000},
            'kg': {'g': 1000, 'kg': 1, 'mg': 1000000},
            'mg': {'g': 0.001, 'kg': 0.000001, 'mg': 1},
            
            # Volume vers millilitres
            'ml': {'ml': 1, 'l': 0.001, 'cl': 0.1, 'dl': 0.01},
            'l': {'ml': 1000, 'l': 1, 'cl': 100, 'dl': 10},
            'cl': {'ml': 10, 'l': 0.01, 'cl': 1, 'dl': 0.1},
            'dl': {'ml': 100, 'l': 0.1, 'cl': 10, 'dl': 1},
            
            # Mesures cuisine vers ml
            'cuillère à soupe': {'ml': 15},
            'cuillère à café': {'ml': 5},
            'c. à soupe': {'ml': 15},
            'c. à café': {'ml': 5},
            'tasse': {'ml': 250},
            'verre': {'ml': 200},
            
            # Unités restent en unités
            'unité': {'unité': 1, 'pièce': 1, 'tranche': 1},
            'pièce': {'unité': 1, 'pièce': 1, 'tranche': 1},
            'tranche': {'unité': 1, 'pièce': 1, 'tranche': 1},
            'gousse': {'unité': 1, 'gousse': 1},
            'branche': {'unité': 1, 'branche': 1},
            'pincée': {'pincée': 1}
        }
    
    def _init_ingredient_aliases(self) -> Dict[str, str]:
        """Initialise les alias d'ingrédients pour détecter les doublons"""
        return {
            # Pâtes
            'spaghetti': 'pâtes',
            'spaghettis': 'pâtes',
            'tagliatelles': 'pâtes',
            'penne': 'pâtes',
            'fusilli': 'pâtes',
            'linguine': 'pâtes',
            'macaroni': 'pâtes',
            'pasta': 'pâtes',
            
            # Légumes
            'tomate': 'tomates',
            'tomates cerises': 'tomates',
            'oignon': 'oignons',
            'oignon rouge': 'oignons',
            'oignon blanc': 'oignons',
            'échalote': 'oignons',
            'pomme de terre': 'pommes de terre',
            'patate': 'pommes de terre',
            
            # Produits laitiers
            'lait entier': 'lait',
            'lait demi-écrémé': 'lait',
            'lait écrémé': 'lait',
            'crème fraîche': 'crème',
            'crème liquide': 'crème',
            
            # Viandes
            'blanc de poulet': 'poulet',
            'cuisse de poulet': 'poulet',
            'escalope de poulet': 'poulet',
            'bœuf haché': 'bœuf',
            'steak haché': 'bœuf',
            
            # Fromages
            'parmesan râpé': 'parmesan',
            'gruyère râpé': 'gruyère',
            'emmental râpé': 'emmental'
        }
    
    def normalize_ingredient_name(self, name: str) -> str:
        """Normalise le nom d'un ingrédient pour détecter les similitudes"""
        # Nettoyage basique
        normalized = name.lower().strip()
        
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
            normalized = normalized.replace(accent, normal)
        
        # Suppression de la ponctuation
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Application des alias
        for alias, canonical in self.ingredient_aliases.items():
            if alias in normalized or normalized in alias:
                normalized = canonical
                break
        
        return normalized
    
    def find_similar_ingredient(self, name: str, existing_ingredients: List[Dict]) -> Optional[Dict]:
        """Trouve un ingrédient similaire dans la liste existante"""
        normalized_name = self.normalize_ingredient_name(name)
        
        for existing in existing_ingredients:
            existing_normalized = self.normalize_ingredient_name(existing['name'])
            
            # Correspondance exacte
            if normalized_name == existing_normalized:
                return existing
            
            # Correspondance par similarité
            similarity = SequenceMatcher(None, normalized_name, existing_normalized).ratio()
            if similarity >= self.similarity_threshold:
                return existing
            
            # Correspondance si l'un contient l'autre
            if (normalized_name in existing_normalized or 
                existing_normalized in normalized_name) and len(normalized_name) > 3:
                return existing
        
        return None
    
    def convert_units(self, quantity: float, from_unit: str, to_unit: str) -> Optional[float]:
        """Convertit une quantité d'une unité vers une autre"""
        from_unit = from_unit.lower().strip()
        to_unit = to_unit.lower().strip()
        
        if from_unit == to_unit:
            return quantity
        
        # Chercher la conversion directe
        if from_unit in self.unit_conversions:
            conversions = self.unit_conversions[from_unit]
            if to_unit in conversions:
                return quantity * conversions[to_unit]
        
        # Chercher via une unité intermédiaire (ex: cuillère à soupe -> ml -> l)
        for intermediate_unit, from_conversions in self.unit_conversions.items():
            if (from_unit in from_conversions and 
                intermediate_unit in self.unit_conversions and 
                to_unit in self.unit_conversions[intermediate_unit]):
                
                # Conversion en deux étapes
                intermediate_quantity = quantity * from_conversions[from_unit]
                return intermediate_quantity * self.unit_conversions[intermediate_unit][to_unit]
        
        return None  # Conversion impossible
    
    def get_best_unit(self, quantity: float, current_unit: str) -> Tuple[float, str]:
        """Retourne la meilleure unité pour afficher une quantité"""
        current_unit = current_unit.lower().strip()
        
        # Règles d'optimisation d'affichage
        if current_unit == 'g':
            if quantity >= 1000:
                return quantity / 1000, 'kg'
        elif current_unit == 'ml':
            if quantity >= 1000:
                return quantity / 1000, 'l'
        elif current_unit == 'mg':
            if quantity >= 1000:
                return quantity / 1000, 'g'
        
        return quantity, current_unit
    
    def add_or_update_item(self, name: str, quantity: float, unit: str, 
                          category: str = 'Recettes', recipe_source: str = None) -> Dict[str, Any]:
        """Ajoute ou met à jour un article avec gestion intelligente des quantités"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Récupérer les articles existants non cochés
                cursor.execute('''
                    SELECT * FROM shopping_list 
                    WHERE checked = 0
                    ORDER BY name
                ''')
                existing_items = [dict(row) for row in cursor.fetchall()]
                
                # Chercher un article similaire
                similar_item = self.find_similar_ingredient(name, existing_items)
                
                if similar_item:
                    # Mettre à jour l'article existant
                    return self._update_existing_item(similar_item, quantity, unit, recipe_source)
                else:
                    # Créer un nouvel article
                    return self._create_new_item(name, quantity, unit, category, recipe_source)
                    
        except Exception as e:
            print(f"Erreur add_or_update_item: {e}")
            return {'success': False, 'error': str(e)}
    
    def _update_existing_item(self, existing_item: Dict, new_quantity: float, 
                            new_unit: str, recipe_source: str = None) -> Dict[str, Any]:
        """Met à jour un article existant en consolidant les quantités"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                existing_quantity = existing_item.get('quantity_decimal', existing_item.get('quantity', 1))
                existing_unit = existing_item.get('unit', 'unité')
                
                # Essayer de convertir vers l'unité existante
                converted_quantity = self.convert_units(new_quantity, new_unit, existing_unit)
                
                if converted_quantity is not None:
                    # Consolidation possible
                    total_quantity = existing_quantity + converted_quantity
                    final_quantity, final_unit = self.get_best_unit(total_quantity, existing_unit)
                    
                    # Mettre à jour en base
                    cursor.execute('''
                        UPDATE shopping_list 
                        SET quantity = ?, quantity_decimal = ?, unit = ?, 
                            recipe_sources = COALESCE(recipe_sources, '') || ?, 
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (
                        int(final_quantity) if final_quantity.is_integer() else final_quantity,
                        final_quantity,
                        final_unit,
                        f", {recipe_source}" if recipe_source else "",
                        existing_item['id']
                    ))
                    
                    conn.commit()
                    
                    return {
                        'success': True,
                        'action': 'consolidated',
                        'item_id': existing_item['id'],
                        'item_name': existing_item['name'],
                        'old_quantity': existing_quantity,
                        'old_unit': existing_unit,
                        'new_quantity': final_quantity,
                        'new_unit': final_unit,
                        'message': f"Consolidé: {existing_quantity} {existing_unit} + {new_quantity} {new_unit} = {final_quantity} {final_unit}"
                    }
                else:
                    # Conversion impossible, créer une note
                    note = f" (+ {new_quantity} {new_unit})"
                    cursor.execute('''
                        UPDATE shopping_list 
                        SET name = CASE 
                            WHEN name LIKE '%+%' THEN name || ', {new_quantity} {new_unit}'
                            ELSE name || ?
                        END,
                        recipe_sources = COALESCE(recipe_sources, '') || ?,
                        updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (note, f", {recipe_source}" if recipe_source else "", existing_item['id']))
                    
                    conn.commit()
                    
                    return {
                        'success': True,
                        'action': 'noted',
                        'item_id': existing_item['id'],
                        'message': f"Ajouté en note: {existing_item['name']}{note}"
                    }
                    
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _create_new_item(self, name: str, quantity: float, unit: str, 
                        category: str, recipe_source: str = None) -> Dict[str, Any]:
        """Crée un nouvel article"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Optimiser l'affichage de la quantité
                display_quantity, display_unit = self.get_best_unit(quantity, unit)
                
                cursor.execute('''
                    INSERT INTO shopping_list 
                    (name, category, quantity, quantity_decimal, unit, recipe_sources, checked, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
                ''', (
                    name,
                    category,
                    int(display_quantity) if display_quantity.is_integer() else display_quantity,
                    display_quantity,
                    display_unit,
                    recipe_source or ""
                ))
                
                item_id = cursor.lastrowid
                conn.commit()
                
                return {
                    'success': True,
                    'action': 'created',
                    'item_id': item_id,
                    'item_name': name,
                    'quantity': display_quantity,
                    'unit': display_unit,
                    'message': f"Créé: {name} ({display_quantity} {display_unit})"
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def add_recipe_ingredients(self, recipe: Dict[str, Any]) -> Dict[str, Any]:
        """Ajoute tous les ingrédients d'une recette avec consolidation"""
        results = {
            'success': True,
            'recipe_name': recipe.get('name', 'Recette sans nom'),
            'total_ingredients': len(recipe.get('ingredients', [])),
            'actions': [],
            'consolidated_count': 0,
            'created_count': 0,
            'errors': []
        }
        
        for ingredient in recipe.get('ingredients', []):
            try:
                result = self.add_or_update_item(
                    name=ingredient.get('name', ''),
                    quantity=ingredient.get('quantity', 1),
                    unit=ingredient.get('unit', 'unité'),
                    category='Recettes',
                    recipe_source=recipe.get('name', 'Recette')
                )
                
                if result['success']:
                    results['actions'].append(result)
                    if result['action'] == 'consolidated':
                        results['consolidated_count'] += 1
                    elif result['action'] == 'created':
                        results['created_count'] += 1
                else:
                    results['errors'].append(result.get('error', 'Erreur inconnue'))
                    
            except Exception as e:
                results['errors'].append(str(e))
        
        if results['errors']:
            results['success'] = len(results['errors']) < len(recipe.get('ingredients', []))
        
        return results
    
    def update_item_quantity(self, item_id: int, new_quantity: float, new_unit: str = None) -> Dict[str, Any]:
        """Met à jour la quantité d'un article existant"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Récupérer l'article actuel
                cursor.execute('SELECT * FROM shopping_list WHERE id = ?', (item_id,))
                item = cursor.fetchone()
                
                if not item:
                    return {'success': False, 'error': 'Article non trouvé'}
                
                # Utiliser l'unité existante si pas spécifiée
                unit = new_unit or item[5] if len(item) > 5 else 'unité'  # Assuming unit is at index 5
                
                # Optimiser l'affichage
                display_quantity, display_unit = self.get_best_unit(new_quantity, unit)
                
                cursor.execute('''
                    UPDATE shopping_list 
                    SET quantity = ?, quantity_decimal = ?, unit = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    int(display_quantity) if display_quantity.is_integer() else display_quantity,
                    display_quantity,
                    display_unit,
                    item_id
                ))
                
                conn.commit()
                
                return {
                    'success': True,
                    'item_id': item_id,
                    'new_quantity': display_quantity,
                    'new_unit': display_unit
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Fonction utilitaire pour migrer la base de données
def upgrade_database_schema(db_path: str):
    """Met à jour le schéma de la base de données pour supporter les nouvelles fonctionnalités"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Ajouter les nouvelles colonnes si elles n'existent pas
            new_columns = [
                ('quantity_decimal', 'REAL'),
                ('unit', 'TEXT DEFAULT "unité"'),
                ('recipe_sources', 'TEXT'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            ]
            
            # Vérifier les colonnes existantes
            cursor.execute("PRAGMA table_info(shopping_list)")
            existing_columns = {col[1]: col for col in cursor.fetchall()}
            
            for column_name, column_def in new_columns:
                if column_name not in existing_columns:
                    cursor.execute(f'ALTER TABLE shopping_list ADD COLUMN {column_name} {column_def}')
                    print(f"✅ Colonne {column_name} ajoutée")
            
            # Migrer les données existantes
            cursor.execute('''
                UPDATE shopping_list 
                SET quantity_decimal = CAST(quantity AS REAL),
                    unit = COALESCE(unit, 'unité'),
                    updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
                WHERE quantity_decimal IS NULL
            ''')
            
            # Créer des index pour améliorer les performances
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_shopping_name_normalized ON shopping_list(LOWER(name))',
                'CREATE INDEX IF NOT EXISTS idx_shopping_checked ON shopping_list(checked)',
                'CREATE INDEX IF NOT EXISTS idx_shopping_category ON shopping_list(category)',
                'CREATE INDEX IF NOT EXISTS idx_shopping_updated ON shopping_list(updated_at)'
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            conn.commit()
            print("✅ Mise à jour du schéma terminée")
            
    except Exception as e:
        print(f"❌ Erreur mise à jour schéma: {e}")

# Instance globale
def get_ingredient_manager(db_path: str) -> AdvancedIngredientManager:
    """Retourne une instance du gestionnaire d'ingrédients"""
    return AdvancedIngredientManager(db_path)
