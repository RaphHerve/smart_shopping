#!/bin/bash
# Script d'installation pour Smart Shopping sur Raspberry Pi Ubuntu Server

echo "🚀 Installation Smart Shopping sur Raspberry Pi..."

# Mise à jour du système
echo "📦 Mise à jour du système..."
sudo apt update && sudo apt upgrade -y

# Installation des dépendances système
echo "🔧 Installation des dépendances..."
sudo apt install -y python3 python3-pip python3-venv nginx git sqlite3 curl

# Création du répertoire de l'application
echo "📁 Création du répertoire d'application..."
sudo mkdir -p /opt/smart-shopping
sudo chown $USER:$USER /opt/smart-shopping
cd /opt/smart-shopping

# Création de l'environnement virtuel Python
echo "🐍 Configuration environnement Python..."
python3 -m venv venv
source venv/bin/activate

# Installation des paquets Python
echo "📚 Installation des paquets Python..."
cat > requirements.txt << EOF
Flask==2.3.3
Flask-CORS==4.0.0
requests==2.31.0
beautifulsoup4==4.12.2
schedule==1.2.0
lxml==4.9.3
python-dotenv==1.0.0
gunicorn==21.2.0
selenium==4.15.0
fake-useragent==1.4.0
EOF

pip install -r requirements.txt

# Création de la structure des dossiers
echo "📂 Création de la structure..."
mkdir -p {templates,static/{css,js},logs}

