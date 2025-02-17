from flask import Flask, request, jsonify, render_template
import sqlite3
import requests
import base64

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
        image TEXT,
        location TEXT,
        scientific_name TEXT
    )
''')
conn.commit()

# Ruta principal
@app.route('/')
def index():
    # Obtener todos los registros de la base de datos
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

        # Decodificar imagen
        image_bytes = base64.b64decode(image_data)

        # Enviar a Pl@ntNet
        PLANTNET_API_KEY = "2b103McS4Rs5cVcuZS9e2ObBKe"
        PLANTNET_API_URL = f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_API_KEY}"
        response = requests.post(
            PLANTNET_API_URL,
            files={"images": ("image.png", image_bytes, "image/png")},
            data={"organs": organ}
        )

        if response.status_code != 200:
            return jsonify({"error": "Error en la API de Pl@ntNet"}), 500

        result = response.json()
        suggestions = result.get("results", [])
        if not suggestions:
            return jsonify({"error": "No se encontraron sugerencias"}), 404

        scientific_name = suggestions[0]["species"]["scientificNameWithoutAuthor"]

        # Guardar en la base de datos
        cursor.execute('''
            INSERT INTO plant_data (username, organ, image, location, scientific_name)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, organ, image_data, location, scientific_name))
        conn.commit()

        return jsonify({
            "scientific_name": scientific_name
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)