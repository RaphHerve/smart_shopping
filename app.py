#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Shopping Backend - Flask Application
Serveur pour Raspberry Pi Ubuntu Server
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import json
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import schedule
import time
import threading
from datetime import datetime, timedelta
import os
import logging
from urllib.parse import urljoin
import re

# Configuration
app = Flask(__name__)
CORS(app)

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration email
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'email': 'rapherv@gmail.com',
    'password': '',  # À configurer avec mot de passe d'application Gmail
    'recipient': 'rapherv@gmail.com'
}

# Configuration base de données
DB_PATH = 'smart_shopping.db'

def init_database():
    """Initialise la base de données SQLite"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table des articles de la liste de courses
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shopping_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Divers',
            checked BOOLEAN DEFAULT 0,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            priority INTEGER DEFAULT 1
        )
    ''')
    
    # Table des articles fréquents (habitudes)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS frequent_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT,
            frequency INTEGER DEFAULT 1,
            last_bought TIMESTAMP,
            avg_price REAL DEFAULT 0
        )
    ''')
    
    # Table des recettes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ingredients TEXT,  -- JSON
            source TEXT DEFAULT 'jow',
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table de surveillance des prix (erreurs détectées)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            url TEXT NOT NULL,
            original_price REAL,
            current_price REAL,
            discount_percent REAL,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notified BOOLEAN DEFAULT 0,
            site TEXT DEFAULT 'amazon'
        )
    ''')
    
    # Table des promos locales
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS local_deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store TEXT NOT NULL,  -- carrefour, leclerc, lidl
            product_name TEXT NOT NULL,
            original_price REAL,
            promo_price REAL,
            discount_percent REAL,
            valid_until DATE,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insérer les articles fréquents par défaut
    frequent_items = [
        ('Pâtes', 'Épicerie', 5), ('Riz', 'Épicerie', 4),
        ('Thon en boîte', 'Conserves', 4), ('Champignons surgelés', 'Surgelés', 5),
        ('Oignons surgelés', 'Surgelés', 5), ('Mozzarella', 'Fromage', 4),
        ('Crème fraîche', 'Frais', 4), ('Pesto vert', 'Épicerie', 3),
        ('Pesto rosso', 'Épicerie', 3), ('Fromage râpé', 'Fromage', 4),
        ('Poisson pané', 'Surgelés', 3), ('Wraps', 'Épicerie', 3),
        ('Tomates', 'Légumes', 4), ('Salade', 'Légumes', 3),
        ('Jambon', 'Charcuterie', 3), ('Ravioli Rana', 'Frais', 2),
        ('Semoule', 'Épicerie', 2), ('Huile truffe', 'Épicerie', 2),
        ('Curry', 'Épices', 2), ('Poulet', 'Viande', 3),
        ('Viande hachée', 'Viande', 2)
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO frequent_items (name, category, frequency) 
        VALUES (?, ?, ?)
    ''', frequent_items)
    
    # Insérer les recettes par défaut
    recipes_data = [
        ('Fried Egg with Sweet Potato Hash', '["Sweet potato", "Feta", "Eggs", "Chile pepper"]'),
        ('Tomato and Mozzarella Bruschetta', '["Bread", "Tomato", "Mozzarella"]'),
        ('Shrimp Curry with Rice', '["Riz", "Crevettes", "Épinards", "Curry", "Sauce tomate", "Lait de coco", "Bouillon de légumes"]'),
        ('Macaroni Risotto', '["Pasta", "Ham", "Shallot", "Comté", "Crème fraîche", "White wine"]'),
        ('Wraps Thon Tomate', '["Wraps", "Thon en boîte", "Tomates", "Salade"]'),
        ('Pâtes Pesto', '["Pâtes", "Pesto vert", "Fromage râpé"]'),
        ('Pâtes Carbonara', '["Pâtes", "Jambon", "Crème fraîche", "Fromage râpé"]'),
        ('Tacos Viande', '["Tortillas", "Viande hachée", "Champignons surgelés", "Oignons surgelés"]')
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO recipes (name, ingredients) 
        VALUES (?, ?)
    ''', recipes_data)
    
    conn.commit()
    conn.close()
    logger.info("Base de données initialisée")

# Routes API
@app.route('/')
def index():
    """Page d'accueil - sert l'application React"""
    return render_template('index.html')

@app.route('/api/shopping-list', methods=['GET'])
def get_shopping_list():
    """Récupère la liste de courses"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, category, checked, added_at, priority 
        FROM shopping_items 
        ORDER BY checked ASC, priority DESC, added_at DESC
    ''')
    items = []
    for row in cursor.fetchall():
        items.append({
            'id': row[0],
            'name': row[1],
            'category': row[2],
            'checked': bool(row[3]),
            'addedAt': row[4],
            'priority': row[5]
        })
    conn.close()
    return jsonify(items)

@app.route('/api/shopping-list', methods=['POST'])
def add_shopping_item():
    """Ajoute un article à la liste de courses"""
    data = request.get_json()
    name = data.get('name', '').strip()
    category = data.get('category', 'Divers')
    
    if not name:
        return jsonify({'error': 'Nom requis'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO shopping_items (name, category) 
        VALUES (?, ?)
    ''', (name, category))
    item_id = cursor.lastrowid
    
    # Mettre à jour la fréquence si l'article est connu
    cursor.execute('''
        UPDATE frequent_items 
        SET frequency = frequency + 1, last_bought = CURRENT_TIMESTAMP
        WHERE name = ?
    ''', (name,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'id': item_id, 'name': name, 'category': category})

