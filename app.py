from flask import Flask, request, jsonify, render_template
import sqlite3
import requests
import base64
import os

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

# Endpoint para recibir datos
@app.route('/upload', methods=['POST'])
def upload():
    try:
        print("Recibiendo solicitud desde el frontend...")  # Mensaje de depuración
        data = request.json
        username = data.get('username')
        organ = data.get('organ')
        image_data = data.get('image')
        location = data.get('location')

        if not username or not organ or not image_data:
            print("Faltan campos obligatorios.")  # Mensaje de depuración
            return jsonify({"error": "Faltan campos obligatorios"}), 400

        # Decodificar imagen
        try:
            print("Decodificando imagen...")  # Mensaje de depuración
            image_bytes = base64.b64decode(image_data)
        except Exception as e:
            print(f"Error al decodificar la imagen: {str(e)}")  # Mensaje de depuración
            return jsonify({"error": f"Error al decodificar la imagen: {str(e)}"}), 400

        # Enviar a Pl@ntNet
        PLANTNET_API_KEY = "2b103McS4Rs5cVcuZS9e2ObBKe"
        PLANTNET_API_URL = f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_API_KEY}"
        try:
            print("Enviando solicitud a la API de Pl@ntNet...")  # Mensaje de depuración
            response = requests.post(
                PLANTNET_API_URL,
                files={"images": ("image.png", image_bytes, "image/png")},
                data={"organs": organ},
                timeout=60  # Aumenta el tiempo de espera a 60 segundos
            )
            print(f"Respuesta de la API de Pl@ntNet: {response.status_code} - {response.text}")  # Mensaje de depuración
            if response.status_code != 200:
                return jsonify({
                    "error": f"Error en la API de Pl@ntNet: {response.status_code} - {response.text}"
                }), 500
        except requests.exceptions.Timeout:
            print("La API de Pl@ntNet tardó demasiado tiempo en responder.")  # Mensaje de depuración
            return jsonify({"error": "La API de Pl@ntNet tardó demasiado tiempo en responder."}), 500
        except Exception as e:
            print(f"Error al conectar con la API de Pl@ntNet: {str(e)}")  # Mensaje de depuración
            return jsonify({"error": f"Error al conectar con la API de Pl@ntNet: {str(e)}"}), 500

        result = response.json()
        suggestions = result.get("results", [])
        if not suggestions:
            print("No se encontraron sugerencias en la respuesta de Pl@ntNet.")  # Mensaje de depuración
            return jsonify({"error": "No se encontraron sugerencias"}), 404

        scientific_name = suggestions[0]["species"]["scientificNameWithoutAuthor"]

        # Guardar en la base de datos
        try:
            print("Guardando datos en la base de datos...")  # Mensaje de depuración
            cursor.execute('''
                INSERT INTO plant_data (username, organ, image, location, scientific_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, organ, image_data, location, scientific_name))
            conn.commit()
        except Exception as e:
            print(f"Error al guardar en la base de datos: {str(e)}")  # Mensaje de depuración
            return jsonify({"error": f"Error al guardar en la base de datos: {str(e)}"}), 500

        print("Proceso completado exitosamente.")  # Mensaje de depuración
        return jsonify({
            "scientific_name": scientific_name
        })

    except Exception as e:
        print(f"Error general en /upload: {str(e)}")  # Mensaje de depuración
        return jsonify({"error": f"Error general: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)