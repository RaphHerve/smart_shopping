#!/bin/bash
# Script d'installation Smart Shopping Assistant v2.0
# Installation complète sur Raspberry Pi Ubuntu Server

set -e  # Arrêter en cas d'erreur

echo "🚀 Installation Smart Shopping Assistant v2.0 sur Raspberry Pi..."

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction d'affichage coloré
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérification des prérequis
check_prerequisites() {
    print_status "Vérification des prérequis..."
    
    # Vérifier si on est sur Raspberry Pi
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        print_warning "Ce script est optimisé pour Raspberry Pi"
    fi
    
    # Vérifier les permissions sudo
    if ! sudo -n true 2>/dev/null; then
        print_error "Ce script nécessite les privilèges sudo"
        exit 1
    fi
    
    print_success "Prérequis vérifiés"
}

# Mise à jour du système
update_system() {
    print_status "Mise à jour du système..."
    sudo apt update && sudo apt upgrade -y
    print_success "Système mis à jour"
}

# Installation des dépendances système
install_dependencies() {
    print_status "Installation des dépendances système..."
    
    # Paquets de base
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        nginx \
        git \
        sqlite3 \
        curl \
        wget \
        unzip \
        cron \
        logrotate
    
    # Chrome/Chromium pour Selenium (optionnel)
    if command -v chromium-browser &> /dev/null; then
        print_success "Chromium déjà installé"
    else
        print_status "Installation de Chromium pour Selenium..."
        sudo apt install -y chromium-browser chromium-chromedriver || print_warning "Chromium non installé - le scraping sera limité"
    fi
    
    print_success "Dépendances installées"
}

# Création de l'environnement de l'application
setup_application_environment() {
    print_status "Configuration de l'environnement d'application..."
    
    # Création du répertoire de l'application
    sudo mkdir -p /opt/smart-shopping
    sudo chown $USER:$USER /opt/smart-shopping
    cd /opt/smart-shopping
    
    # Création de l'environnement virtuel Python
    python3 -m venv venv
    source venv/bin/activate
    
    # Installation des paquets Python
    cat > requirements.txt << 'EOF'
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
python-crontab==3.0.0
psutil==5.9.6
EOF
    
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Création de la structure des dossiers
    mkdir -p {templates,static/{css,js,images},logs,backups,data}
    
    print_success "Environnement d'application configuré"
}

# Téléchargement des fichiers depuis GitHub
download_application_files() {
    print_status "Téléchargement des fichiers de l'application..."
    
    # L'application Flask principale
    curl -sSL https://raw.githubusercontent.com/RaphHerve/smart_shopping/main/app.py -o app.py || cat > app.py << 'EOF'
# Fichier app.py sera créé avec le contenu complet
print("Smart Shopping Assistant - Fichier app.py à configurer")
EOF
    
    # Template HTML
    curl -sSL https://raw.githubusercontent.com/RaphHerve/smart_shopping/main/templates/index.html -o templates/index.html || cat > templates/index.html << 'EOF'
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Shopping Assistant</title>
</head>
<body>
    <div id="root">
        <h1>Smart Shopping Assistant</h1>
        <p>Application en cours de configuration...</p>
    </div>
</body>
</html>
EOF
    
    chmod +x app.py
    print_success "Fichiers de l'application téléchargés"
}

# Configuration des variables d'environnement
setup_environment_variables() {
    print_status "Configuration des variables d'environnement..."
    
    # Générer une clé secrète aléatoire
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    cat > .env << EOF
# Configuration Smart Shopping Assistant
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_SECRET_KEY=${SECRET_KEY}

# Configuration base de données
DB_PATH=/opt/smart-shopping/smart_shopping.db

# Configuration Email Gmail (À CONFIGURER)
GMAIL_EMAIL=rapherv@gmail.com
GMAIL_APP_PASSWORD=

# Configuration scraping
USER_AGENT=Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36

# Configuration notifications
NOTIFICATION_EMAIL=rapherv@gmail.com
ENABLE_PRICE_ALERTS=true
ENABLE_PROMOTION_ALERTS=true

# Configuration surveillance
PRICE_CHECK_INTERVAL_HOURS=2
PROMOTION_CHECK_TIME=08:00
CLEANUP_DAY=sunday
CLEANUP_TIME=02:00

# Configuration seuils
MAX_DISCOUNT_THRESHOLD=90.0
MIN_PRICE_ALERT=5.0

# Configuration log
LOG_LEVEL=INFO
LOG_MAX_SIZE=10MB
EOF
    
    print_success "Variables d'environnement configurées"
}

