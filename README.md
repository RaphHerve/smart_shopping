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
# Sauvegarde complète
/opt/smart-shopping/backup.sh

# Sauvegarde base de données uniquement
sqlite3 /opt/smart-shopping/smart_shopping.db ".backup backup_$(date +%Y%m%d).db"

# Sauvegarde configuration
tar -czf config_backup.tar.gz /opt/smart-shopping/.env /opt/smart-shopping/requirements.txt
```

### Restauration
```bash
# Arrêter l'application
sudo systemctl stop smart-shopping

# Restaurer la base de données
sqlite3 /opt/smart-shopping/smart_shopping.db ".restore /path/to/backup.db"

# Redémarrer l'application
sudo systemctl start smart-shopping
```

## 🔧 Maintenance

### Commandes utiles

```bash
# Statut des services
sudo systemctl status smart-shopping nginx

# Redémarrage
sudo systemctl restart smart-shopping

# Mise à jour des dépendances
cd /opt/smart-shopping
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart smart-shopping

# Nettoyage des logs
sudo journalctl --vacuum-time=30d

# Vérification de l'espace disque
df -h /opt/smart-shopping
```

### Mise à jour de l'application

```bash
# Télécharger la dernière version
cd /opt/smart-shopping
git pull origin main

# Mettre à jour les dépendances
source venv/bin/activate
pip install -r requirements.txt

# Redémarrer les services
sudo systemctl restart smart-shopping nginx
```

## 🐛 Dépannage

### Problèmes courants

#### ❌ L'application ne démarre pas
```bash
# Vérifier les logs
sudo journalctl -u smart-shopping -n 50

# Vérifier la configuration
cd /opt/smart-shopping
source venv/bin/activate
python -c "from app import app; print('Configuration OK')"

# Vérifier les permissions
ls -la /opt/smart-shopping/
```

#### ❌ Les emails ne fonctionnent pas
```bash
# Tester la configuration email
curl -X POST http://localhost/api/send-test-email

# Vérifier les variables d'environnement
grep GMAIL /opt/smart-shopping/.env

# Logs d'erreur email
sudo journalctl -u smart-shopping | grep -i email
```

#### ❌ Nginx retourne une erreur 502
```bash
# Vérifier que l'app Flask fonctionne
curl http://127.0.0.1:5000

# Vérifier la configuration Nginx
sudo nginx -t
sudo systemctl status nginx

# Redémarrer Nginx
sudo systemctl restart nginx
```

#### ❌ Base de données corrompue
```bash
# Vérifier l'intégrité
sqlite3 /opt/smart-shopping/smart_shopping.db "PRAGMA integrity_check;"

# Restaurer depuis une sauvegarde
cp /opt/smart-shopping/backups/smart_shopping_YYYYMMDD.db /opt/smart-shopping/smart_shopping.db
sudo systemctl restart smart-shopping
```

### Diagnostics avancés

```bash
# Script de diagnostic complet
cat > diagnostic.sh << 'EOF'
#!/bin/bash
echo "=== Diagnostic Smart Shopping ==="
echo "Date: $(date)"
echo ""

echo "1. Services:"
systemctl is-active smart-shopping nginx
echo ""

echo "2. Ports:"
netstat -tlnp | grep -E ':80|:5000'
echo ""

echo "3. Espace disque:"
df -h /opt/smart-shopping
echo ""

echo "4. Processus:"
ps aux | grep -E 'gunicorn|nginx' | head -5
echo ""

echo "5. Dernières erreurs:"
journalctl -u smart-shopping --since "1 hour ago" | grep -i error | tail -5
echo ""

echo "6. Base de données:"
ls -lh /opt/smart-shopping/smart_shopping.db
echo ""

echo "7. Configuration réseau:"
ip addr show | grep inet
EOF

chmod +x diagnostic.sh
./diagnostic.sh
```

## 📈 Performance

### Optimisations implémentées

- **🔄 Pool de connexions** pour la base de données
- **📦 Compression Gzip** pour les ressources statiques
- **⚡ Cache navigateur** pour les assets CSS/JS
- **🎯 Requêtes optimisées** avec index SQLite
- **🚀 Workers Gunicorn** pour la parallélisation

### Monitoring des performances

```bash
# Utilisation CPU/Mémoire
htop
# ou
ps aux | grep gunicorn

