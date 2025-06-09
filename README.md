# 🛒 Smart Shopping Assistant

Assistant intelligent pour optimiser vos courses et détecter les erreurs de prix, conçu spécialement pour Raspberry Pi.

![Smart Shopping](https://img.shields.io/badge/Smart-Shopping-blue?style=for-the-badge&logo=shopping-cart)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Compatible-red?style=for-the-badge&logo=raspberry-pi)
![Python](https://img.shields.io/badge/Python-3.8+-green?style=for-the-badge&logo=python)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success?style=for-the-badge)

## ✨ Fonctionnalités

### ✅ Implémentées
- **📝 Liste de courses dynamique** avec suggestions intelligentes basées sur vos habitudes
- **🍳 Intégration recettes** (Jow et recettes personnalisées) 
- **💰 Détection d'erreurs de prix Amazon** (réductions > 90%)
- **🏪 Optimisation promos locales** (Carrefour, Leclerc, Lidl)
- **📧 Notifications email automatiques** pour les alertes et promotions
- **📱 Interface web moderne et responsive** avec React
- **🤖 Surveillance automatique** des prix et promotions
- **💾 Sauvegarde automatique** des données
- **🔒 Sécurité avancée** avec firewall et service systemd

### 🚀 Fonctionnalités avancées
- **🧠 IA de suggestions** qui apprend de vos habitudes d'achat
- **📊 Statistiques détaillées** de vos courses et économies
- **🔄 Synchronisation temps réel** entre tous vos appareils
- **📈 Analyse des tendances** de prix sur plusieurs semaines
- **🎯 Recommandations personnalisées** basées sur vos préférences

## 🏃‍♂️ Installation rapide

### Installation automatique (Recommandée)

```bash
curl -sSL https://raw.githubusercontent.com/RaphHerve/smart_shopping/main/install.sh | bash
```

### Installation manuelle

1. **Prérequis système:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install python3 python3-pip python3-venv nginx git sqlite3 curl
   ```

2. **Cloner le projet:**
   ```bash
   git clone https://github.com/RaphHerve/smart_shopping.git
   cd smart_shopping
   ```

3. **Configuration de l'environnement:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Configuration des variables d'environnement:**
   ```bash
   cp .env.example .env
   # Éditer .env avec vos paramètres
   ```

5. **Démarrage:**
   ```bash
   python app.py
   ```

## 🔧 Configuration

### Configuration Email

Pour recevoir les notifications, configurez votre compte Gmail :

1. Allez sur [Google App Passwords](https://myaccount.google.com/apppasswords)
2. Générez un nouveau mot de passe d'application
3. Modifiez le fichier `.env` :
   ```bash
   GMAIL_EMAIL=votre-email@gmail.com
   GMAIL_APP_PASSWORD=votre-mot-de-passe-application
   ```

### Configuration avancée

Le fichier `.env` permet de personnaliser :

```env
# Surveillance des prix
PRICE_CHECK_INTERVAL_HOURS=2
MAX_DISCOUNT_THRESHOLD=90.0

# Notifications
ENABLE_PRICE_ALERTS=true
ENABLE_PROMOTION_ALERTS=true

# Performance
SELENIUM_HEADLESS=true
MAX_CONCURRENT_REQUESTS=5
```

## 📱 Utilisation

### Interface Web

Accédez à l'interface via :
- **Local :** http://localhost
- **Réseau local :** http://[IP-de-votre-Pi]

### Fonctionnalités principales

#### 📝 Liste de courses
- ➕ Ajout d'articles avec catégories automatiques
- ✅ Marquage des articles achetés
- 🔄 Suggestions intelligentes basées sur l'historique
- 📊 Statistiques de vos habitudes d'achat

#### 🍳 Gestion des recettes
- 📖 Ajout de recettes personnalisées
- 🔗 Intégration avec l'API Jow
- 🛒 Ajout automatique des ingrédients à la liste
- 👥 Calcul des portions et ajustement des quantités

#### 💰 Surveillance des prix
- 🔍 Vérification automatique toutes les 2 heures
- 🚨 Alertes pour les réductions > 90%
- 📧 Notifications email instantanées
- 📈 Historique des prix et tendances

#### 🏪 Promotions locales
- 🔄 Surveillance quotidienne (Carrefour, Leclerc, Lidl)
- 📊 Comparaison des prix entre magasins
- 📅 Suivi des dates de validité
- 🎯 Recommandations personnalisées

## 🏗️ Architecture

```
Smart Shopping Assistant
├── 🐍 Backend (Python Flask)
│   ├── app.py - Application principale
│   ├── Database Manager - Gestion SQLite
│   ├── Price Monitor - Surveillance prix
│   ├── Recipe Manager - Gestion recettes
│   └── Notification Manager - Emails
├── 🌐 Frontend (React)
│   ├── Interface responsive
│   ├── Composants modulaires
│   └── Real-time updates
├── 🗄️ Base de données (SQLite)
│   ├── shopping_list - Liste de courses
│   ├── recipes - Recettes
│   ├── price_alerts - Alertes prix
│   └── local_promotions - Promotions
└── ⚙️ Infrastructure
    ├── Nginx - Reverse proxy
    ├── Systemd - Service daemon
    ├── Cron - Tâches planifiées
    └── UFW - Firewall
```

## 📊 API Endpoints

### Liste de courses
```http
GET    /api/shopping-list          # Récupérer la liste
POST   /api/shopping-list          # Ajouter un article
PUT    /api/shopping-list/{id}     # Modifier un article
DELETE /api/shopping-list/{id}     # Supprimer un article
```

### Recettes
```http
GET    /api/recipes                # Récupérer les recettes
POST   /api/recipes                # Ajouter une recette
POST   /api/recipes/{id}/add-to-list # Ajouter à la liste
```

### Prix et promotions
```http
GET    /api/price-alerts           # Récupérer les alertes
GET    /api/promotions             # Récupérer les promotions
POST   /api/check-prices           # Vérification manuelle
POST   /api/check-promotions       # Vérification manuelle
```

## 🛠️ Développement

### Structure du projet

```
smart_shopping/
├── app.py                 # Application Flask principale
├── templates/
│   └── index.html        # Interface React
├── static/
│   ├── css/             # Styles personnalisés
│   ├── js/              # Scripts supplémentaires
│   └── images/          # Images et icônes
├── logs/                # Fichiers de log
├── backups/             # Sauvegardes automatiques
├── requirements.txt     # Dépendances Python
├── .env                # Variables d'environnement
└── install.sh          # Script d'installation
```

### Tests et développement

```bash
# Mode développement
export FLASK_ENV=development
export FLASK_DEBUG=True
python app.py

# Tests (à implémenter)
python -m pytest tests/

# Linting
flake8 app.py
black app.py
```

## 📈 Monitoring

### Logs système
```bash
# Logs de l'application
sudo journalctl -u smart-shopping -f

# Logs Nginx
sudo tail -f /var/log/nginx/smart-shopping.*.log

# Logs des tâches cron
tail -f /opt/smart-shopping/logs/backup.log
```

### Métriques
- 📊 Nombre d'articles en liste
- 🎯 Alertes de prix détectées
- 🏪 Promotions trouvées
- 📧 Emails envoyés
- 💾 Taille de la base de données

## 🔐 Sécurité

### Mesures implémentées
- 🔒 **Firewall UFW** configuré automatiquement
- 🛡️ **Service systemd** avec restrictions de sécurité
- 🔐 **Variables d'environnement** pour les secrets
- 📝 **Logs sécurisés** avec rotation automatique
- 🚫 **Pas de stockage des mots de passe** en clair

### Bonnes pratiques
- 🔑 Utilisez toujours des mots de passe d'application Gmail
- 🔄 Changez régulièrement les clés secrètes
- 📊 Surveillez les logs pour les accès suspects
- 💾 Effectuez des sauvegardes régulières

## 💾 Sauvegarde et restauration

### Sauvegarde automatique
- 📅 **Quotidienne à 3h** du matin
- 💿 **Base de données SQLite** complète
- ⚙️ **Configuration** (.env, requirements.txt)
- 🗂️ **Rétention 30 jours** automatique

### Sauvegarde manuelle
```bash
# Sauveg