# Configuration Nginx
setup_nginx() {
    print_status "Configuration de Nginx..."
    
    sudo tee /etc/nginx/sites-available/smart-shopping << 'EOF'
server {
    listen 80;
    server_name _;
    
    # Logs
    access_log /var/log/nginx/smart-shopping.access.log;
    error_log /var/log/nginx/smart-shopping.error.log;
    
    # Taille maximale des uploads
    client_max_body_size 10M;
    
    # Proxy vers l'application Flask
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Fichiers statiques
    location /static {
        alias /opt/smart-shopping/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
        
        # Compression
        gzip on;
        gzip_vary on;
        gzip_types text/css application/javascript application/json;
    }
    
    # API avec cache court
    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Pas de cache pour les API
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
}
EOF
    
    # Activation du site
    sudo ln -sf /etc/nginx/sites-available/smart-shopping /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test de la configuration
    sudo nginx -t
    sudo systemctl reload nginx
    
    print_success "Nginx configuré"
}

# Configuration du service systemd
setup_systemd_service() {
    print_status "Configuration du service systemd..."
    
    sudo tee /etc/systemd/system/smart-shopping.service << EOF
[Unit]
Description=Smart Shopping Flask Application
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=/opt/smart-shopping
Environment=PATH=/opt/smart-shopping/venv/bin
EnvironmentFile=/opt/smart-shopping/.env
ExecStart=/opt/smart-shopping/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 120 --keep-alive 5 --max-requests 1000 app:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=3
KillMode=mixed
TimeoutStopSec=5

# Sécurité
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=/opt/smart-shopping

# Logs
StandardOutput=journal
StandardError=journal
SyslogIdentifier=smart-shopping

[Install]
WantedBy=multi-user.target
EOF
    
    print_success "Service systemd configuré"
}

# Configuration de la rotation des logs
setup_log_rotation() {
    print_status "Configuration de la rotation des logs..."
    
    sudo tee /etc/logrotate.d/smart-shopping << 'EOF'
/opt/smart-shopping/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        systemctl reload smart-shopping
    endscript
}
EOF
    
    print_success "Rotation des logs configurée"
}

# Configuration des tâches cron pour les sauvegardes
setup_backup_cron() {
    print_status "Configuration des sauvegardes automatiques..."
    
    # Script de sauvegarde
    cat > /opt/smart-shopping/backup.sh << 'EOF'
#!/bin/bash
# Script de sauvegarde Smart Shopping

BACKUP_DIR="/opt/smart-shopping/backups"
DB_PATH="/opt/smart-shopping/smart_shopping.db"
DATE=$(date +%Y%m%d_%H%M%S)

# Créer le répertoire de sauvegarde si nécessaire
mkdir -p "$BACKUP_DIR"

# Sauvegarde de la base de données
if [ -f "$DB_PATH" ]; then
    sqlite3 "$DB_PATH" ".backup $BACKUP_DIR/smart_shopping_$DATE.db"
    echo "Sauvegarde DB créée: smart_shopping_$DATE.db"
fi

# Sauvegarde de la configuration
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" -C /opt/smart-shopping .env requirements.txt

# Nettoyage des anciennes sauvegardes (garder 30 jours)
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "Sauvegarde terminée: $DATE"
EOF
    
    chmod +x /opt/smart-shopping/backup.sh
    
    # Ajouter la tâche cron (sauvegarde quotidienne à 3h)
    (crontab -l 2>/dev/null; echo "0 3 * * * /opt/smart-shopping/backup.sh >> /opt/smart-shopping/logs/backup.log 2>&1") | crontab -
    
    print_success "Sauvegardes automatiques configurées"
}

