import mysql.connector
import numpy as np
from tensorflow.keras.models import load_model
from sklearn.preprocessing import LabelEncoder
import time
import joblib

# Cargar el modelo, LabelEncoder y scaler
model = load_model('modelo_entrenado.keras')  # Cambiado a .keras
label_encoder = joblib.load('label_encoder.pkl')
scaler = joblib.load('scaler.pkl')  # Asegúrate de guardar el scaler durante el entrenamiento

def get_latest_data():
    """
    Obtiene los últimos 5 registros de la base de datos.
    """
    try:
        with mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="bd_helios"
        ) as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT bpm, SPo2
                    FROM bpm_data
                    ORDER BY timestamp DESC
                    LIMIT 5
                """
                cursor.execute(query)
                latest_data = cursor.fetchall()
                return np.array(latest_data)
    except Exception as e:
        print(f"❌ Error al conectar a la base de datos: {e}")
        return None

def preprocess_data(data):
    """
    Preprocesa los datos para la predicción.
    """
    if data is None or len(data) < 5:
        print("No hay suficientes datos para realizar la predicción.")
        return None

    if np.any(np.isnan(data)) or np.any(data == None):
        print("Datos incompletos o nulos.")
        return None

    # Normalizar los datos
    data_normalized = scaler.transform(data)

    # Asegurar la forma correcta: (1, 5 pasos de tiempo, 2 características)
    return data_normalized.reshape((1, 5, 2))

def predict_risk(model, X_new):
    """
    Realiza la predicción y decodifica el resultado.
    """
    try:
        predictions = model.predict(X_new)
        print(f"Predicciones crudas: {predictions}")

        # Obtener el índice de la clase con mayor probabilidad
        predicted_classes = np.argmax(predictions, axis=1)
        print(f"Índices predichos: {predicted_classes}")

        # Verificar si el índice es válido antes de decodificar
        if predicted_classes[0] >= len(label_encoder.classes_):
            print("⚠️ Índice fuera de rango en la predicción. Revisar entrenamiento del modelo.")
            return None

        # Decodificar la predicción
        predicted_risk = label_encoder.inverse_transform(predicted_classes)
        return predicted_risk[0]
    except Exception as e:
        print(f"❌ Error durante la predicción: {e}")
        return None

def handle_event(predicted_risk):
    """
    Maneja el evento predicho.
    """
    if predicted_risk == "⚠️ Estrés cardíaco extremo":
        print("⚠️ Evento de Estrés detectado")
    elif predicted_risk == "⚠️ Fatiga extrema o hipotermia":
        print("⚠️ Evento de Fatiga detectado")
    elif predicted_risk == "⚠️ Hipoxia o intoxicación por humo":
        print("⚠️ Evento de Hipoxia detectado")
    else:
        print(f"✅ Estado normal: {predicted_risk}")

# Bucle principal
while True:
    # Obtener los últimos datos
    latest_data = get_latest_data()

    # Preprocesar los datos
    X_new = preprocess_data(latest_data)

    if X_new is None:
        print("Esperando 5 segundos antes de reintentar...")
        time.sleep(5)
        continue

    # Realizar la predicción
    predicted_risk = predict_risk(model, X_new)

    if predicted_risk is None:
        print("Esperando 60 segundos antes de reintentar...")
        time.sleep(60)
        continue

    # Manejar el evento predicho
    handle_event(predicted_risk)

    # Esperar 15 segundos antes de la siguiente iteración
    time.sleep(15)