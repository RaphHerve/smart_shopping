# 📝 TODO Smart Shopping Assistant

## 🎯 NOUVELLE VISION : "DÉCOUVERTE → VALIDATION → IA"

### 🔥 PHASE 1 - SYSTÈME DÉCOUVERTE (Priorité absolue)

#### Cette semaine
- [ ] **Créer onglet "Découvrir"** dans l'interface
  - [ ] Nouveau composant React pour découverte
  - [ ] Séparation claire avec "Mes Recettes"
  - [ ] Interface de recherche dédiée

- [ ] **Système validation recettes** 
  - [ ] Boutons ❤️ "J'aime" / ❌ "Pas intéressé" 
  - [ ] API endpoint pour sauvegarder validation
  - [ ] Preview recettes avec photo + ingrédients

- [ ] **Finaliser consolidation UI**
  - [ ] Badges "CONSOLIDÉ" visibles dans l'interface
  - [ ] Affichage quantités cumulées correctes
  - [ ] Messages "Présent dans X recettes"

#### Semaine suivante  
- [ ] **Scraper Marmiton**
  - [ ] Extension du scraper Jow vers Marmiton
  - [ ] Parser HTML Marmiton pour recettes
  - [ ] Extraction images + temps de préparation

- [ ] **Base recettes validées**
  - [ ] Table `validated_recipes` en BDD
  - [ ] Migration des recettes existantes
  - [ ] Gestion tags personnalisés

### 🧠 PHASE 2 - RECHERCHE INTELLIGENTE (1 mois)

- [ ] **Recherche par ingrédients multiples**
  - [ ] Input ["saumon", "courgettes", "riz"]
  - [ ] Algorithme score de pertinence
  - [ ] Tri par nombre d'ingrédients matchés

- [ ] **Filtres avancés**
  - [ ] Temps de préparation (< 30min, 30-60min, > 1h)
  - [ ] Difficulté (Facile, Moyen, Difficile)
  - [ ] Type de cuisine (Italien, Asiatique, Français...)
  - [ ] Régime alimentaire (Végé, Vegan, Sans gluten...)

- [ ] **"Scan frigo virtuel"**
  - [ ] Liste ingrédients disponibles
  - [ ] Suggestions "Que cuisiner avec ça ?"
  - [ ] Optimisation anti-gaspillage

### 🤖 PHASE 3 - IA PRÉDICTIVE (2-3 mois)

- [ ] **Machine Learning habitudes**
  - [ ] Analyse ingrédients fréquents
  - [ ] Détection types de cuisine préférés
  - [ ] Temps de préparation moyen préféré

- [ ] **Recommandations contextuelles**
  - [ ] Lundi soir → Recettes rapides (< 30min)
  - [ ] Weekend → Recettes élaborées
  - [ ] Saison → Légumes de saison
  - [ ] Météo → Soupes si froid, salades si chaud

- [ ] **Optimisation courses**
  - [ ] "3 recettes utilisent des tomates cette semaine"
  - [ ] "Achetez des courgettes, 4 recettes possibles"
  - [ ] Planning repas intelligent

## ✅ TERMINÉ AUJOURD'HUI (11 juin 2025)
- ✅ **Consolidation intelligente** opérationnelle
- ✅ **Scraper Jow intelligent** 10+ types de plats
- ✅ **Schema BDD étendu** quantités/unités
- ✅ **API consolidation** avancée
- ✅ **Parser ingrédients** avec quantités
- ✅ **Normalisation ingrédients** (spaghetti = pâtes)
- ✅ **Conversion unités** automatique
- ✅ **Tests validation** recherches wraps/burger/salade

## 🚫 ABANDONNÉ / REPORTÉ

### Abandonné définitivement
- ~~API Jow officielle~~ → Scraper maison plus fiable
- ~~Recherche temps réel~~ → Approche validation locale
- ~~Cache externe~~ → Base personnelle 

### Reporté après IA
- [ ] Application mobile (Phase 4)
- [ ] Mode collaboratif (Phase 4) 
- [ ] Reconnaissance vocale (Phase 5)
- [ ] Scanner codes-barres (Phase 5)

## 🛠️ TECHNIQUE & INFRASTRUCTURE

### À faire prochainement
- [ ] **SSL/HTTPS** pour accès externe sécurisé
- [ ] **Backup automatique** quotidien BDD
- [ ] **Monitoring** performance + erreurs
- [ ] **Tests automatisés** endpoints critiques

### Améliorations UX
- [ ] **Mode sombre/clair** 
- [ ] **Notifications push** dans l'interface
- [ ] **Raccourcis clavier** (Ctrl+A pour ajouter)
- [ ] **Glisser-déposer** pour réorganiser
- [ ] **Historique listes** précédentes

## 📧 NOTIFICATIONS & PROMOTIONS

### Court terme (après Phase 1)
- [ ] **Configuration email** notifications
- [ ] **Surveillance promotions** magasins locaux
- [ ] **Détection erreurs prix** Amazon (> 90% réduction)
- [ ] **Alertes recettes** selon promotions détectées

### Moyen terme  
- [ ] **Comparateur prix** entre magasins
- [ ] **Géolocalisation** magasins les moins chers
- [ ] **Export listes** vers autres apps (Bring, Google Keep)

## 🎯 OBJECTIFS PAR PHASE

### Phase 1 - Découverte (3 semaines)
**Objectif :** Interface découverte + validation fonctionnelle  
**Success metric :** 50+ recettes validées en base personnelle

### Phase 2 - Recherche intelligente (4 semaines)
**Objectif :** Recherche par ingrédients + filtres avancés  
**Success metric :** Trouve recettes pertinentes avec 2-3 ingrédients

### Phase 3 - IA prédictive (8 semaines)  
**Objectif :** Recommandations automatiques personnalisées  
**Success metric :** 80% de suggestions acceptées par l'utilisateur

---

**Prochaine session :** Création onglet "Découvrir" 🔍  
**Priorité #1 :** Interface validation ❤️/❌  
**État d'esprit :** Evolution progressive, chaque phase apporte de la valeur ! 🚀

**Bonne nuit ! 😴** Le système de consolidation fonctionne, maintenant cap sur la découverte intelligente ! ✨
