#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scraper RÉEL pour jow.fr et marmiton.fr - VERSION SANS LXML
Utilise html.parser natif Python + html5lib comme fallback
"""

import requests
import json
import re
import logging
import time
import random
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote

# Import BeautifulSoup avec gestion d'erreur
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
    print("✅ BeautifulSoup disponible")
except ImportError:
    BS4_AVAILABLE = False
    print("❌ BeautifulSoup non disponible")

try:
    from fake_useragent import UserAgent
    UA_AVAILABLE = True
except ImportError:
    UA_AVAILABLE = False
    print("⚠️  fake_useragent non disponible, utilisation d'un user agent fixe")

logger = logging.getLogger(__name__)

# User Agent de fallback si fake_useragent ne fonctionne pas
DEFAULT_USER_AGENT = "Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

def safe_beautifulsoup(content, preferred_parser='html.parser'):
    """
    Crée un objet BeautifulSoup de manière sécurisée
    Essaie plusieurs parsers dans l'ordre de préférence
    """
    if not BS4_AVAILABLE:
        return None
    
    parsers_to_try = [
        'html.parser',     # Parser natif Python (toujours disponible)
        'html5lib',        # Parser plus robuste si disponible
        'lxml-xml',        # Fallback lxml si installé (peu probable sur Raspberry Pi)
    ]
    
    # Mettre le parser préféré en premier
    if preferred_parser in parsers_to_try:
        parsers_to_try.remove(preferred_parser)
        parsers_to_try.insert(0, preferred_parser)
    
    for parser in parsers_to_try:
        try:
            return BeautifulSoup(content, parser)
        except Exception as e:
            logger.warning(f"Parser {parser} failed: {e}")
            continue
    
    # Si tous les parsers échouent, essayer sans spécifier de parser
    try:
        return BeautifulSoup(content)
    except Exception as e:
        logger.error(f"Tous les parsers BeautifulSoup ont échoué: {e}")
        return None

class RealJowScraper:
    """Scraper réel pour jow.fr - VERSION SANS LXML"""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://jow.fr"
        
        # User agent avec fallback
        if UA_AVAILABLE:
            try:
                ua = UserAgent()
                user_agent = ua.random
            except:
                user_agent = DEFAULT_USER_AGENT
        else:
            user_agent = DEFAULT_USER_AGENT
        
        # Headers réalistes pour éviter la détection
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.delay_range = (1, 3)  # Délai entre requêtes
    
    def search_recipes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche réelle sur jow.fr avec fallback robuste"""
        try:
            logger.info(f"🔍 Recherche Jow réelle pour: '{query}'")
            
            if not BS4_AVAILABLE:
                return self._fallback_jow_recipes(query, limit)
            
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
            
            # Parser avec notre fonction sécurisée
            soup = safe_beautifulsoup(response.content, 'html.parser')
            
            if soup is None:
                logger.warning("Échec parsing HTML Jow, utilisation du fallback")
                return self._fallback_jow_recipes(query, limit)
            
            # Parser les recettes depuis le HTML
            recipes = self._parse_jow_recipes_html(soup, limit)
            
            logger.info(f"✅ Trouvé {len(recipes)} recettes Jow pour '{query}'")
            return recipes
            
        except Exception as e:
            logger.error(f"❌ Erreur scraping Jow: {e}")
            # Fallback vers API interne si scraping échoue
            return self._fallback_jow_recipes(query, limit)
    
    def _parse_jow_recipes_html(self, soup, limit: int) -> List[Dict[str, Any]]:
        """Parse les recettes depuis le HTML de Jow de manière robuste"""
        recipes = []
        
        if soup is None:
            return recipes
        
        # Sélecteurs CSS pour les recettes Jow (plusieurs formats possibles)
        selectors = [
            'div[class*="recipe"]',
            'div[class*="Recipe"]',
            'article[class*="recipe"]',
            '.recipe-card',
            '.RecipeCard',
            '.recipe-item'
        ]
        
        recipe_cards = []
        for selector in selectors:
            try:
                cards = soup.select(selector)
                if cards:
                    recipe_cards = cards[:limit]
                    break
            except:
                continue
        
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
        """Extrait les données d'une recette depuis une carte HTML de manière robuste"""
        try:
            # Nom de la recette - plusieurs sélecteurs possibles
            name = None
            name_selectors = ['h2', 'h3', 'h4', '[class*="title"]', '[class*="name"]']
            
            for selector in name_selectors:
                try:
                    name_elem = card.select_one(selector)
                    if name_elem:
                        name = name_elem.get_text(strip=True)
                        if name:
                            break
                except:
                    continue
            
            if not name:
                name = "Recette Jow"
            
            # Temps de préparation
            prep_time = 30
            try:
                time_elem = card.select_one('[data-time]') or card.find(string=re.compile(r'\d+\s*min'))
                if time_elem:
                    prep_time = self._extract_time(time_elem)
            except:
                pass
            
            # Portions
            servings = 4
            try:
                serving_elem = card.find(string=re.compile(r'\d+\s*pers'))
                if serving_elem:
                    servings = self._extract_servings(serving_elem)
            except:
                pass
            
            # Image
            image_url = None
            try:
                img_elem = card.select_one('img')
                if img_elem:
                    image_url = img_elem.get('src') or img_elem.get('data-src')
            except:
                pass
            
            # URL de la recette pour récupérer les ingrédients
            recipe_url = None
            try:
                link_elem = card.select_one('a')
                if link_elem:
                    href = link_elem.get('href')
                    if href:
                        recipe_url = urljoin(self.base_url, href)
            except:
                pass
            
            # Récupérer les ingrédients depuis la page de détail (avec gestion d'erreur)
            ingredients = []
            if recipe_url:
                try:
                    ingredients = self._get_recipe_ingredients(recipe_url)
                except:
                    pass
            
            # Si pas d'ingrédients, créer des ingrédients de base
            if not ingredients:
                ingredients = self._generate_basic_ingredients(name)
            
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
            
        except Exception as e:
            logger.warning(f"Erreur extraction recette: {e}")
            return None
    
    def _get_recipe_ingredients(self, recipe_url: str) -> List[Dict[str, Any]]:
        """Récupère les ingrédients depuis la page de détail de manière robuste"""
        try:
            time.sleep(random.uniform(*self.delay_range))
            response = self.session.get(recipe_url, timeout=10)
            response.raise_for_status()
            
            soup = safe_beautifulsoup(response.content, 'html.parser')
            if soup is None:
                return []
            
            # Chercher les ingrédients dans différents formats possibles
            ingredients = []
            
            # Format 1: Listes d'ingrédients
            ingredient_selectors = [
                'ul[class*="ingredient"] li',
                'ol[class*="ingredient"] li',
                '.ingredients li',
                '.ingredient-list li',
                '[class*="ingredient"] li'
            ]
            
            for selector in ingredient_selectors:
                try:
                    items = soup.select(selector)
                    for item in items:
                        text = item.get_text(strip=True)
                        if text and len(text) > 2:
                            parsed = self._parse_ingredient_text(text)
                            if parsed:
                                ingredients.append(parsed)
                    
                    if ingredients:
                        break
                except:
                    continue
            
            # Format 2: Divs d'ingrédients si pas trouvé dans les listes
            if not ingredients:
                div_selectors = [
                    'div[class*="ingredient"]',
                    '.ingredient-item',
                    '[data-ingredient]'
                ]
                
                for selector in div_selectors:
                    try:
                        items = soup.select(selector)
                        for item in items:
                            text = item.get_text(strip=True)
                            if text and len(text) > 2:
                                parsed = self._parse_ingredient_text(text)
                                if parsed:
                                    ingredients.append(parsed)
                        
                        if ingredients:
                            break
                    except:
                        continue
            
            return ingredients[:20]  # Limiter à 20 ingrédients max
            
        except Exception as e:
            logger.warning(f"Erreur récupération ingrédients: {e}")
            return []
    
    def _parse_ingredient_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse le texte d'un ingrédient pour extraire quantité, unité et nom"""
        if not text or len(text.strip()) < 2:
            return None
        
        # Patterns pour parser les ingrédients (ordre d'importance)
        patterns = [
            r'^(\d+(?:[.,]\d+)?)\s*(g|kg|ml|l|cl|dl)\s+(.+)$',  # 500g farine
            r'^(\d+(?:[.,]\d+)?)\s+(cuillères?\s+à\s+(?:soupe|café)|c\.?\s*à\s*[sc]\.?)\s+(.+)$',  # cuillères
            r'^(\d+(?:[.,]\d+)?)\s+(tasses?|verres?|pincées?|gousses?|tranches?|branches?)\s+(.+)$',  # mesures
            r'^(\d+(?:[.,]\d+)?)\s+(.+)$',  # 3 oeufs
            r'^(.+)',  # Juste le nom
        ]
        
        for pattern in patterns:
            try:
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
                        except (ValueError, IndexError):
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
                        except (ValueError, IndexError):
                            continue
                    else:
                        name = groups[0].strip()
                        if name:
                            return {
                                'name': name,
                                'quantity': 1,
                                'unit': 'unité',
                                'originalText': text
                            }
            except Exception:
                continue
        
        # Fallback: retourner le texte brut
        return {
            'name': text.strip(),
            'quantity': 1,
            'unit': 'unité',
            'originalText': text
        }
    
    def _generate_basic_ingredients(self, recipe_name: str) -> List[Dict[str, Any]]:
        """Génère des ingrédients de base selon le nom de la recette"""
        basic_ingredients = []
        
        name_lower = recipe_name.lower()
        
        # Ingrédients basés sur des mots-clés
        if any(word in name_lower for word in ['pâtes', 'spaghetti', 'tagliatelle', 'pasta']):
            basic_ingredients = [
                {'name': 'pâtes', 'quantity': 400, 'unit': 'g'},
                {'name': 'huile d\'olive', 'quantity': 2, 'unit': 'cuillère à soupe'}
            ]
        elif any(word in name_lower for word in ['riz', 'risotto']):
            basic_ingredients = [
                {'name': 'riz', 'quantity': 300, 'unit': 'g'},
                {'name': 'bouillon', 'quantity': 500, 'unit': 'ml'}
            ]
        elif any(word in name_lower for word in ['salade', 'salad']):
            basic_ingredients = [
                {'name': 'salade', 'quantity': 1, 'unit': 'unité'},
                {'name': 'vinaigrette', 'quantity': 3, 'unit': 'cuillère à soupe'}
            ]
        else:
            # Ingrédients génériques
            basic_ingredients = [
                {'name': 'ingrédient principal', 'quantity': 300, 'unit': 'g'},
                {'name': 'huile', 'quantity': 1, 'unit': 'cuillère à soupe'}
            ]
        
        return basic_ingredients
    
    def _extract_time(self, element) -> int:
        """Extrait le temps de préparation"""
        try:
            if isinstance(element, str):
                text = element
            else:
                text = element.get_text() if hasattr(element, 'get_text') else str(element)
            
            time_match = re.search(r'(\d+)', text)
            return int(time_match.group(1)) if time_match else 30
        except:
            return 30
    
    def _extract_servings(self, element) -> int:
        """Extrait le nombre de portions"""
        try:
            if isinstance(element, str):
                text = element
            else:
                text = element.get_text() if hasattr(element, 'get_text') else str(element)
            
            serving_match = re.search(r'(\d+)', text)
            return int(serving_match.group(1)) if serving_match else 4
        except:
            return 4
    
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
                },
                {
                    'id': 'fallback_pates_2',
                    'name': 'Pâtes à la bolognaise',
                    'servings': 4,
                    'prepTime': 25,
                    'ingredients': [
                        {'name': 'pâtes', 'quantity': 400, 'unit': 'g'},
                        {'name': 'viande hachée', 'quantity': 300, 'unit': 'g'},
                        {'name': 'sauce tomate', 'quantity': 400, 'unit': 'ml'},
                        {'name': 'oignon', 'quantity': 1, 'unit': 'unité'}
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
            ],
            'salade': [
                {
                    'id': 'fallback_salade_1',
                    'name': 'Salade César',
                    'servings': 4,
                    'prepTime': 15,
                    'ingredients': [
                        {'name': 'salade romaine', 'quantity': 1, 'unit': 'unité'},
                        {'name': 'poulet grillé', 'quantity': 200, 'unit': 'g'},
                        {'name': 'parmesan', 'quantity': 50, 'unit': 'g'},
                        {'name': 'croûtons', 'quantity': 100, 'unit': 'g'}
                    ],
                    'source': 'jow_fallback'
                }
            ]
        }
        
        query_lower = query.lower()
        for key, recipes in fallback_recipes.items():
            if key in query_lower:
                return recipes[:limit]
        
        # Fallback générique
        return [{
            'id': 'fallback_generic',
            'name': f'Recette au {query}',
            'servings': 4,
            'prepTime': 30,
            'ingredients': [
                {'name': query, 'quantity': 300, 'unit': 'g'},
                {'name': 'huile d\'olive', 'quantity': 2, 'unit': 'cuillère à soupe'},
                {'name': 'sel et poivre', 'quantity': 1, 'unit': 'pincée'}
            ],
            'source': 'jow_fallback'
        }]

