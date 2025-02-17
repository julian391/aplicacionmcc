from flask import Flask, request, jsonify, render_template
import sqlite3
import requests
import base64
import os
import io

app = Flask(__name__)

# Configuración de la base de datos SQLite
conn = sqlite3.connect('data.db', check_same_thread=False)
cursor = conn.cursor()

# Crear tabla si no existe
cursor.execute('''
    CREATE TABLE IF NOT EXISTS plant_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        organ TEXT,
        image_path TEXT,
        location TEXT,
        scientific_name TEXT
    )
''')
conn.commit()

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Ruta principal
@app.route('/')
def index():
    cursor.execute('SELECT * FROM plant_data ORDER BY id DESC')
    records = cursor.fetchall()
    return render_template('index.html', records=records)

# Ruta para recibir datos
@app.route('/upload', methods=['POST'])
def upload():
    try:
        data = request.json
        username = data.get('username')
        organ = data.get('organ')
        image_data = data.get('image')
        location = data.get('location')

        # Decodificar imagen base64
        image_bytes = base64.b64decode(image_data.split(",")[-1])

        # Guardar imagen en el servidor
        image_filename = f"{username}_{organ}.png"
        image_path = os.path.join(UPLOAD_FOLDER, image_filename)
        with open(image_path, "wb") as f:
            f.write(image_bytes)

        # Enviar imagen a Google AI Studio
        GOOGLE_API_KEY = "AIzaSyCk8PXyVMeJROJWGQAMiIP2hwWL2s-PztI"
        GOOGLE_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"

        response = requests.post(
            GOOGLE_API_URL,
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": "Identify the plant in the image"}]}]}
        )

        if response.status_code != 200:
            return jsonify({"error": "Error en la API de Google AI"}), 500

        result = response.json()
        scientific_name = result.get("predictions", [{}])[0].get("label", "Desconocido")

        # Guardar en la base de datos
        cursor.execute('''
            INSERT INTO plant_data (username, organ, image_path, location, scientific_name)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, organ, image_path, location, scientific_name))
        conn.commit()

        return jsonify({
            "scientific_name": scientific_name,
            "image_url": image_path
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
