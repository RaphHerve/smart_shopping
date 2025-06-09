#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Shopping Assistant - Utilitaires et scripts d'aide
Outils de maintenance, migration et configuration
"""

import os
import sys
import sqlite3
import json
import shutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Configuration par défaut
DEFAULT_DB_PATH = '/opt/smart-shopping/smart_shopping.db'
DEFAULT_BACKUP_DIR = '/opt/smart-shopping/backups'

class DatabaseUtilities:
    """Utilitaires pour la gestion de la base de données"""
    
    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = db_path
    
    def backup_database(self, backup_path=None):
        """Crée une sauvegarde de la base de données"""
        if not backup_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{DEFAULT_BACKUP_DIR}/smart_shopping_{timestamp}.db"
        
        # Créer le répertoire de sauvegarde si nécessaire
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # Copier la base de données
        if os.path.exists(self.db_path):
            shutil.copy2(self.db_path, backup_path)
            print(f"✅ Sauvegarde créée: {backup_path}")
            return backup_path
        else:
            print(f"❌ Base de données non trouvée: {self.db_path}")
            return None
    
    def restore_database(self, backup_path):
        """Restaure une sauvegarde de la base de données"""
        if not os.path.exists(backup_path):
            print(f"❌ Fichier de sauvegarde non trouvé: {backup_path}")
            return False
        
        # Créer une sauvegarde de la base actuelle
        if os.path.exists(self.db_path):
            current_backup = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(self.db_path, current_backup)
            print(f"📦 Sauvegarde actuelle créée: {current_backup}")
        
        # Restaurer la sauvegarde
        shutil.copy2(backup_path, self.db_path)
        print(f"✅ Base de données restaurée depuis: {backup_path}")
        return True
    
    def export_data(self, output_file):
        """Exporte toutes les données en JSON"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            data = {}
            
            # Liste des tables à exporter
            tables = ['shopping_list', 'frequent_items', 'recipes', 'price_alerts', 'local_promotions']
            
            for table in tables:
                cursor.execute(f"SELECT * FROM {table}")
                data[table] = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            # Écrire le JSON
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"✅ Données exportées vers: {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de l'export: {e}")
            return False
    
    def import_data(self, input_file):
        """Importe des données depuis un fichier JSON"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for table_name, records in data.items():
                if records:
                    # Obtenir les colonnes de la table
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns_info = cursor.fetchall()
                    columns = [col[1] for col in columns_info if col[1] != 'id']  # Exclure l'ID
                    
                    # Préparer la requête d'insertion
                    placeholders = ', '.join(['?' for _ in columns])
                    query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                    
                    # Insérer les données
                    for record in records:
                        values = [record.get(col) for col in columns]
                        cursor.execute(query, values)
            
            conn.commit()
            conn.close()
            
            print(f"✅ Données importées depuis: {input_file}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de l'import: {e}")
            return False
    
    def analyze_database(self):
        """Analyse la base de données et affiche des statistiques"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            print("📊 Analyse de la base de données Smart Shopping")
            print("=" * 50)
            
            # Informations générales
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size = cursor.fetchone()[0]
            print(f"📦 Taille de la base: {db_size / 1024:.1f} KB")
            
            # Statistiques par table
            tables = ['shopping_list', 'frequent_items', 'recipes', 'price_alerts', 'local_promotions']
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"📋 {table}: {count} enregistrements")
            
            # Analyse des articles fréquents
            cursor.execute("""
                SELECT name, usage_count 
                FROM frequent_items 
                ORDER BY usage_count DESC 
                LIMIT 5
            """)
            frequent = cursor.fetchall()
            
            if frequent:
                print("\n🔥 Top 5 articles les plus achetés:")
                for item, count in frequent:
                    print(f"   • {item}: {count} fois")
            
            # Analyse des alertes de prix
            cursor.execute("""
                SELECT COUNT(*) as count, AVG(discount_percentage) as avg_discount
                FROM price_alerts 
                WHERE is_error = 1
            """)
            alerts_data = cursor.fetchone()
            
            if alerts_data[0] > 0:
                print(f"\n🚨 Alertes de prix: {alerts_data[0]} détectées")
                print(f"💰 Réduction moyenne: {alerts_data[1]:.1f}%")
            
            # Promotions actives
            cursor.execute("""
                SELECT COUNT(*) 
                FROM local_promotions 
                WHERE valid_until >= date('now')
            """)
            active_promos = cursor.fetchone()[0]
            print(f"🏪 Promotions actives: {active_promos}")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Erreur lors de l'analyse: {e}")