# Configuration du firewall
setup_firewall() {
    print_status "Configuration du firewall..."
    
    # Configuration UFW
    sudo ufw --force reset
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # Autoriser SSH, HTTP et HTTPS
    sudo ufw allow 22/tcp comment 'SSH'
    sudo ufw allow 80/tcp comment 'HTTP'
    sudo ufw allow 443/tcp comment 'HTTPS'
    
    # Activer le firewall
    sudo ufw --force enable
    
    print_success "Firewall configuré"
}

# Démarrage des services
start_services() {
    print_status "Démarrage des services..."
    
    # Recharger la configuration systemd
    sudo systemctl daemon-reload
    
    # Activer et démarrer les services
    sudo systemctl enable smart-shopping
    sudo systemctl start smart-shopping
    
    sudo systemctl enable nginx
    sudo systemctl restart nginx
    
    # Attendre que les services se lancent
    sleep 5
    
    print_success "Services démarrés"
}

# Vérification de l'installation
verify_installation() {
    print_status "Vérification de l'installation..."
    
    # Vérifier les services
    if systemctl is-active --quiet smart-shopping; then
        print_success "Service Smart Shopping: Actif"
    else
        print_error "Service Smart Shopping: Problème détecté"
        sudo systemctl status smart-shopping --no-pager -l
    fi
    
    if systemctl is-active --quiet nginx; then
        print_success "Service Nginx: Actif"
    else
        print_error "Service Nginx: Problème détecté"
        sudo systemctl status nginx --no-pager -l
    fi
    
    # Test de connectivité
    LOCAL_IP=$(hostname -I | cut -d' ' -f1)
    
    if curl -s http://localhost >/dev/null; then
        print_success "Application accessible localement"
    else
        print_warning "Problème d'accès local détecté"
    fi
    
    print_success "Vérification terminée"
}

# Affichage des informations finales
show_final_info() {
    LOCAL_IP=$(hostname -I | cut -d' ' -f1)
    
    echo ""
    echo "=================================================="
    echo "✅ Installation Smart Shopping Assistant terminée!"
    echo "=================================================="
    echo ""
    echo "🌐 Accès à l'application:"
    echo "   • Local:        http://localhost"
    echo "   • Réseau local: http://$LOCAL_IP"
    echo ""
    echo "📁 Fichiers installés dans: /opt/smart-shopping"
    echo ""
    echo "⚙️  Prochaines étapes:"
    echo "   1. 📧 Configurer l'email Gmail:"
    echo "      - Aller sur: https://myaccount.google.com/apppasswords"
    echo "      - Générer un mot de passe d'application"
    echo "      - Modifier /opt/smart-shopping/.env"
    echo "      - Redémarrer: sudo systemctl restart smart-shopping"
    echo ""
    echo "   2. 🔧 Commandes utiles:"
    echo "      - Logs app:    sudo journalctl -u smart-shopping -f"
    echo "      - Logs nginx:  sudo tail -f /var/log/nginx/smart-shopping.*.log"
    echo "      - Redémarrer:  sudo systemctl restart smart-shopping"
    echo "      - Statut:      sudo systemctl status smart-shopping"
    echo ""
    echo "   3. 💾 Sauvegardes:"
    echo "      - Automatiques: Quotidiennes à 3h"
    echo "      - Manuel:       /opt/smart-shopping/backup.sh"
    echo "      - Dossier:      /opt/smart-shopping/backups"
    echo ""
    echo "🎉 Votre assistant intelligent est prêt!"
    echo "   Il surveillera automatiquement les prix et promotions."
    echo ""
}

# Fonction principale
main() {
    echo "Smart Shopping Assistant - Installation automatique"
    echo "=================================================="
    
    check_prerequisites
    update_system
    install_dependencies
    setup_application_environment
    download_application_files
    setup_environment_variables
    setup_nginx
    setup_systemd_service
    setup_log_rotation
    setup_backup_cron
    setup_firewall
    start_services
    verify_installation
    show_final_info
}

# Gestion des erreurs
trap 'print_error "Installation interrompue"; exit 1' ERR

# Exécution du script principal
main "$@"
