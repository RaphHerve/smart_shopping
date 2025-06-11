#!/bin/bash
echo "🔧 Correction Smart Shopping Assistant..."

cd ~/smart_shopping

# Arrêter le service
echo "⏹️ Arrêt du service..."
sudo systemctl stop smart-shopping

# Créer les répertoires nécessaires
echo "📁 Création des répertoires..."
mkdir -p templates logs backups

# Vérifier les dépendances critiques
echo "📦 Vérification des dépendances..."
source venv/bin/activate

# Installer les dépendances manquantes une par une
pip install Flask==2.3.3
pip install Flask-CORS==4.0.0 
pip install requests==2.31.0
pip install beautifulsoup4==4.12.2
pip install python-dotenv==1.0.0
pip install fake-useragent==1.4.0

# Vérifier que les fichiers principaux existent
if [ ! -f "app.py" ]; then
    echo "❌ app.py manquant!"
    exit 1
fi

if [ ! -f "smart_shopping_intelligent.py" ]; then
    echo "❌ smart_shopping_intelligent.py manquant!"
    exit 1
fi

# Créer un fichier .env basique si absent
if [ ! -f ".env" ]; then
    echo "📝 Création du fichier .env..."
    cat > .env << EOF
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_SECRET_KEY=smart-shopping-secret-key-$(date +%s)
DB_PATH=smart_shopping.db
GMAIL_EMAIL=rapherv@gmail.com
NOTIFICATION_EMAIL=rapherv@gmail.com
USER_AGENT=Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36
ENABLE_PRICE_ALERTS=true
ENABLE_PROMOTION_ALERTS=true
LOG_LEVEL=INFO
EOF
fi

# Vérifier les permissions
echo "🔐 Correction des permissions..."
chmod +x app.py smart_shopping_intelligent.py
chmod -R 755 templates logs
touch logs/smart_shopping.log
chmod 644 logs/smart_shopping.log

# Test rapide de l'application
echo "🧪 Test de l'application..."
timeout 10s python3 app.py &
APP_PID=$!
sleep 5

if ps -p $APP_PID > /dev/null; then
    echo "✅ L'application démarre correctement"
    kill $APP_PID
else
    echo "❌ Problème au démarrage - vérification des erreurs..."
    python3 -c "
import sys
try:
    from smart_shopping_intelligent import IngredientManager
    print('✅ Module intelligent OK')
except Exception as e:
    print(f'❌ Erreur module intelligent: {e}')

try:
    import flask
    print('✅ Flask OK')
except Exception as e:
    print(f'❌ Erreur Flask: {e}')

try:
    import sqlite3
    print('✅ SQLite OK')
except Exception as e:
    print(f'❌ Erreur SQLite: {e}')
"
fi

# Redémarrer le service
echo "🚀 Redémarrage du service..."
sudo systemctl start smart-shopping

sleep 3

# Vérifier le statut
echo "📊 Statut du service:"
sudo systemctl status smart-shopping --no-pager

echo ""
echo "🌐 Application accessible sur:"
echo "   http://192.168.1.177"
echo "   http://localhost:5000"
echo ""
echo "📋 Pour vérifier les logs:"
echo "   sudo journalctl -u smart-shopping -f"
echo "   tail -f ~/smart_shopping/logs/smart_shopping.log"