class MaintenanceUtilities:
    """Utilitaires de maintenance système"""
    
    @staticmethod
    def cleanup_old_files():
        """Nettoie les anciens fichiers de logs et sauvegardes"""
        cleaned_files = 0
        
        # Nettoyer les anciens logs (> 30 jours)
        log_dir = Path('/opt/smart-shopping/logs')
        if log_dir.exists():
            cutoff_date = datetime.now() - timedelta(days=30)
            for log_file in log_dir.glob('*.log*'):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    cleaned_files += 1
                    print(f"🗑️  Supprimé: {log_file}")
        
        # Nettoyer les anciennes sauvegardes (> 30 jours)
        backup_dir = Path(DEFAULT_BACKUP_DIR)
        if backup_dir.exists():
            cutoff_date = datetime.now() - timedelta(days=30)
            for backup_file in backup_dir.glob('*.db'):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    cleaned_files += 1
                    print(f"🗑️  Supprimé: {backup_file}")
        
        print(f"✅ Nettoyage terminé: {cleaned_files} fichiers supprimés")
    
    @staticmethod
    def check_system_health():
        """Vérifie la santé du système"""
        print("🏥 Vérification de la santé du système")
        print("=" * 40)
        
        # Vérifier l'espace disque
        import shutil
        total, used, free = shutil.disk_usage('/opt/smart-shopping')
        usage_percent = (used / total) * 100
        
        print(f"💾 Espace disque:")
        print(f"   Total: {total // (1024**3)} GB")
        print(f"   Utilisé: {used // (1024**3)} GB ({usage_percent:.1f}%)")
        print(f"   Libre: {free // (1024**3)} GB")
        
        if usage_percent > 90:
            print("⚠️  Attention: Espace disque faible!")
        
        # Vérifier les services
        import subprocess
        
        services = ['smart-shopping', 'nginx']
        for service in services:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', service],
                    capture_output=True, text=True
                )
                status = "🟢 Actif" if result.stdout.strip() == 'active' else "🔴 Inactif"
                print(f"🔧 Service {service}: {status}")
            except Exception:
                print(f"🔧 Service {service}: ❓ Statut inconnu")
        
        # Vérifier la base de données
        if os.path.exists(DEFAULT_DB_PATH):
            try:
                conn = sqlite3.connect(DEFAULT_DB_PATH)
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()[0]
                conn.close()
                
                if result == 'ok':
                    print("🗄️  Base de données: 🟢 Intègre")
                else:
                    print("🗄️  Base de données: 🔴 Problème détecté")
            except Exception as e:
                print(f"🗄️  Base de données: ❌ Erreur - {e}")
        else:
            print("🗄️  Base de données: ❌ Non trouvée")