# Configuration Nginx
echo "🌐 Configuration Nginx..."
sudo tee /etc/nginx/sites-available/smart-shopping << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias /opt/smart-shopping/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Activation du site Nginx
sudo ln -sf /etc/nginx/sites-available/smart-shopping /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Service systemd pour l'application
echo "⚙️ Configuration du service systemd..."
sudo tee /etc/systemd/system/smart-shopping.service << EOF
[Unit]
Description=Smart Shopping Flask App
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/smart-shopping
Environment=PATH=/opt/smart-shopping/venv/bin
ExecStart=/opt/smart-shopping/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Template HTML pour servir l'application React
echo "🎨 Création du template HTML..."
cat > templates/index.html << 'EOF'
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Shopping Assistant</title>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body>
    <div id="root"></div>
    
    <script type="text/babel">
    // Ici on intégrera le code React de l'interface
    // Version simplifiée pour le serveur Flask
    
    const { useState, useEffect } = React;
    
    const App = () => {
        const [shoppingList, setShoppingList] = useState([]);
        const [newItem, setNewItem] = useState('');
        const [activeTab, setActiveTab] = useState('shopping');
        const [frequentItems, setFrequentItems] = useState([]);
        const [recipes, setRecipes] = useState([]);
        const [priceAlerts, setPriceAlerts] = useState([]);
        
        const API_BASE = '';
        
        // Charger les données
        useEffect(() => {
            fetchShoppingList();
            fetchFrequentItems();
            fetchRecipes();
            fetchPriceAlerts();
        }, []);
        
        const fetchShoppingList = async () => {
            try {
                const response = await fetch(`${API_BASE}/api/shopping-list`);
                const data = await response.json();
                setShoppingList(data);
            } catch (error) {
                console.error('Erreur chargement liste:', error);
            }
        };
        
        const fetchFrequentItems = async () => {
            try {
                const response = await fetch(`${API_BASE}/api/frequent-items`);
                const data = await response.json();
                setFrequentItems(data);
            } catch (error) {
                console.error('Erreur chargement suggestions:', error);
            }
        };
        
        const fetchRecipes = async () => {
            try {
                const response = await fetch(`${API_BASE}/api/recipes`);
                const data = await response.json();
                setRecipes(data);
            } catch (error) {
                console.error('Erreur chargement recettes:', error);
            }
        };
        
        const fetchPriceAlerts = async () => {
            try {
                const response = await fetch(`${API_BASE}/api/price-alerts`);
                const data = await response.json();
                setPriceAlerts(data);
            } catch (error) {
                console.error('Erreur chargement alertes:', error);
            }
        };
        
        const addItem = async (name, category = 'Divers') => {
            if (!name.trim()) return;
            
            try {
                const response = await fetch(`${API_BASE}/api/shopping-list`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ name, category }),
                });
                
                if (response.ok) {
                    fetchShoppingList();
                    setNewItem('');
                }
            } catch (error) {
                console.error('Erreur ajout article:', error);
            }
        };
        
        const toggleItem = async (id, checked) => {
            try {
                await fetch(`${API_BASE}/api/shopping-list/${id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ checked }),
                });
                fetchShoppingList();
            } catch (error) {
                console.error('Erreur modification article:', error);
            }
        };
        
        const removeItem = async (id) => {
            try {
                await fetch(`${API_BASE}/api/shopping-list/${id}`, {
                    method: 'DELETE',
                });
                fetchShoppingList();
            } catch (error) {
                console.error('Erreur suppression article:', error);
            }
        };
        
        const addRecipeToList = async (recipeId) => {
            try {
                const response = await fetch(`${API_BASE}/api/recipes/${recipeId}/add-to-list`, {
                    method: 'POST',
                });
                
                if (response.ok) {
                    const result = await response.json();
                    alert(`${result.added_count} ingrédients ajoutés pour "${result.recipe_name}"`);
                    fetchShoppingList();
                }
            } catch (error) {
                console.error('Erreur ajout recette:', error);
            }
        };
        
        // Interface simplifiée pour le serveur
        return (
            <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
                <div className="max-w-4xl mx-auto">
                    <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
                        <h1 className="text-3xl font-bold text-gray-800 mb-2">
                            🛒 Smart Shopping Assistant
                        </h1>
                        <p className="text-gray-600">
                            Serveur: Raspberry Pi • Status: En ligne
                        </p>
                    </div>
                    
                    <div className="bg-white rounded-xl shadow-lg p-6">
                        <div className="text-center py-12">
                            <i className="fas fa-cog fa-spin text-4xl text-blue-500 mb-4"></i>
                            <h2 className="text-xl font-semibold text-gray-800 mb-2">
                                Application en cours de démarrage...
                            </h2>
                            <p className="text-gray-600">
                                Le serveur Flask est maintenant configuré !
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        );
    };
    
    ReactDOM.render(<App />, document.getElementById('root'));
    </script>
</body>
</html>
EOF

# Configuration des variables d'environnement
echo "🔒 Configuration des variables d'environnement..."
cat > .env << EOF
# Configuration Smart Shopping
FLASK_ENV=production
FLASK_DEBUG=False

# Configuration Email Gmail
GMAIL_EMAIL=rapherv@gmail.com
GMAIL_APP_PASSWORD=

# Configuration base de données
DB_PATH=smart_shopping.db

# Configuration scraping
USER_AGENT=Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36
EOF

# Permissions
echo "🔐 Configuration des permissions..."
sudo chown -R $USER:$USER /opt/smart-shopping
chmod +x /opt/smart-shopping/app.py

# Démarrage des services
echo "🚀 Démarrage des services..."
sudo systemctl daemon-reload
sudo systemctl enable smart-shopping
sudo systemctl start smart-shopping
sudo systemctl enable nginx
sudo systemctl start nginx

# Configuration du firewall
echo "🔥 Configuration du firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Affichage des informations finales
echo ""
echo "✅ Installation terminée !"
echo ""
echo "📊 Status des services:"
sudo systemctl status smart-shopping --no-pager -l
echo ""
sudo systemctl status nginx --no-pager -l
echo ""
echo "🌐 Votre application est accessible à:"
echo "   - Localement: http://localhost"
echo "   - Réseau local: http://$(hostname -I | cut -d' ' -f1)"
echo ""
echo "📧 Configuration email à faire:"
echo "   1. Aller sur https://myaccount.google.com/apppasswords"
echo "   2. Générer un mot de passe d'application"
echo "   3. Modifier /opt/smart-shopping/.env"
echo ""
echo "🔧 Commandes utiles:"
echo "   - Logs: sudo journalctl -u smart-shopping -f"
echo "   - Redémarrer: sudo systemctl restart smart-shopping"
echo "   - Arrêter: sudo systemctl stop smart-shopping"
echo ""
echo "📁 Fichiers de l'application dans: /opt/smart-shopping"
