from flask import Flask, request, jsonify, render_template
import psycopg2
import os
import requests
import time

app = Flask(__name__)

# Configuración de la base de datos PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Crear tabla si no existe
def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plant_data (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            organ TEXT NOT NULL,
            location TEXT,
            gps_location TEXT,  -- Nueva columna para la ubicación GPS
            scientific_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Nueva columna para la fecha y hora
        )
    ''')
    conn.commit()
    conn.close()

initialize_database()

# Ruta principal
@app.route('/')
def index():
    # Obtener todos los registros de la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM plant_data ORDER BY id DESC')
    records = cursor.fetchall()
    conn.close()

    return render_template('index.html', records=records)

# Endpoint para recibir datos
@app.route('/upload', methods=['POST'])
def upload():
    try:
        print("Recibiendo solicitud desde el frontend...")
        start_time = time.time()

        data = request.json
        username = data.get('username')
        organ = data.get('organ')
        location = data.get('location')  # Ubicación general (puede ser "Desconocida")
        gps_location = data.get('gps_location')  # Ubicación GPS específica

        if not username or not organ:
            return jsonify({"error": "Faltan campos obligatorios"}), 400

        print(f"Enviando solicitud a la API de Pl@ntNet... ({time.time() - start_time:.2f} segundos)")
        PLANTNET_API_KEY = "2b103McS4Rs5cVcuZS9e2ObBKe"
        PLANTNET_API_URL = f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_API_KEY}"
        response = requests.post(
            PLANTNET_API_URL,
            files={"images": ("image.png", b"", "image/png")},  # Sin imagen por ahora
            data={"organs": organ},
            timeout=120
        )

        print(f"Respuesta recibida de la API de Pl@ntNet: {response.status_code} ({time.time() - start_time:.2f} segundos)")
        if response.status_code != 200:
            return jsonify({"error": f"Error en la API de Pl@ntNet: {response.status_code}"}), 500

        result = response.json()
        suggestions = result.get("results", [])
        if not suggestions:
            return jsonify({"error": "No se encontraron sugerencias"}), 404

        scientific_name = suggestions[0]["species"]["scientificNameWithoutAuthor"]

        print(f"Guardando datos en la base de datos... ({time.time() - start_time:.2f} segundos)")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO plant_data (username, organ, location, gps_location, scientific_name)
            VALUES (%s, %s, %s, %s, %s)
        ''', (username, organ, location, gps_location, scientific_name))
        conn.commit()
        conn.close()

        print(f"Proceso completado exitosamente. Tiempo total: {time.time() - start_time:.2f} segundos")
        return jsonify({"scientific_name": scientific_name})

    except Exception as e:
        print(f"Error general en /upload: {str(e)}")
        return jsonify({"error": f"Error general: {str(e)}"}), 500

# Endpoint para obtener la IP pública del servidor
@app.route('/get-ip', methods=['GET'])
def get_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json')
        if response.status_code == 200:
            ip_data = response.json()
            public_ip = ip_data.get('ip')
            return jsonify({"public_ip": public_ip}), 200
        else:
            return jsonify({"error": "No se pudo obtener la IP pública"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)