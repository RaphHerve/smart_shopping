# 🛒 Smart Shopping Assistant

Assistant intelligent pour optimiser vos courses avec IA, conçu spécialement pour Raspberry Pi.

![Smart Shopping](https://img.shields.io/badge/Smart-Shopping-blue?style=for-the-badge&logo=shopping-cart)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Compatible-red?style=for-the-badge&logo=raspberry-pi)
![Python](https://img.shields.io/badge/Python-3.8+-green?style=for-the-badge&logo=python)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success?style=for-the-badge)

## 🎯 Vision : Netflix pour la Cuisine

**Découverte → Validation → IA personnalisée**

Comme Netflix ou Spotify, Smart Shopping apprend vos goûts culinaires pour vous proposer les recettes parfaites, au bon moment, avec la liste de courses optimisée.

## ✨ Fonctionnalités

### ✅ Opérationnelles (v1.0.1)
- **📝 Liste de courses intelligente** avec suggestions et quantités réelles
- **🧠 Consolidation automatique** des ingrédients (détecte doublons)
- **🍳 Gestionnaire de recettes** avec ajout automatique des ingrédients
- **⚡ Recherche recettes** par type de plat (pâtes, wraps, burger, salade...)
- **📱 Interface React moderne** et responsive
- **🔄 Gestion quantités avancée** avec unités automatiques
- **💾 Base de données locale** SQLite sécurisée
- **🌐 Accès réseau** depuis tous vos appareils

### 🚀 Prochainement (v1.1 - Découverte)
- **🔍 Onglet "Découvrir"** pour explorer de nouvelles recettes
- **❤️ Système de validation** (J'aime/Pas intéressé)
- **🕷️ Scraping Marmiton/Jow** pour recettes réelles
- **📚 Base personnelle** de recettes validées uniquement

### 🤖 Roadmap IA (v1.2-1.3)
- **🔎 Recherche par ingrédients** multiples
- **🧠 Recommandations personnalisées** basées sur vos habitudes
- **📈 Optimisation courses** intelligente
- **🎯 Suggestions contextuelles** (rapide en semaine, élaboré le weekend)

## 🏃‍♂️ Installation rapide

### Installation automatique (Recommandée)

```bash
curl -sSL https://raw.githubusercontent.com/RaphHerve/smart_shopping/main/install.sh | bash
```

## 📱 Utilisation

### Interface Web

Accédez à l'interface via :
- **Local :** http://localhost
- **Réseau local :** http://[IP-de-votre-Pi]

### ✨ Nouvelles fonctionnalités

#### 🧠 Consolidation intelligente
- **Détection automatique** des doublons (spaghetti + pennes = pâtes)
- **Calcul quantités** cumulées (200g + 300g = 500g pâtes)
- **Badges visuels** "CONSOLIDÉ" dans l'interface
- **Normalisation** des noms d'ingrédients

#### 🍳 Recherche recettes avancée
- **10+ types de plats** supportés (wraps, burger, salade, curry...)
- **Ingrédients réalistes** avec quantités adaptées
- **Génération dynamique** selon votre recherche
- **Quantités modifiables** avant ajout à la liste

#### 📊 Gestion quantités
- **Unités automatiques** (g, kg, ml, l, cuillères, pincées...)
- **Conversion intelligente** entre unités compatibles  
- **Quantités décimales** pour précision (250.5g)
- **Affichage optimisé** (1500g → 1.5kg)

## 🏗️ Architecture Technique

### Backend Intelligent
```
📊 Consolidation Engine
├── Normalisation noms ingrédients
├── Détection doublons avancée  
├── Conversion unités automatique
└── Calcul quantités cumulées

🔍 Scraper Engine  
├── Jow intelligent (10+ types plats)
├── Génération recettes dynamique
├── Parser ingrédients automatique
└── Support Marmiton (à venir)

💾 Base de Données Étendue
├── Quantités décimales (quantity_decimal)
├── Unités standardisées (unit)
├── Source recettes (recipe_source)  
└── Cache recettes optimisé
```

## 📊 API Endpoints Avancés

### Nouvelles routes intelligentes
```http
POST   /api/jow/search-recipes           # Recherche recettes intelligente
POST   /api/intelligent/consolidate-and-add # Ajout avec consolidation
GET    /api/intelligent/suggestions      # Suggestions personnalisées
POST   /api/intelligent/consolidate      # Consolidation pure
```

### Tests en ligne de commande
```bash
# Test recherche wraps
curl -X POST http://localhost:5000/api/jow/search-recipes \
  -H "Content-Type: application/json" \
  -d '{"query": "wraps", "limit": 2}'

# Test consolidation
curl -X POST http://localhost:5000/api/intelligent/consolidate-and-add \
  -H "Content-Type: application/json" \
  -d '{"recipe": {"name": "Test", "ingredients": [{"name": "pâtes", "quantity": 400, "unit": "g"}]}}'
```

## 🚀 Nouveautés v1.0.1 (11 juin 2025)

### ✅ Réalisé
- **🧠 Algorithme consolidation** des ingrédients opérationnel
- **🔍 Scraper Jow intelligent** avec 10+ types de plats
- **📊 Schema BDD étendu** pour quantités/unités réelles
- **⚡ Parser ingrédients** automatique depuis texte
- **🔄 Conversion unités** automatique (kg↔g, l↔ml)
- **✨ Interface quantités** modifiables en temps réel

### 🧪 Tests validés
- ✅ Recherche "wraps" → Wrap au poulet, Wrap végétarien, Wrap saumon
- ✅ Recherche "burger" → Burger bœuf, Burger poulet avec bons ingrédients  
- ✅ Consolidation pâtes : spaghetti + tagliatelles = pâtes consolidées
- ✅ Quantités cumulées : 400g + 300g = 700g automatiquement

## 🎯 Prochaines Étapes

### Phase 1 - Système Découverte (3 semaines)
1. **Onglet "Découvrir"** séparé de "Mes Recettes"
2. **Système validation** ❤️ J'aime / ❌ Pas intéressé
3. **Scraper Marmiton** extension du système actuel
4. **Base recettes personnelles** enrichie

### Phase 2 - Recherche Intelligente (1 mois)  
1. **Input multiple ingrédients** ["saumon", "courgettes"] 
2. **Score de pertinence** selon ingrédients disponibles
3. **Filtres avancés** (temps, difficulté, type cuisine)
4. **"Scan frigo virtuel"** pour suggestions

### Phase 3 - IA Prédictive (2-3 mois)
1. **Machine Learning** sur vos habitudes culinaires
2. **Recommandations contextuelles** (lundi = rapide, weekend = élaboré)
3. **Optimisation courses** (3 recettes utilisent des tomates)
4. **Suggestions automatiques** façon Netflix

## 🔧 Développement & Contribution

### Structure étendue
```
smart_shopping/
├── app.py                          # Flask principal
├── jow_scraper_intelligent.py      # Scraper recettes intelligent  
├── smart_shopping_intelligent.py   # Engine consolidation
├── templates/index.html            # Interface React complète
├── fix_jow_real_api.py            # Scripts de migration
└── smart_shopping.db              # Base étendue
```

### Développement local
```bash
# Mode développement avec nouvelles fonctionnalités
cd ~/smart_shopping
source venv/bin/activate

# Test consolidation en direct
python3 -c "
from smart_shopping_intelligent import IngredientManager
manager = IngredientManager()
manager.add_ingredient('spaghetti', 400, 'g', 'recipe1', 'Carbonara')  
manager.add_ingredient('pâtes', 300, 'g', 'recipe2', 'Bolognaise')
print(manager.consolidate_shopping_list())
"

# Test scraper intelligent
python3 -c "
from jow_scraper_intelligent import intelligent_jow_scraper
recipes = intelligent_jow_scraper.search_recipes('wraps', 2)
for r in recipes: print(f'{r[\"name\"]} - {len(r[\"ingredients\"])} ingrédients')
"
```

## 🌟 Vision Produit

### 🎯 Objectif Final
**Devenir le "Netflix de la cuisine"** - Une IA qui comprend vos goûts, propose les bonnes recettes au bon moment, et optimise automatiquement vos courses.

### 🚀 Impact Utilisateur
- **⏰ Gain de temps** : Plus de réflexion "qu'est-ce qu'on mange ?"
- **💰 Économies** : Optimisation courses + détection promotions
- **🍽️ Découverte** : Nouvelles recettes adaptées à vos goûts
- **🧠 Simplicité** : L'IA gère la complexité, vous cuisinez

---

**Version actuelle :** v1.0.1 - Consolidation Intelligente  
**Prochaine version :** v1.1 - Système Découverte  
**Dernière mise à jour :** 11 Juin 2025, 23h30  

<div align="center">

**🛒 Smart Shopping Assistant - L'IA qui révolutionne vos courses ! 🤖**

[![Made with ❤️](https://img.shields.io/badge/Made%20with-❤️-red.svg)](https://github.com/RaphHerve/smart_shopping)
[![Raspberry Pi](https://img.shields.io/badge/Optimized%20for-Raspberry%20Pi-red.svg)](https://www.raspberrypi.org/)

</div>
