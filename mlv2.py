import mysql.connector
import numpy as np
from tensorflow.keras.models import load_model
import time
import joblib
from datetime import datetime
import warnings

# Configuración global
CONFIG = {
    "model_path": "modelo_entrenado.keras",
    "label_encoder_path": "label_encoder.pkl",
    "scaler_path": "scaler.pkl",
    "window_size": 5,
    "db_config": {
        "host": "localhost",
        "user": "root",
        "password": "",
        "database": "bd_helios"
    },
    "default_user_id": 50,
    "feature_names": ['bpm', 'SPo2']  # Nombres de características usados en entrenamiento
}

# Suprimir warnings específicos de sklearn
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

# Cargar recursos del modelo
try:
    model = load_model(CONFIG['model_path'])
    label_encoder = joblib.load(CONFIG['label_encoder_path'])
    scaler = joblib.load(CONFIG['scaler_path'])
    print("✅ Modelo y preprocesadores cargados correctamente")
    
    # Verificar clases conocidas
    print(f"🔡 Clases conocidas por el modelo: {list(label_encoder.classes_)}")
except Exception as e:
    print(f"❌ Error al cargar recursos del modelo: {e}")
    exit()

def ensure_mysql_compatible(value):
    """Convierte valores NumPy a tipos nativos de Python compatibles con MySQL"""
    if isinstance(value, (np.integer)):
        return int(value)
    elif isinstance(value, (np.floating)):
        return float(value)
    return value

def get_latest_data():
    """Obtiene los últimos registros necesarios para la predicción"""
    try:
        with mysql.connector.connect(**CONFIG['db_config']) as conn:
            with conn.cursor() as cursor:
                query = f"""
                    SELECT bpm, SPo2
                    FROM bpm_data
                    ORDER BY timestamp DESC
                    LIMIT {CONFIG['window_size']}
                """
                cursor.execute(query)
                data = cursor.fetchall()
                
                if len(data) < CONFIG['window_size']:
                    print(f"⚠️ Necesita {CONFIG['window_size']} registros, solo hay {len(data)}")
                    return None
                
                # Convertir a array numpy con nombres de características
                arr = np.array(data, dtype=np.float64)
                return arr
    except Exception as e:
        print(f"❌ Error en get_latest_data(): {e}")
        return None

def preprocess_data(raw_data):
    """Preprocesa los datos igual que durante el entrenamiento"""
    if raw_data is None:
        return None
    
    try:
        # Convertir a DataFrame con nombres de columnas para evitar warnings
        import pandas as pd
        df = pd.DataFrame(raw_data, columns=CONFIG['feature_names'])
        
        # Normalización con el scaler
        normalized_data = scaler.transform(df)
        return normalized_data.reshape((1, CONFIG['window_size'], 2))
    except Exception as e:
        print(f"❌ Error en preprocess_data(): {e}")
        return None

def make_prediction(input_data):
    """Realiza la predicción usando el modelo cargado"""
    try:
        if input_data is None:
            return None, None
            
        prediction = model.predict(input_data)
        class_index = np.argmax(prediction, axis=1)[0]
        
        # Verificar que el índice es válido
        if class_index >= len(label_encoder.classes_):
            print(f"⚠️ Índice {class_index} fuera de rango. Máximo esperado: {len(label_encoder.classes_)-1}")
            return None, None
            
        label = label_encoder.inverse_transform([class_index])[0]
        return label, ensure_mysql_compatible(class_index)
    except Exception as e:
        print(f"❌ Error en make_prediction(): {e}")
        return None, None

def save_prediction(user_id, status_code):
    """Guarda la predicción en la base de datos"""
    try:
        # Validar que el código de estado sea válido
        valid_codes = {0, 1, 2, 3}  # Códigos esperados según tu modelo
        status_code = ensure_mysql_compatible(status_code)
        
        if status_code not in valid_codes:
            print(f"⚠️ Código de estado inválido: {status_code}. Usando código por defecto (3)")
            status_code = 3
        
        with mysql.connector.connect(**CONFIG['db_config']) as conn:
            with conn.cursor() as cursor:
                query = """
                    INSERT INTO prev_data 
                    (id_user, estado_prev, timestamp_prev)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(query, (
                    ensure_mysql_compatible(user_id),
                    status_code,
                    datetime.now()
                ))
                conn.commit()
                print(f"📊 Predicción guardada - ID: {user_id}, Estado: {status_code}")
                return True
    except Exception as e:
        print(f"❌ Error al guardar predicción: {e}")
        return False

def interpret_prediction(predicted_label, predicted_code, user_id=None):
    """Interpreta y actúa según la predicción"""
    if user_id is None:
        user_id = CONFIG['default_user_id']
    
    # Mapeo completo de estados conocidos
    status_mapping = {
        "⚠️ Estrés cardíaco extremo": (0, "🚨 ALERTA: Estrés cardíaco detectado!"),
        "⚠️ Fatiga extrema o hipotermia": (1, "⚠️ Alerta: Fatiga extrema detectada!"),
        "⚠️ Hipoxia o intoxicación por humo": (2, "☠️ ALERTA: Hipoxia detectada!"),
        "✅ Sin riesgo": (3, "✅ Estado normal - Sin riesgo"),
        "Normal": (3, "✅ Estado normal")  # Alias alternativo
    }
    
    # Buscar coincidencia exacta o parcial
    matched = False
    for pattern, (code, message) in status_mapping.items():
        if pattern.lower() in predicted_label.lower():
            print(message)
            save_prediction(user_id, code)
            matched = True
            break
    
    if not matched:
        print(f"🔍 Estado no reconocido: '{predicted_label}'. Guardando como normal (3)")
        save_prediction(user_id, 3)  # Por defecto a estado normal

def main_loop():
    """Bucle principal de monitoreo"""
    while True:
        try:
            # Paso 1: Obtener datos
            raw_data = get_latest_data()
            if raw_data is None:
                time.sleep(5)
                continue
                
            # Paso 2: Preprocesar
            processed_data = preprocess_data(raw_data)
            if processed_data is None:
                time.sleep(5)
                continue
                
            # Paso 3: Predecir
            label, code = make_prediction(processed_data)
            if label is None:
                time.sleep(10)
                continue
                
            # Paso 4: Interpretar y guardar
            interpret_prediction(label, code)
            
            # Esperar antes de la siguiente iteración
            time.sleep(15)
            
        except KeyboardInterrupt:
            print("\n🔌 Deteniendo el sistema...")
            break
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            time.sleep(30)

if __name__ == "__main__":
    print("🚀 Iniciando sistema de monitoreo cardíaco")
    print(f"🔍 Clases conocidas: {list(label_encoder.classes_)}")
    main_loop()