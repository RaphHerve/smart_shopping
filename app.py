#!/usr/bin/env python3
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = 'smart-shopping-secret-key'
DB_PATH = 'smart_shopping.db'

def init_db():
    """Initialise la base de données"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table des articles de courses
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shopping_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Divers',
            checked BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')

@app.route('/api/shopping-list', methods=['GET'])
def get_shopping_list():
    """Récupère la liste de courses"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM shopping_list ORDER BY checked ASC, created_at DESC')
    items = cursor.fetchall()
    conn.close()
    
    shopping_list = []
    for item in items:
        shopping_list.append({
            'id': item[0],
            'name': item[1],
            'category': item[2],
            'checked': bool(item[3]),
            'created_at': item[4]
        })
    
    return jsonify(shopping_list)

@app.route('/api/shopping-list', methods=['POST'])
def add_shopping_item():
    """Ajoute un article à la liste"""
    data = request.get_json()
    name = data.get('name')
    category = data.get('category', 'Divers')
    
    if not name:
        return jsonify({'error': 'Nom requis'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO shopping_list (name, category) VALUES (?, ?)', (name, category))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True}), 201

@app.route('/api/shopping-list/<int:item_id>', methods=['PUT'])
def update_shopping_item(item_id):
    """Met à jour un article"""
    data = request.get_json()
    checked = data.get('checked')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE shopping_list SET checked = ? WHERE id = ?', (checked, item_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/shopping-list/<int:item_id>/edit', methods=['PUT'])
def edit_shopping_item(item_id):
    """Modifie le nom et/ou la catégorie d'un article"""
    data = request.get_json()
    name = data.get('name')
    category = data.get('category')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Construire la requête dynamiquement selon les champs fournis
    updates = []
    params = []
    
    if name:
        updates.append('name = ?')
        params.append(name)
    
    if category:
        updates.append('category = ?')
        params.append(category)
    
    if updates:
        query = f'UPDATE shopping_list SET {", ".join(updates)} WHERE id = ?'
        params.append(item_id)
        cursor.execute(query, params)
        conn.commit()
    
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/shopping-list/<int:item_id>', methods=['DELETE'])
def delete_shopping_item(item_id):
    """Supprime un article"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM shopping_list WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Récupère la liste des catégories disponibles"""
    categories = [
        'Fruits & Légumes',
        'Produits frais',
        'Boulangerie',
        'Épicerie',
        'Fromage',
        'Viande & Poisson',
        'Surgelés',
        'Boissons',
        'Hygiène & Beauté',
        'Entretien',
        'Divers'
    ]
    return jsonify(categories)

@app.route('/api/frequent-items', methods=['GET'])
def get_frequent_items():
    """Récupère les articles fréquents"""
    frequent_items = [
        {'name': 'Pain', 'category': 'Boulangerie'},
        {'name': 'Lait', 'category': 'Produits frais'},
        {'name': 'Œufs', 'category': 'Produits frais'},
        {'name': 'Pommes', 'category': 'Fruits & Légumes'},
        {'name': 'Bananes', 'category': 'Fruits & Légumes'},
        {'name': 'Tomates', 'category': 'Fruits & Légumes'},
        {'name': 'Pâtes', 'category': 'Épicerie'},
        {'name': 'Riz', 'category': 'Épicerie'},
        {'name': 'Mozzarella', 'category': 'Fromage'},
        {'name': 'Emmental', 'category': 'Fromage'},
        {'name': 'Camembert', 'category': 'Fromage'},
        {'name': 'Gruyère', 'category': 'Fromage'}
    ]
    
    return jsonify(frequent_items)

@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    """Récupère les recettes"""
    example_recipes = [
        {
            'id': 1,
            'name': 'Salade de tomates',
            'ingredients': ['Tomates', 'Mozzarella', 'Basilic', 'Huile d\'olive'],
            'instructions': 'Couper les tomates et la mozzarella, ajouter le basilic et l\'huile d\'olive.'
        },
        {
            'id': 2,
            'name': 'Pâtes à l\'ail',
            'ingredients': ['Pâtes', 'Ail', 'Huile d\'olive', 'Parmesan'],
            'instructions': 'Cuire les pâtes, faire revenir l\'ail, mélanger avec le parmesan.'
        }
    ]
    return jsonify(example_recipes)

@app.route('/api/price-alerts', methods=['GET'])
def get_price_alerts():
    """Récupère les alertes de prix"""
    alerts = []
    return jsonify(alerts)

@app.route('/health')
def health_check():
    """Point de contrôle santé"""
    return jsonify({
        'status': 'healthy',
        'service': 'Smart Shopping',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Initialiser la base de données
    init_db()
    
    print("🚀 Smart Shopping démarrage...")
    print("📍 Accessible sur http://127.0.0.1:5000")
    
    # Démarrer l'application
    app.run(host='127.0.0.1', port=5000, debug=False)