class ConfigurationUtilities:
    """Utilitaires de configuration"""
    
    @staticmethod
    def generate_sample_data():
        """Génère des données d'exemple pour les tests"""
        try:
            conn = sqlite3.connect(DEFAULT_DB_PATH)
            cursor = conn.cursor()
            
            # Articles d'exemple
            sample_items = [
                ('Lait demi-écrémé', 'Produits laitiers', 1, False),
                ('Pain complet', 'Boulangerie', 1, False),
                ('Pommes Golden', 'Fruits et légumes', 2, False),
                ('Yaourts nature', 'Produits laitiers', 1, True),
                ('Pâtes spaghetti', 'Épicerie', 1, False),
            ]
            
            for name, category, quantity, checked in sample_items:
                cursor.execute("""
                    INSERT OR IGNORE INTO shopping_list (name, category, quantity, checked)
                    VALUES (?, ?, ?, ?)
                """, (name, category, quantity, checked))
            
            # Recettes d'exemple
            sample_recipes = [
                ('Pâtes carbonara', 'Personnalisée', None, 
                 '["pâtes spaghetti", "lardons", "œufs", "parmesan", "crème fraîche"]', 4),
                ('Salade de fruits', 'Personnalisée', None,
                 '["pommes", "bananes", "oranges", "kiwis", "miel"]', 6),
            ]
            
            for name, source, url, ingredients, servings in sample_recipes:
                cursor.execute("""
                    INSERT OR IGNORE INTO recipes (name, source, url, ingredients, servings)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, source, url, ingredients, servings))
            
            # Articles fréquents d'exemple
            frequent_items = [
                ('Lait', 'Produits laitiers', 15),
                ('Pain', 'Boulangerie', 12),
                ('Pommes', 'Fruits et légumes', 8),
                ('Œufs', 'Produits laitiers', 6),
            ]
            
            for name, category, usage_count in frequent_items:
                cursor.execute("""
                    INSERT OR IGNORE INTO frequent_items (name, category, usage_count)
                    VALUES (?, ?, ?)
                """, (name, category, usage_count))
            
            conn.commit()
            conn.close()
            
            print("✅ Données d'exemple générées avec succès")
            
        except Exception as e:
            print(f"❌ Erreur lors de la génération des données: {e}")
    
    @staticmethod
    def validate_configuration():
        """Valide la configuration de l'application"""
        print("🔍 Validation de la configuration")
        print("=" * 35)
        
        # Vérifier le fichier .env
        env_path = '/opt/smart-shopping/.env'
        if os.path.exists(env_path):
            print("✅ Fichier .env trouvé")
            
            with open(env_path, 'r') as f:
                env_content = f.read()
                
            # Vérifier les variables critiques
            required_vars = ['GMAIL_EMAIL', 'GMAIL_APP_PASSWORD', 'FLASK_SECRET_KEY']
            for var in required_vars:
                if f"{var}=" in env_content and not f"{var}=\n" in env_content:
                    print(f"✅ {var} configuré")
                else:
                    print(f"⚠️  {var} manquant ou vide")
        else:
            print("❌ Fichier .env non trouvé")
        
        # Vérifier les répertoires
        required_dirs = [
            '/opt/smart-shopping/logs',
            '/opt/smart-shopping/backups',
            '/opt/smart-shopping/templates'
        ]
        
        for directory in required_dirs:
            if os.path.exists(directory):
                print(f"✅ Répertoire {directory} existe")
            else:
                print(f"❌ Répertoire {directory} manquant")

def main():
    """Fonction principale avec interface en ligne de commande"""
    parser = argparse.ArgumentParser(description='Utilitaires Smart Shopping Assistant')
    
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')
    
    # Commandes de base de données
    db_parser = subparsers.add_parser('db', help='Opérations sur la base de données')
    db_subparsers = db_parser.add_subparsers(dest='db_command')
    
    # Sauvegarde
    backup_parser = db_subparsers.add_parser('backup', help='Créer une sauvegarde')
    backup_parser.add_argument('--path', help='Chemin de la sauvegarde')
    
    # Restauration
    restore_parser = db_subparsers.add_parser('restore', help='Restaurer une sauvegarde')
    restore_parser.add_argument('backup_path', help='Chemin de la sauvegarde à restaurer')
    
    # Export
    export_parser = db_subparsers.add_parser('export', help='Exporter les données en JSON')
    export_parser.add_argument('output_file', help='Fichier de sortie JSON')
    
    # Import
    import_parser = db_subparsers.add_parser('import', help='Importer des données JSON')
    import_parser.add_argument('input_file', help='Fichier JSON à importer')
    
    # Analyse
    db_subparsers.add_parser('analyze', help='Analyser la base de données')
    
    # Commandes de maintenance
    maintenance_parser = subparsers.add_parser('maintenance', help='Opérations de maintenance')
    maintenance_subparsers = maintenance_parser.add_subparsers(dest='maintenance_command')
    
    maintenance_subparsers.add_parser('cleanup', help='Nettoyer les anciens fichiers')
    maintenance_subparsers.add_parser('health', help='Vérifier la santé du système')
    
    # Commandes de configuration
    config_parser = subparsers.add_parser('config', help='Configuration')
    config_subparsers = config_parser.add_subparsers(dest='config_command')
    
    config_subparsers.add_parser('validate', help='Valider la configuration')
    config_subparsers.add_parser('sample-data', help='Générer des données d\'exemple')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialiser les utilitaires
    db_utils = DatabaseUtilities()
    
    # Traiter les commandes
    if args.command == 'db':
        if args.db_command == 'backup':
            db_utils.backup_database(args.path)
        elif args.db_command == 'restore':
            db_utils.restore_database(args.backup_path)
        elif args.db_command == 'export':
            db_utils.export_data(args.output_file)
        elif args.db_command == 'import':
            db_utils.import_data(args.input_file)
        elif args.db_command == 'analyze':
            db_utils.analyze_database()
        else:
            db_parser.print_help()
    
    elif args.command == 'maintenance':
        if args.maintenance_command == 'cleanup':
            MaintenanceUtilities.cleanup_old_files()
        elif args.maintenance_command == 'health':
            MaintenanceUtilities.check_system_health()
        else:
            maintenance_parser.print_help()
    
    elif args.command == 'config':
        if args.config_command == 'validate':
            ConfigurationUtilities.validate_configuration()
        elif args.config_command == 'sample-data':
            ConfigurationUtilities.generate_sample_data()
        else:
            config_parser.print_help()
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
