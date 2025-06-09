#!/bin/bash
echo "🔄 Mise à jour Smart Shopping depuis GitHub..."

cd ~/smart_shopping

# Arrêter le service
sudo systemctl stop smart-shopping

# Télécharger les dernières versions
echo "📥 Téléchargement app_test.py..."
wget -q https://raw.githubusercontent.com/RaphHerve/smart_shopping/main/app_test.py -O app_test.py

echo "📥 Téléchargement app.py..."
wget -q https://raw.githubusercontent.com/RaphHerve/smart_shopping/main/app.py -O app.py

echo "📥 Téléchargement index.html..."
wget -q https://raw.githubusercontent.com/RaphHerve/smart_shopping/main/templates/index.html -O templates/index.html

echo "📥 Téléchargement requirements.txt..."
wget -q https://raw.githubusercontent.com/RaphHerve/smart_shopping/main/requirements.txt -O requirements.txt

echo "📥 Téléchargement utils.py..."
wget -q https://raw.githubusercontent.com/RaphHerve/smart_shopping/main/utils.py -O utils.py

# Permissions
chmod +x app.py app_test.py utils.py

# Mise à jour des dépendances
echo "🐍 Mise à jour dépendances..."
source venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null || echo "⚠️ Certaines dépendances ont échoué (non critique)"

# Redémarrer
echo "🚀 Redémarrage..."
sudo systemctl start smart-shopping

echo "✅ Mise à jour terminée!"
echo "🌐 Application : http://192.168.1.177"

# Status
sleep 3
sudo systemctl status smart-shopping --no-pager
