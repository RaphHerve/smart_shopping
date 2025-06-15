#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour valider le fonctionnement SANS LXML
À exécuter après les corrections pour valider le setup
"""

import sys
import traceback

def test_imports():
    """Test tous les imports critiques"""
    print("🧪 Test des imports...")
    
    tests = [
        ("BeautifulSoup", "from bs4 import BeautifulSoup"),
        ("html5lib", "import html5lib"),
        ("requests", "import requests"),
        ("Flask", "from flask import Flask"),
        ("Flask-Limiter", "from flask_limiter import Limiter"),
        ("fake_useragent", "from fake_useragent import UserAgent"),
        ("redis", "import redis"),
    ]
    
    results = {}
    
    for name, import_cmd in tests:
        try:
            exec(import_cmd)
            results[name] = "✅ OK"
            print(f"  {name}: ✅ OK")
        except ImportError as e:
            results[name] = f"❌ ERREUR: {e}"
            print(f"  {name}: ❌ ERREUR: {e}")
        except Exception as e:
            results[name] = f"⚠️  PROBLÈME: {e}"
            print(f"  {name}: ⚠️  PROBLÈME: {e}")
    
    return results

def test_beautifulsoup_parsers():
    """Test des différents parsers BeautifulSoup"""
    print("\n🧪 Test des parsers BeautifulSoup...")
    
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("❌ BeautifulSoup non disponible")
        return False
    
    test_html = "<html><body><h1>Test</h1><p>Parser test</p></body></html>"
    
    parsers_to_test = [
        'html.parser',
        'html5lib',
        'lxml',
        'lxml-xml'
    ]
    
    working_parsers = []
    
    for parser in parsers_to_test:
        try:
            soup = BeautifulSoup(test_html, parser)
            title = soup.find('h1').get_text()
            if title == "Test":
                working_parsers.append(parser)
                print(f"  {parser}: ✅ OK")
            else:
                print(f"  {parser}: ⚠️  Parse incorrect")
        except Exception as e:
            print(f"  {parser}: ❌ ERREUR: {e}")
    
    print(f"\n✅ Parsers fonctionnels: {working_parsers}")
    return len(working_parsers) > 0

def test_scraper_import():
    """Test de l'import du scraper"""
    print("\n🧪 Test import scraper...")
    
    try:
        from real_jow_marmiton_scraper import unified_recipe_scraper
        print("✅ Scraper importé avec succès")
        return True
    except ImportError as e:
        print(f"❌ Erreur import scraper: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Problème import scraper: {e}")
        return False

def test_scraper_functionality():
    """Test de fonctionnalité basique du scraper"""
    print("\n🧪 Test fonctionnalité scraper...")
    
    try:
        from real_jow_marmiton_scraper import unified_recipe_scraper
        
        # Test simple
        recipes = unified_recipe_scraper.search_recipes("test", 1)
        
        if recipes and len(recipes) > 0:
            recipe = recipes[0]
            print(f"✅ Scraper fonctionnel: trouvé '{recipe['name']}'")
            print(f"  Source: {recipe.get('source', 'unknown')}")
            print(f"  Ingrédients: {len(recipe.get('ingredients', []))}")
            return True
        else:
            print("⚠️  Scraper retourne des résultats vides")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test scraper: {e}")
        traceback.print_exc()
        return False

def test_quantity_manager():
    """Test du gestionnaire de quantités"""
    print("\n🧪 Test gestionnaire quantités...")
    
    try:
        from intelligent_quantity_manager import get_ingredient_manager
        
        # Test basique
        manager = get_ingredient_manager(":memory:")  # Base en mémoire pour test
        print("✅ Gestionnaire quantités importé")
        return True
        
    except ImportError as e:
        print(f"❌ Erreur import gestionnaire: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Problème gestionnaire: {e}")
        return False

def test_flask_app():
    """Test basique de l'app Flask"""
    print("\n🧪 Test app Flask...")
    
    try:
        from app import app
        
        with app.test_client() as client:
            # Test route de santé
            response = client.get('/api/health')
            
            if response.status_code == 200:
                print("✅ App Flask fonctionnelle")
                return True
            else:
                print(f"⚠️  App Flask retourne code {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Erreur test Flask: {e}")
        return False

def main():
    """Fonction principale de test"""
    print("=" * 60)
    print("🔬 SMART SHOPPING - TEST SANS LXML")
    print("=" * 60)
    
    all_tests = [
        ("Imports", test_imports),
        ("Parsers BeautifulSoup", test_beautifulsoup_parsers),
        ("Import Scraper", test_scraper_import),
        ("Fonctionnalité Scraper", test_scraper_functionality),
        ("Gestionnaire Quantités", test_quantity_manager),
        ("App Flask", test_flask_app),
    ]
    
    results = {}
    
    for test_name, test_func in all_tests:
        try:
            result = test_func()
            results[test_name] = "✅ OK" if result else "❌ ÉCHEC"
        except Exception as e:
            results[test_name] = f"💥 ERREUR: {e}"
            print(f"💥 Erreur inattendue dans {test_name}: {e}")
    
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    all_ok = True
    for test_name, result in results.items():
        print(f"{test_name:25}: {result}")
        if "❌" in result or "💥" in result:
            all_ok = False
    
    print("\n" + "=" * 60)
    
    if all_ok:
        print("🎉 TOUS LES TESTS SONT PASSÉS!")
        print("✅ Votre application devrait fonctionner sans lxml")
        print("\n🚀 Vous pouvez maintenant lancer: python3 app.py")
    else:
        print("⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print("🔧 Vérifiez les erreurs ci-dessus et corrigez-les")
        print("\n📋 Actions recommandées:")
        print("  1. pip install -r requirements.txt --no-cache-dir")
        print("  2. Vérifiez que tous les fichiers sont présents")
        print("  3. Relancez ce script de test")
    
    print("=" * 60)
    
    return all_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
