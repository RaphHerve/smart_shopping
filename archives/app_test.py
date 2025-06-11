#!/usr/bin/env python3
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# Template HTML simple intégré
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Shopping Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .status { padding: 10px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px; margin: 20px 0; }
        .api-test { margin: 20px 0; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
        #result { margin-top: 20px; padding: 10px; background: #f8f9fa; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛒 Smart Shopping Assistant</h1>
        
        <div class="status">
            ✅ <strong>Statut:</strong> Application en ligne sur Raspberry Pi
        </div>
        
        <div class="api-test">
            <h3>Test de l'API</h3>
            <button onclick="testAPI()">Tester l'API</button>
            <div id="result"></div>
        </div>
        
        <div>
            <h3>Informations</h3>
            <p><strong>Serveur:</strong> Raspberry Pi Ubuntu</p>
            <p><strong>IP:</strong> 192.168.1.177</p>
            <p><strong>Port:</strong> 5000</p>
            <p><strong>Framework:</strong> Flask</p>
        </div>
        
        <div>
            <h3>Prochaines étapes</h3>
            <p>📝 Interface complète Smart Shopping en cours de développement</p>
            <p>🔧 Cette version test valide que le serveur fonctionne</p>
        </div>
    </div>
    
    <script>
        async function testAPI() {
            try {
                const response = await fetch('/api/test');
                const data = await response.json();
                document.getElementById('result').innerHTML = 
                    '<strong>✅ API fonctionne!</strong><br>' + 
                    'Statut: ' + data.status + '<br>' +
                    'Message: ' + data.message + '<br>' +
                    'Serveur: ' + data.server;
            } catch (error) {
                document.getElementById('result').innerHTML = 
                    '<strong>❌ Erreur API:</strong> ' + error.message;
            }
        }
    </script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/test')
def api_test():
    return jsonify({
        'status': 'OK',
        'message': 'Smart Shopping API fonctionnelle',
        'server': 'Raspberry Pi',
        'framework': 'Flask'
    })

@app.route('/api/stats')
def stats():
    return jsonify({
        'shopping_list_items': 0,
        'completed_items': 0,
        'recipes': 0,
        'price_alerts': 0,
        'active_promotions': 0,
        'status': 'running'
    })

if __name__ == '__main__':
    print("🚀 Démarrage Smart Shopping Assistant...")
    print("🌐 Accessible sur http://192.168.1.177:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
