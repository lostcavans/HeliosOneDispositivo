import pymysql
import numpy as np
import threading
import time
from datetime import datetime, timedelta
import random
import math

# --- Configuración realista ---
CONFIG = {
    "id_user": 50,
    "db_config": {
        "host": "localhost",
        "user": "root",
        "password": "",
        "database": "bd_helios"
    },
    "intervalo_muestreo": 15,  # segundos entre mediciones
    "probabilidad_evento": 0.05,  # 5% de chance de evento por chequeo
    "duracion_evento": timedelta(minutes=10),  # Duración típica de un evento
    "periodo_minimo_normal": timedelta(minutes=30),  # Tiempo mínimo entre eventos
    "valores_normales": {
        "bpm": (60, 100),
        "spo2": (95, 100)
    },
    "eventos": {
        "estres": {
            "nombre": "⚠️ Estrés cardíaco extremo",
            "bpm": (140, 180),
            "spo2": (90, 100),
            "probabilidad": 0.4  # 40% de los eventos
        },
        "fatiga": {
            "nombre": "⚠️ Fatiga extrema o hipotermia",
            "bpm": (50, 70),
            "spo2": (85, 95),
            "probabilidad": 0.3  # 30% de los eventos
        },
        "hipoxia": {
            "nombre": "⚠️ Hipoxia o intoxicación por humo",
            "bpm": (70, 110),
            "spo2": (75, 85),
            "probabilidad": 0.3  # 30% de los eventos
        }
    }
}

class SimuladorSignosVitales:
    def __init__(self):
        self.evento_actual = None
        self.inicio_evento = None
        self.fin_evento = None
        self.ultimo_evento = None
        self.transicion_activa = False
        self.proximo_evento_posible = datetime.now()

    def conectar_db(self):
        """Conexión a la base de datos"""
        try:
            return pymysql.connect(**CONFIG['db_config'])
        except Exception as e:
            print(f"❌ Error de conexión a DB: {e}")
            return None

    def generar_valor_suavizado(self, base, variacion_normal=5):
        """Genera valores con variación suave"""
        return base + random.uniform(-variacion_normal, variacion_normal)

    def simular_signos(self):
        """Genera valores de BPM y SpO2 según el estado actual"""
        now = datetime.now()
        
        # Estado normal
        if not self.evento_actual:
            bpm = self.generar_valor_suavizado(80)
            spo2 = self.generar_valor_suavizado(98, 2)
            return bpm, spo2, "✅ Sin riesgo"
        
        # Durante evento
        tiempo_transcurrido = (now - self.inicio_evento).total_seconds()
        duracion_total = (self.fin_evento - self.inicio_evento).total_seconds()
        progreso = min(tiempo_transcurrido / duracion_total, 1.0)
        
        # Valores base del evento
        if "estres" in self.evento_actual:
            bpm_base = 160
            spo2_base = 95
        elif "fatiga" in self.evento_actual:
            bpm_base = 60
            spo2_base = 90
        else:  # hipoxia
            bpm_base = 90
            spo2_base = 80
        
        # Suavizar transición
        if progreso < 0.2:  # Inicio del evento
            factor = progreso / 0.2
            bpm = 80 + (bpm_base - 80) * factor
            spo2 = 98 + (spo2_base - 98) * factor
        elif progreso > 0.8:  # Final del evento
            factor = (progreso - 0.8) / 0.2
            bpm = bpm_base + (80 - bpm_base) * factor
            spo2 = spo2_base + (98 - spo2_base) * factor
        else:  # Pico del evento
            bpm = bpm_base + math.sin(progreso * math.pi * 4) * 10
            spo2 = spo2_base + math.sin(progreso * math.pi * 4) * 3
        
        return bpm, spo2, self.evento_actual

    def evaluar_evento(self):
        """Determina si debe comenzar un nuevo evento"""
        now = datetime.now()
        
        # No iniciar nuevo evento si ya hay uno activo o no ha pasado el tiempo mínimo
        if self.evento_actual or now < self.proximo_evento_posible:
            return False
        
        # Chequear probabilidad de evento
        if random.random() > CONFIG['probabilidad_evento']:
            return False
        
        # Seleccionar tipo de evento
        r = random.random()
        acumulado = 0
        for evento in CONFIG['eventos'].values():
            acumulado += evento['probabilidad']
            if r <= acumulado:
                self.evento_actual = evento['nombre']
                self.inicio_evento = now
                self.fin_evento = now + CONFIG['duracion_evento']
                self.ultimo_evento = now
                self.proximo_evento_posible = now + CONFIG['periodo_minimo_normal']
                print(f"🚨 Iniciando evento: {self.evento_actual}")
                return True
        return False

    def finalizar_evento(self):
        """Finaliza el evento actual"""
        print(f"✅ Finalizando evento: {self.evento_actual}")
        self.evento_actual = None
        self.inicio_evento = None
        self.fin_evento = None

    def insertar_datos(self, bpm, spo2, estado):
        """Guarda los datos en la base de datos"""
        try:
            conn = self.conectar_db()
            if not conn:
                return
                
            with conn.cursor() as cursor:
                query = """
                    INSERT INTO bpm_data 
                    (id_user, bpm, SPo2, estado, timestamp) 
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    CONFIG['id_user'],
                    round(bpm, 2),
                    round(spo2, 2),
                    estado,
                    datetime.now()
                ))
                conn.commit()
                print(f"📊 {estado} - BPM: {round(bpm)}, SpO2: {round(spo2)}")
        except Exception as e:
            print(f"❌ Error al insertar datos: {e}")
        finally:
            if conn:
                conn.close()

    def ejecutar_ciclo(self):
        """Ejecuta un ciclo completo de simulación"""
        now = datetime.now()
        
        # Verificar si debe finalizar un evento
        if self.evento_actual and now >= self.fin_evento:
            self.finalizar_evento()
        
        # Evaluar inicio de nuevo evento
        self.evaluar_evento()
        
        # Generar y guardar datos
        bpm, spo2, estado = self.simular_signos()
        self.insertar_datos(bpm, spo2, estado)

    def iniciar_simulacion(self):
        """Inicia la simulación en tiempo real"""
        print("🚀 Iniciando simulador de signos vitales - Modo Realista")
        print(f"⏱  Intervalo de muestreo: {CONFIG['intervalo_muestreo']} segundos")
        
        while True:
            self.ejecutar_ciclo()
            time.sleep(CONFIG['intervalo_muestreo'])

# --- Iniciar la simulación ---
if __name__ == "__main__":
    simulador = SimuladorSignosVitales()
    hilo = threading.Thread(target=simulador.iniciar_simulacion)
    hilo.daemon = True
    hilo.start()
    
    # Mantener el script principal ejecutándose
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🔴 Simulación detenida")