import pymysql
import numpy as np
import threading
import time
from datetime import datetime, timedelta
import random  # Para generar probabilidades

# --- Parámetros ---
id_user = 50  # ID del usuario
evento_activado = None  # Evento activado (estrés, fatiga, hipoxia)
fin_evento = None  # Hora de finalización del evento
tiempo_sin_riesgo = None  # Hora para iniciar un nuevo evento
ultimo_evento = None  # Hora del último evento

# --- Conectar a la base de datos ---
def conectar_db():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='bd_helios'
    )

# --- Función para simular la evolución de los eventos ---
def simular_evento(evento):
    if evento == "⚠️ Estrés cardíaco extremo":
        return round(np.random.uniform(140, 180), 2), round(np.random.uniform(90, 100), 2)
    elif evento == "⚠️ Fatiga extrema o hipotermia":
        return round(np.random.uniform(50, 70), 2), round(np.random.uniform(85, 95), 2)
    elif evento == "⚠️ Hipoxia o intoxicación por humo":
        return round(np.random.uniform(70, 110), 2), round(np.random.uniform(75, 85), 2)
    return round(np.random.uniform(60, 100), 2), round(np.random.uniform(95, 100), 2)

# --- Función para generar datos en tiempo real ---
def generar_datos():
    global evento_activado, fin_evento, tiempo_sin_riesgo, ultimo_evento
    while True:
        now = datetime.now()

        # Si un evento está activo y ya pasó el tiempo, lo desactiva
        if evento_activado and now >= fin_evento:
            print(f"✅ Evento finalizado: {evento_activado}. Iniciando periodo sin riesgo.")
            evento_activado = None
            tiempo_sin_riesgo = now + timedelta(seconds=600)  # 30 segundos sin riesgo

        # Si hay tiempo sin riesgo
        if tiempo_sin_riesgo and now >= tiempo_sin_riesgo:
            print("✅ Sin riesgo")
            tiempo_sin_riesgo = None  # Reiniciar el tiempo sin riesgo

        # Determinar valores de BPM y SpO2
        if evento_activado:
            bpm, spo2 = simular_evento(evento_activado)
        else:
            bpm, spo2 = simular_evento("✅ Sin riesgo")

        # Generar un evento si no hay uno activo y ha pasado suficiente tiempo
        if evento_activado is None and (not ultimo_evento or now - ultimo_evento >= timedelta(minutes=2)):
            probabilidad_evento = random.random()

            if probabilidad_evento < 0.10:
                evento_activado = "⚠️ Estrés cardíaco extremo"
            elif probabilidad_evento < 0.20:
                evento_activado = "⚠️ Fatiga extrema o hipotermia"
            elif probabilidad_evento < 0.30:
                evento_activado = "⚠️ Hipoxia o intoxicación por humo"

            if evento_activado:
                fin_evento = now + timedelta(minutes=2)
                ultimo_evento = now
                print(f"🔥 Evento iniciado: {evento_activado}")

        # Insertar en la base de datos
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            query = "INSERT INTO bpm_data (id_user, bpm, SPo2, estado, timestamp) VALUES (%s, %s, %s, %s, %s)"
            estado_actual = evento_activado if evento_activado else "✅ Sin riesgo"
            cursor.execute(query, (id_user, bpm, spo2, estado_actual, now))
            conn.commit()
            cursor.close()
            conn.close()
            print(f"{estado_actual} - BPM: {bpm}, SpO2: {spo2}, Hora: {now}")
        except Exception as e:
            print(f"❌ Error al insertar datos: {e}")

        # Esperar 10 segundos antes de la próxima medición
        time.sleep(15)

# --- Iniciar la simulación en un hilo separado ---
hilo = threading.Thread(target=generar_datos)
hilo.daemon = True
hilo.start()

# Mantener el script corriendo
while True:
    time.sleep(1)