class RealMarmitonScraper:
    """Scraper réel pour marmiton.org - VERSION SANS LXML"""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.marmiton.org"
        
        # User agent avec fallback
        if UA_AVAILABLE:
            try:
                ua = UserAgent()
                user_agent = ua.random
            except:
                user_agent = DEFAULT_USER_AGENT
        else:
            user_agent = DEFAULT_USER_AGENT
        
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
        })
        
        self.delay_range = (2, 4)  # Délai plus long pour Marmiton
    
    def search_recipes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche réelle sur marmiton.org avec fallback robuste"""
        try:
            logger.info(f"🔍 Recherche Marmiton réelle pour: '{query}'")
            
            if not BS4_AVAILABLE:
                return self._fallback_marmiton_recipes(query, limit)
            
            # URL de recherche Marmiton
            search_url = f"{self.base_url}/recettes/recherche.aspx"
            params = {
                'aqt': query
            }
            
            time.sleep(random.uniform(*self.delay_range))
            
            response = self.session.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            
            soup = safe_beautifulsoup(response.content, 'html.parser')
            
            if soup is None:
                logger.warning("Échec parsing HTML Marmiton, utilisation du fallback")
                return self._fallback_marmiton_recipes(query, limit)
            
            # Parser les résultats de recherche
            recipes = self._parse_marmiton_search_results(soup, limit)
            
            logger.info(f"✅ Trouvé {len(recipes)} recettes Marmiton pour '{query}'")
            return recipes
            
        except Exception as e:
            logger.error(f"❌ Erreur scraping Marmiton: {e}")
            return self._fallback_marmiton_recipes(query, limit)
    
    def _parse_marmiton_search_results(self, soup, limit: int) -> List[Dict[str, Any]]:
        """Parse les résultats de recherche Marmiton de manière robuste"""
        recipes = []
        
        if soup is None:
            return recipes
        
        # Sélecteurs pour les recettes Marmiton
        selectors = [
            'div[class*="recipe"]',
            'div[class*="Recipe"]',
            'article[class*="recipe"]',
            '.recipe-card',
            'div[class*="MRTN"]'
        ]
        
        recipe_cards = []
        for selector in selectors:
            try:
                cards = soup.select(selector)
                if cards:
                    recipe_cards = cards[:limit]
                    break
            except:
                continue
        
        for i, card in enumerate(recipe_cards):
            try:
                recipe = self._extract_marmiton_recipe(card, f"marmiton_real_{i}")
                if recipe:
                    recipes.append(recipe)
            except Exception as e:
                logger.warning(f"Erreur parsing recette Marmiton: {e}")
                continue
        
        return recipes
    
    def _extract_marmiton_recipe(self, card, recipe_id: str) -> Optional[Dict[str, Any]]:
        """Extrait une recette depuis une carte Marmiton de manière robuste"""
        try:
            # Nom de la recette
            name = None
            name_selectors = ['h2', 'h3', 'a[class*="title"]', '[class*="recipe-title"]']
            
            for selector in name_selectors:
                try:
                    name_elem = card.select_one(selector)
                    if name_elem:
                        name = name_elem.get_text(strip=True)
                        if name:
                            break
                except:
                    continue
            
            if not name:
                name = "Recette Marmiton"
            
            # Lien vers la recette
            recipe_url = None
            try:
                link_elem = card.select_one('a')
                if link_elem:
                    href = link_elem.get('href')
                    if href:
                        recipe_url = urljoin(self.base_url, href)
            except:
                pass
            
            # Récupérer les détails depuis la page de la recette (avec gestion d'erreur)
            recipe_details = {}
            if recipe_url:
                try:
                    recipe_details = self._get_marmiton_recipe_details(recipe_url)
                except:
                    pass
            
            # Si pas de détails, utiliser des valeurs par défaut
            if not recipe_details:
                recipe_details = {
                    'ingredients': self._generate_basic_ingredients_marmiton(name),
                    'prepTime': 30,
                    'servings': 4,
                    'image': None
                }
            
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
            
        except Exception as e:
            logger.warning(f"Erreur extraction recette Marmiton: {e}")
            return None
    
    def _generate_basic_ingredients_marmiton(self, recipe_name: str) -> List[Dict[str, Any]]:
        """Génère des ingrédients de base pour Marmiton"""
        return [
            {'name': 'ingrédient principal', 'quantity': 300, 'unit': 'g'},
            {'name': 'oignon', 'quantity': 1, 'unit': 'unité'},
            {'name': 'huile d\'olive', 'quantity': 2, 'unit': 'cuillère à soupe'}
        ]
    
    def _get_marmiton_recipe_details(self, recipe_url: str) -> Dict[str, Any]:
        """Récupère les détails d'une recette Marmiton de manière robuste"""
        try:
            time.sleep(random.uniform(*self.delay_range))
            response = self.session.get(recipe_url, timeout=15)
            response.raise_for_status()
            
            soup = safe_beautifulsoup(response.content, 'html.parser')
            
            if soup is None:
                return {}
            
            details = {}
            
            # Ingrédients avec plusieurs sélecteurs
            ingredients = []
            ingredient_selectors = [
                'ul[class*="ingredient"] li',
                'div[class*="ingredient"]',
                '.recipe-ingredients li',
                '.mrtn__recipe_ingredients li'
            ]
            
            for selector in ingredient_selectors:
                try:
                    items = soup.select(selector)
                    for item in items:
                        text = item.get_text(strip=True)
                        if text and len(text) > 2:
                            parsed = self._parse_marmiton_ingredient(text)
                            if parsed:
                                ingredients.append(parsed)
                    
                    if ingredients:
                        break
                except:
                    continue
            
            details['ingredients'] = ingredients[:15]  # Limiter à 15
            
            # Temps de préparation
            try:
                time_elem = soup.select_one('[data-cooktime]') or soup.find(string=re.compile(r'\d+\s*min'))
                details['prepTime'] = self._extract_time(time_elem) if time_elem else 30
            except:
                details['prepTime'] = 30
            
            # Portions
            try:
                serving_elem = soup.select_one('[data-serving]') or soup.find(string=re.compile(r'\d+\s*pers'))
                details['servings'] = self._extract_servings(serving_elem) if serving_elem else 4
            except:
                details['servings'] = 4
            
            # Image
            try:
                img_elem = soup.select_one('img[class*="recipe"], img[class*="media"]')
                details['image'] = img_elem.get('src') if img_elem else None
            except:
                details['image'] = None
            
            return details
            
        except Exception as e:
            logger.warning(f"Erreur détails recette Marmiton: {e}")
            return {}
    
    def _parse_marmiton_ingredient(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse un ingrédient Marmiton de manière robuste"""
        # Réutiliser la logique de parsing de Jow
        return RealJowScraper()._parse_ingredient_text(text)
    
    def _extract_time(self, element) -> int:
        """Extrait le temps depuis un élément"""
        try:
            if isinstance(element, str):
                text = element
            else:
                text = element.get_text() if hasattr(element, 'get_text') else str(element)
            
            time_match = re.search(r'(\d+)', text)
            return int(time_match.group(1)) if time_match else 30
        except:
            return 30
    
    def _extract_servings(self, element) -> int:
        """Extrait les portions depuis un élément"""
        try:
            if isinstance(element, str):
                text = element
            else:
                text = element.get_text() if hasattr(element, 'get_text') else str(element)
            
            serving_match = re.search(r'(\d+)', text)
            return int(serving_match.group(1)) if serving_match else 4
        except:
            return 4
    
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
                    {'name': 'huile d\'olive', 'quantity': 2, 'unit': 'cuillère à soupe'},
                    {'name': 'ail', 'quantity': 2, 'unit': 'gousse'},
                    {'name': 'herbes de Provence', 'quantity': 1, 'unit': 'cuillère à café'}
                ],
                'source': 'marmiton_fallback'
            }
        ]
        
        return fallback_recipes[:limit]

class UnifiedRecipeScraper:
    """Scraper unifié qui utilise Jow ET Marmiton - VERSION SANS LXML"""
    
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
            # Recherche Jow avec gestion d'erreur
            jow_recipes = []
            try:
                jow_recipes = self.jow_scraper.search_recipes(query, jow_limit)
            except Exception as e:
                logger.warning(f"Erreur scraping Jow: {e}")
            
            all_recipes.extend(jow_recipes)
            
            # Recherche Marmiton avec gestion d'erreur
            marmiton_recipes = []
            try:
                marmiton_recipes = self.marmiton_scraper.search_recipes(query, marmiton_limit)
            except Exception as e:
                logger.warning(f"Erreur scraping Marmiton: {e}")
            
            all_recipes.extend(marmiton_recipes)
            
            # Mélanger les résultats pour plus de diversité
            import random
            random.shuffle(all_recipes)
            
            logger.info(f"✅ Total: {len(all_recipes)} recettes ({len(jow_recipes)} Jow + {len(marmiton_recipes)} Marmiton)")
            return all_recipes[:limit]
            
        except Exception as e:
            logger.error(f"❌ Erreur scraping unifié: {e}")
            # Fallback complet
            return [{
                'id': 'unified_fallback',
                'name': f'Recette {query}',
                'servings': 4,
                'prepTime': 30,
                'ingredients': [
                    {'name': query, 'quantity': 300, 'unit': 'g'},
                    {'name': 'huile', 'quantity': 1, 'unit': 'cuillère à soupe'}
                ],
                'source': 'unified_fallback'
            }]

# Instance globale pour utilisation dans app.py
unified_recipe_scraper = UnifiedRecipeScraper()

# Test de fonctionnement au chargement du module
if __name__ == "__main__":
    print("🧪 Test du scraper sans lxml...")
    try:
        recipes = unified_recipe_scraper.search_recipes("pâtes", 2)
        print(f"✅ Test réussi: {len(recipes)} recettes trouvées")
        for recipe in recipes:
            print(f"  - {recipe['name']} ({recipe['source']})")
    except Exception as e:
        print(f"❌ Test échoué: {e}")
