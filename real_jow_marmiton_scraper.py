#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scraper RÉEL pour jow.fr et marmiton.fr
Remplace jow_scraper_intelligent.py
"""

import requests
import json
import re
import logging
import time
import random
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from urllib.parse import urljoin, quote

logger = logging.getLogger(__name__)

class RealJowScraper:
    """Scraper réel pour jow.fr"""
    
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
        self.base_url = "https://jow.fr"
        
        # Headers réalistes pour éviter la détection
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.delay_range = (1, 3)  # Délai entre requêtes
    
    def search_recipes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche réelle sur jow.fr"""
        try:
            logger.info(f"🔍 Recherche Jow réelle pour: '{query}'")
            
            # URL de recherche Jow
            search_url = f"{self.base_url}/recherche"
            params = {
                'q': query,
                'type': 'recettes'
            }
            
            # Respecter les délais
            time.sleep(random.uniform(*self.delay_range))
            
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parser les recettes depuis le HTML
            recipes = self._parse_jow_recipes_html(soup, limit)
            
            logger.info(f"✅ Trouvé {len(recipes)} recettes Jow pour '{query}'")
            return recipes
            
        except Exception as e:
            logger.error(f"❌ Erreur scraping Jow: {e}")
            # Fallback vers API interne si scraping échoue
            return self._fallback_jow_recipes(query, limit)
    
    def _parse_jow_recipes_html(self, soup: BeautifulSoup, limit: int) -> List[Dict[str, Any]]:
        """Parse les recettes depuis le HTML de Jow"""
        recipes = []
        
        # Sélecteurs CSS pour les recettes Jow (à ajuster selon leur structure)
        recipe_cards = soup.find_all('div', class_=['recipe-card', 'RecipeCard', 'recipe-item'])[:limit]
        
        for i, card in enumerate(recipe_cards):
            try:
                recipe = self._extract_recipe_from_card(card, f"jow_real_{i}")
                if recipe:
                    recipes.append(recipe)
            except Exception as e:
                logger.warning(f"Erreur parsing recette Jow: {e}")
                continue
        
        return recipes
    
    def _extract_recipe_from_card(self, card, recipe_id: str) -> Dict[str, Any]:
        """Extrait les données d'une recette depuis une carte HTML"""
        # Nom de la recette
        name_elem = card.find(['h2', 'h3', 'h4'], class_=['title', 'name', 'recipe-title'])
        name = name_elem.get_text(strip=True) if name_elem else "Recette sans nom"
        
        # Temps de préparation
        time_elem = card.find(attrs={'data-time': True}) or card.find(text=re.compile(r'\d+\s*min'))
        prep_time = self._extract_time(time_elem) if time_elem else 30
        
        # Portions
        serving_elem = card.find(text=re.compile(r'\d+\s*pers'))
        servings = self._extract_servings(serving_elem) if serving_elem else 4
        
        # Image
        img_elem = card.find('img')
        image_url = img_elem.get('src') or img_elem.get('data-src') if img_elem else None
        
        # URL de la recette pour récupérer les ingrédients
        link_elem = card.find('a')
        recipe_url = urljoin(self.base_url, link_elem.get('href')) if link_elem else None
        
        # Récupérer les ingrédients depuis la page de détail
        ingredients = self._get_recipe_ingredients(recipe_url) if recipe_url else []
        
        return {
            'id': recipe_id,
            'name': name,
            'servings': servings,
            'prepTime': prep_time,
            'difficulty': 'Moyen',
            'image': image_url,
            'ingredients': ingredients,
            'source': 'jow',
            'url': recipe_url,
            'tags': ['jow', 'scraping']
        }
    
    def _get_recipe_ingredients(self, recipe_url: str) -> List[Dict[str, Any]]:
        """Récupère les ingrédients depuis la page de détail"""
        try:
            time.sleep(random.uniform(*self.delay_range))
            response = self.session.get(recipe_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Chercher les ingrédients dans différents formats possibles
            ingredients = []
            
            # Format 1: Liste d'ingrédients
            ingredient_lists = soup.find_all(['ul', 'ol'], class_=['ingredients', 'ingredient-list'])
            for ul in ingredient_lists:
                for li in ul.find_all('li'):
                    ingredient_text = li.get_text(strip=True)
                    if ingredient_text:
                        parsed = self._parse_ingredient_text(ingredient_text)
                        ingredients.append(parsed)
            
            # Format 2: Divs d'ingrédients
            ingredient_divs = soup.find_all('div', class_=['ingredient', 'ingredient-item'])
            for div in ingredient_divs:
                ingredient_text = div.get_text(strip=True)
                if ingredient_text:
                    parsed = self._parse_ingredient_text(ingredient_text)
                    ingredients.append(parsed)
            
            return ingredients[:20]  # Limiter à 20 ingrédients max
            
        except Exception as e:
            logger.warning(f"Erreur récupération ingrédients: {e}")
            return []
    
    def _parse_ingredient_text(self, text: str) -> Dict[str, Any]:
        """Parse le texte d'un ingrédient pour extraire quantité, unité et nom"""
        # Patterns pour parser les ingrédients
        patterns = [
            r'^(\d+(?:[.,]\d+)?)\s*(g|kg|ml|l|cl|dl)\s+(.+)$',  # 500g farine
            r'^(\d+(?:[.,]\d+)?)\s+(cuillères?\s+à\s+(?:soupe|café)|c\.?\s*à\s*[sc]\.?)\s+(.+)$',
            r'^(\d+(?:[.,]\d+)?)\s+(tasses?|verres?|pincées?|gousses?|tranches?)\s+(.+)$',
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
                        return {
                            'name': name,
                            'quantity': quantity,
                            'unit': unit,
                            'originalText': text
                        }
                    except ValueError:
                        continue
                elif len(groups) == 2:
                    try:
                        quantity = float(groups[0].replace(',', '.'))
                        name = groups[1].strip()
                        return {
                            'name': name,
                            'quantity': quantity,
                            'unit': 'unité',
                            'originalText': text
                        }
                    except ValueError:
                        continue
                else:
                    return {
                        'name': groups[0].strip(),
                        'quantity': 1,
                        'unit': 'unité',
                        'originalText': text
                    }
        
        return {
            'name': text,
            'quantity': 1,
            'unit': 'unité',
            'originalText': text
        }
    
    def _extract_time(self, element) -> int:
        """Extrait le temps de préparation"""
        if isinstance(element, str):
            text = element
        else:
            text = element.get_text() if hasattr(element, 'get_text') else str(element)
        
        time_match = re.search(r'(\d+)', text)
        return int(time_match.group(1)) if time_match else 30
    
    def _extract_servings(self, element) -> int:
        """Extrait le nombre de portions"""
        if isinstance(element, str):
            text = element
        else:
            text = element.get_text() if hasattr(element, 'get_text') else str(element)
        
        serving_match = re.search(r'(\d+)', text)
        return int(serving_match.group(1)) if serving_match else 4
    
    def _fallback_jow_recipes(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Recettes de fallback si le scraping échoue"""
        fallback_recipes = {
            'pâtes': [
                {
                    'id': 'fallback_pates_1',
                    'name': 'Pâtes à la carbonara',
                    'servings': 4,
                    'prepTime': 20,
                    'ingredients': [
                        {'name': 'spaghetti', 'quantity': 400, 'unit': 'g'},
                        {'name': 'lardons fumés', 'quantity': 200, 'unit': 'g'},
                        {'name': 'œufs', 'quantity': 3, 'unit': 'unité'},
                        {'name': 'parmesan râpé', 'quantity': 100, 'unit': 'g'}
                    ],
                    'source': 'jow_fallback'
                }
            ],
            'riz': [
                {
                    'id': 'fallback_riz_1',
                    'name': 'Riz pilaf aux légumes',
                    'servings': 4,
                    'prepTime': 30,
                    'ingredients': [
                        {'name': 'riz basmati', 'quantity': 300, 'unit': 'g'},
                        {'name': 'bouillon de volaille', 'quantity': 600, 'unit': 'ml'},
                        {'name': 'carotte', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'petits pois', 'quantity': 100, 'unit': 'g'}
                    ],
                    'source': 'jow_fallback'
                }
            ]
        }
        
        query_lower = query.lower()
        for key, recipes in fallback_recipes.items():
            if key in query_lower:
                return recipes[:limit]
        
        return []

class RealMarmitonScraper:
    """Scraper réel pour marmiton.org"""
    
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
        self.base_url = "https://www.marmiton.org"
        
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
        })
        
        self.delay_range = (2, 4)  # Délai plus long pour Marmiton
    
    def search_recipes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche réelle sur marmiton.org"""
        try:
            logger.info(f"🔍 Recherche Marmiton réelle pour: '{query}'")
            
            # URL de recherche Marmiton
            search_url = f"{self.base_url}/recettes/recherche.aspx"
            params = {
                'aqt': query
            }
            
            time.sleep(random.uniform(*self.delay_range))
            
            response = self.session.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parser les résultats de recherche
            recipes = self._parse_marmiton_search_results(soup, limit)
            
            logger.info(f"✅ Trouvé {len(recipes)} recettes Marmiton pour '{query}'")
            return recipes
            
        except Exception as e:
            logger.error(f"❌ Erreur scraping Marmiton: {e}")
            return self._fallback_marmiton_recipes(query, limit)
    
    def _parse_marmiton_search_results(self, soup: BeautifulSoup, limit: int) -> List[Dict[str, Any]]:
        """Parse les résultats de recherche Marmiton"""
        recipes = []
        
        # Sélecteurs pour les recettes Marmiton
        recipe_cards = soup.find_all('div', class_=['recipe-card', 'MRTN__sc-1gofnyi-0'])[:limit]
        
        for i, card in enumerate(recipe_cards):
            try:
                recipe = self._extract_marmiton_recipe(card, f"marmiton_real_{i}")
                if recipe:
                    recipes.append(recipe)
            except Exception as e:
                logger.warning(f"Erreur parsing recette Marmiton: {e}")
                continue
        
        return recipes
    
    def _extract_marmiton_recipe(self, card, recipe_id: str) -> Dict[str, Any]:
        """Extrait une recette depuis une carte Marmiton"""
        # Nom de la recette
        name_elem = card.find(['h2', 'h3', 'a'], class_=['recipe-title', 'MRTN__sc-1gofnyi-7'])
        name = name_elem.get_text(strip=True) if name_elem else "Recette Marmiton"
        
        # Lien vers la recette
        link_elem = card.find('a')
        if link_elem:
            recipe_url = urljoin(self.base_url, link_elem.get('href'))
        else:
            return None
        
        # Récupérer les détails depuis la page de la recette
        recipe_details = self._get_marmiton_recipe_details(recipe_url)
        
        return {
            'id': recipe_id,
            'name': name,
            'servings': recipe_details.get('servings', 4),
            'prepTime': recipe_details.get('prepTime', 30),
            'difficulty': recipe_details.get('difficulty', 'Moyen'),
            'image': recipe_details.get('image'),
            'ingredients': recipe_details.get('ingredients', []),
            'instructions': recipe_details.get('instructions', []),
            'source': 'marmiton',
            'url': recipe_url,
            'tags': ['marmiton', 'scraping']
        }
    
    def _get_marmiton_recipe_details(self, recipe_url: str) -> Dict[str, Any]:
        """Récupère les détails d'une recette Marmiton"""
        try:
            time.sleep(random.uniform(*self.delay_range))
            response = self.session.get(recipe_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {}
            
            # Ingrédients
            ingredients = []
            ingredient_sections = soup.find_all(['ul', 'div'], class_=['recipe-ingredients', 'mrtn__recipe_ingredients'])
            
            for section in ingredient_sections:
                for item in section.find_all(['li', 'div']):
                    text = item.get_text(strip=True)
                    if text and len(text) > 2:
                        parsed = self._parse_marmiton_ingredient(text)
                        ingredients.append(parsed)
            
            details['ingredients'] = ingredients[:15]  # Limiter à 15
            
            # Temps de préparation
            time_elem = soup.find(attrs={'data-cooktime': True}) or soup.find(text=re.compile(r'\d+\s*min'))
            details['prepTime'] = self._extract_time(time_elem) if time_elem else 30
            
            # Portions
            serving_elem = soup.find(attrs={'data-serving': True}) or soup.find(text=re.compile(r'\d+\s*pers'))
            details['servings'] = self._extract_servings(serving_elem) if serving_elem else 4
            
            # Image
            img_elem = soup.find('img', class_=['recipe-media-image', 'mrtn__recipe_media_image'])
            details['image'] = img_elem.get('src') if img_elem else None
            
            return details
            
        except Exception as e:
            logger.warning(f"Erreur détails recette Marmiton: {e}")
            return {}
    
    def _parse_marmiton_ingredient(self, text: str) -> Dict[str, Any]:
        """Parse un ingrédient Marmiton"""
        # Utiliser la même logique que Jow
        patterns = [
            r'^(\d+(?:[.,]\d+)?)\s*(g|kg|ml|l|cl|dl)\s+(.+)$',
            r'^(\d+(?:[.,]\d+)?)\s+(cuillères?\s+à\s+(?:soupe|café)|c\.?\s*à\s*[sc]\.?)\s+(.+)$',
            r'^(\d+(?:[.,]\d+)?)\s+(.+)$',
            r'^(.+)',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, text.strip(), re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    try:
                        return {
                            'name': groups[2].strip(),
                            'quantity': float(groups[0].replace(',', '.')),
                            'unit': groups[1].strip(),
                            'originalText': text
                        }
                    except ValueError:
                        continue
                elif len(groups) == 2:
                    try:
                        return {
                            'name': groups[1].strip(),
                            'quantity': float(groups[0].replace(',', '.')),
                            'unit': 'unité',
                            'originalText': text
                        }
                    except ValueError:
                        continue
                else:
                    return {
                        'name': groups[0].strip(),
                        'quantity': 1,
                        'unit': 'unité',
                        'originalText': text
                    }
        
        return {
            'name': text,
            'quantity': 1,
            'unit': 'unité',
            'originalText': text
        }
    
    def _extract_time(self, element) -> int:
        """Extrait le temps depuis un élément"""
        if isinstance(element, str):
            text = element
        else:
            text = element.get_text() if hasattr(element, 'get_text') else str(element)
        
        time_match = re.search(r'(\d+)', text)
        return int(time_match.group(1)) if time_match else 30
    
    def _extract_servings(self, element) -> int:
        """Extrait les portions depuis un élément"""
        if isinstance(element, str):
            text = element
        else:
            text = element.get_text() if hasattr(element, 'get_text') else str(element)
        
        serving_match = re.search(r'(\d+)', text)
        return int(serving_match.group(1)) if serving_match else 4
    
    def _fallback_marmiton_recipes(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Recettes de fallback Marmiton"""
        fallback_recipes = [
            {
                'id': 'marmiton_fallback_1',
                'name': f'Recette traditionnelle au {query}',
                'servings': 4,
                'prepTime': 45,
                'ingredients': [
                    {'name': query, 'quantity': 300, 'unit': 'g'},
                    {'name': 'oignon', 'quantity': 1, 'unit': 'unité'},
                    {'name': 'huile d\'olive', 'quantity': 2, 'unit': 'cuillère à soupe'}
                ],
                'source': 'marmiton_fallback'
            }
        ]
        
        return fallback_recipes[:limit]

class UnifiedRecipeScraper:
    """Scraper unifié qui utilise Jow ET Marmiton"""
    
    def __init__(self):
        self.jow_scraper = RealJowScraper()
        self.marmiton_scraper = RealMarmitonScraper()
    
    def search_recipes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche sur les deux sources et combine les résultats"""
        all_recipes = []
        
        # Répartir les résultats : 60% Jow, 40% Marmiton
        jow_limit = max(1, int(limit * 0.6))
        marmiton_limit = max(1, limit - jow_limit)
        
        try:
            # Recherche Jow
            jow_recipes = self.jow_scraper.search_recipes(query, jow_limit)
            all_recipes.extend(jow_recipes)
            
            # Recherche Marmiton
            marmiton_recipes = self.marmiton_scraper.search_recipes(query, marmiton_limit)
            all_recipes.extend(marmiton_recipes)
            
            # Mélanger les résultats pour plus de diversité
            import random
            random.shuffle(all_recipes)
            
            logger.info(f"✅ Total: {len(all_recipes)} recettes ({len(jow_recipes)} Jow + {len(marmiton_recipes)} Marmiton)")
            return all_recipes[:limit]
            
        except Exception as e:
            logger.error(f"❌ Erreur scraping unifié: {e}")
            return []

# Instance globale pour utilisation dans app.py
unified_recipe_scraper = UnifiedRecipeScraper()