# Taille de la base de données
sqlite3 /opt/smart-shopping/smart_shopping.db ".dbinfo"

# Temps de réponse
curl -w "@curl-format.txt" -o /dev/null -s http://localhost/api/shopping-list
```

## 🌟 Fonctionnalités futures

### Roadmap v2.1
- [ ] 📱 **Application mobile** (React Native)
- [ ] 🔗 **API publique** avec authentification
- [ ] 🛒 **Intégration caddies connectés**
- [ ] 🏪 **Géolocalisation** des magasins
- [ ] 💳 **Suivi des dépenses** et budgets

### Roadmap v2.2
- [ ] 🤖 **Assistant vocal** (Alexa/Google)
- [ ] 📊 **Dashboard analytics** avancé
- [ ] 🔄 **Synchronisation multi-utilisateurs**
- [ ] 🎯 **IA prédictive** pour les courses
- [ ] 🌍 **Support multi-langues**

## 🤝 Contribution

### Comment contribuer

1. **Fork** le projet
2. **Créer** une branche feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** vos changements (`git commit -m 'Add AmazingFeature'`)
4. **Push** vers la branche (`git push origin feature/AmazingFeature`)
5. **Ouvrir** une Pull Request

### Guidelines

- 📝 Suivre les conventions de code Python (PEP 8)
- ✅ Ajouter des tests pour les nouvelles fonctionnalités
- 📚 Documenter les changements dans le README
- 🔄 Tester sur Raspberry Pi avant de soumettre

## 📄 Licence

Distribué sous licence MIT. Voir `LICENSE` pour plus d'informations.

## 👨‍💻 Auteur

**Raphaël Herve** - [@RaphHerve](https://github.com/RaphHerve)

- 📧 Email: rapherv@gmail.com
- 🐙 GitHub: [RaphHerve/smart_shopping](https://github.com/RaphHerve/smart_shopping)

## 🙏 Remerciements

- [Flask](https://flask.palletsprojects.com/) - Framework web Python
- [React](https://reactjs.org/) - Bibliothèque JavaScript pour l'interface
- [Tailwind CSS](https://tailwindcss.com/) - Framework CSS utilitaire
- [SQLite](https://www.sqlite.org/) - Base de données légère
- [Nginx](https://nginx.org/) - Serveur web haute performance
- [Raspberry Pi Foundation](https://www.raspberrypi.org/) - Plateforme matérielle

## 📞 Support

### Canaux de support

- 🐛 **Issues GitHub** : [Ouvrir une issue](https://github.com/RaphHerve/smart_shopping/issues)
- 💬 **Discussions** : [GitHub Discussions](https://github.com/RaphHerve/smart_shopping/discussions)
- 📧 **Email** : rapherv@gmail.com

### FAQ

**Q: Puis-je utiliser Smart Shopping sur un autre système que Raspberry Pi ?**
R: Oui, le code est compatible avec Ubuntu/Debian. Adaptez simplement le script d'installation.

**Q: Les données sont-elles sécurisées ?**
R: Toutes les données restent locales sur votre Raspberry Pi. Aucune donnée n'est envoyée vers des serveurs externes.

**Q: Puis-je personnaliser les magasins surveillés ?**
R: Actuellement Carrefour, Leclerc et Lidl sont supportés. D'autres magasins peuvent être ajoutés en modifiant le code.

**Q: L'application fonctionne-t-elle hors ligne ?**
R: L'interface fonctionne hors ligne, mais la surveillance des prix nécessite une connexion internet.

---

<div align="center">

**🛒 Smart Shopping Assistant - Optimisez vos courses avec l'intelligence artificielle! 🛒**

[![Made with ❤️](https://img.shields.io/badge/Made%20with-❤️-red.svg)](https://github.com/RaphHerve/smart_shopping)
[![Raspberry Pi](https://img.shields.io/badge/Optimized%20for-Raspberry%20Pi-red.svg)](https://www.raspberrypi.org/)

</div>