@app.route('/api/shopping-list/<int:item_id>', methods=['PUT'])
def update_shopping_item(item_id):
    """Met à jour un article (coché/décoché)"""
    data = request.get_json()
    checked = data.get('checked', False)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE shopping_items 
        SET checked = ? 
        WHERE id = ?
    ''', (checked, item_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/shopping-list/<int:item_id>', methods=['DELETE'])
def delete_shopping_item(item_id):
    """Supprime un article de la liste"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM shopping_items WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/frequent-items', methods=['GET'])
def get_frequent_items():
    """Récupère les articles fréquents pour suggestions"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, category, frequency 
        FROM frequent_items 
        ORDER BY frequency DESC, name ASC
    ''')
    items = []
    for row in cursor.fetchall():
        items.append({
            'name': row[0],
            'category': row[1],
            'frequency': row[2]
        })
    conn.close()
    return jsonify(items)

@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    """Récupère les recettes"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, ingredients FROM recipes ORDER BY name')
    recipes = []
    for row in cursor.fetchall():
        recipes.append({
            'id': row[0],
            'name': row[1],
            'ingredients': json.loads(row[2])
        })
    conn.close()
    return jsonify(recipes)

@app.route('/api/recipes/<int:recipe_id>/add-to-list', methods=['POST'])
def add_recipe_to_list(recipe_id):
    """Ajoute tous les ingrédients d'une recette à la liste"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Récupérer la recette
    cursor.execute('SELECT name, ingredients FROM recipes WHERE id = ?', (recipe_id,))
    recipe = cursor.fetchone()
    
    if not recipe:
        return jsonify({'error': 'Recette non trouvée'}), 404
    
    ingredients = json.loads(recipe[1])
    added_count = 0
    
    for ingredient in ingredients:
        # Vérifier si l'ingrédient n'est pas déjà dans la liste
        cursor.execute('''
            SELECT COUNT(*) FROM shopping_items 
            WHERE LOWER(name) = LOWER(?) AND checked = 0
        ''', (ingredient,))
        
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO shopping_items (name, category) 
                VALUES (?, ?)
            ''', (ingredient, 'Recette'))
            added_count += 1
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True, 
        'added_count': added_count,
        'recipe_name': recipe[0]
    })

@app.route('/api/price-alerts', methods=['GET'])
def get_price_alerts():
    """Récupère les alertes de prix détectées"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT product_name, url, original_price, current_price, 
               discount_percent, detected_at, site
        FROM price_alerts 
        WHERE detected_at > datetime('now', '-7 days')
        ORDER BY detected_at DESC
    ''')
    alerts = []
    for row in cursor.fetchall():
        alerts.append({
            'product_name': row[0],
            'url': row[1],
            'original_price': row[2],
            'current_price': row[3],
            'discount_percent': row[4],
            'detected_at': row[5],
            'site': row[6]
        })
    conn.close()
    return jsonify(alerts)

def send_email_notification(subject, body, html_body=None):
    """Envoie une notification par email"""
    try:
        if not EMAIL_CONFIG['password']:
            logger.warning("Mot de passe email non configuré")
            return False
            
        msg = MimeMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_CONFIG['email']
        msg['To'] = EMAIL_CONFIG['recipient']
        
        # Texte brut
        text_part = MimeText(body, 'plain', 'utf-8')
        msg.attach(text_part)
        
        # HTML si fourni
        if html_body:
            html_part = MimeText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
        
        # Envoi
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email envoyé: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur envoi email: {e}")
        return False

def check_amazon_prices():
    """Vérifie les prix Amazon pour détecter les erreurs"""
    # Cette fonction sera développée pour scraper Amazon
    # Pour l'instant, c'est un placeholder
    logger.info("Vérification des prix Amazon...")
    
    # TODO: Implémenter le scraping Amazon
    # - Rechercher des produits populaires
    # - Détecter les prix anormalement bas
    # - Enregistrer en base et envoyer des alertes
    
    pass

def scrape_local_deals():
    """Scrape les promos des magasins locaux"""
    # TODO: Implémenter le scraping des promos
    # - Carrefour Market
    # - Leclerc Drive  
    # - Lidl
    logger.info("Vérification des promos locales...")
    pass

# Planificateur de tâches
def run_scheduler():
    """Lance le planificateur en arrière-plan"""
    schedule.every(1).hours.do(check_amazon_prices)
    schedule.every(6).hours.do(scrape_local_deals)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# Configuration pour servir les fichiers statiques
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    # Initialisation
    init_database()
    
    # Démarrer le planificateur en arrière-plan
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Démarrer le serveur Flask
    logger.info("Démarrage du serveur Smart Shopping...")
    app.run(host='0.0.0.0', port=5000, debug=False)
