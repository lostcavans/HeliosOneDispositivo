import os
import mysql.connector
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
import numpy as np
import joblib
from sklearn.metrics import confusion_matrix, classification_report
import seaborn as sns
import matplotlib.pyplot as plt

# Conexión a la base de datos MySQL
try:
    with mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="bd_helios"
    ) as conn:
        query = """
            SELECT bpm, SPo2, estado, timestamp
            FROM bpm_data
            ORDER BY timestamp DESC
        """
        df = pd.read_sql(query, conn)
except Exception as e:
    print(f"❌ Error al conectar a la base de datos: {e}")
    exit()

# Verificar datos nulos
if df.isnull().any().any():
    print("Advertencia: Hay datos nulos en el DataFrame.")
    df = df.dropna()

# Convertir 'timestamp' a formato datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Convertir 'estado' en etiquetas numéricas usando LabelEncoder
label_encoder = LabelEncoder()
df['estado_encoded'] = label_encoder.fit_transform(df['estado'])

# Guardar el LabelEncoder para usarlo en predicciones futuras
joblib.dump(label_encoder, 'label_encoder.pkl')

# Normalizar características
scaler = StandardScaler()
df[['bpm', 'SPo2']] = scaler.fit_transform(df[['bpm', 'SPo2']])

# Guardar el scaler para usarlo en predicciones futuras
joblib.dump(scaler, 'scaler.pkl')

# Crear características (X) y etiquetas (y)
X, y = [], []
for i in range(5, len(df)):
    X.append(df[['bpm', 'SPo2']].iloc[i-5:i].values)
    y.append(df['estado_encoded'].iloc[i])

X = np.array(X)
y = np.array(y)

# Ajustar el número de clases dinámicamente
num_classes = np.max(y) + 1
y = to_categorical(y, num_classes=num_classes)

# Dividir en conjunto de entrenamiento y prueba (80%-20%)
train_size = int(len(X) * 0.8)
X_train, X_test = X[:train_size], X[train_size:]
y_train, y_test = y[:train_size], y[train_size:]

# Crear el modelo LSTM
model = Sequential([
    LSTM(50, activation='relu', return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2])),
    Dropout(0.2),
    LSTM(50, activation='relu'),
    Dropout(0.2),
    Dense(num_classes, activation='softmax')
])

# Compilar el modelo
model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# Configurar EarlyStopping y ModelCheckpoint
early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
checkpoint = ModelCheckpoint('mejor_modelo.keras', monitor='val_accuracy', save_best_only=True, mode='max')

# Entrenar el modelo
try:
    history = model.fit(
        X_train, y_train,
        epochs=500,
        batch_size=32,
        validation_split=0.2,
        callbacks=[early_stopping, checkpoint]
    )
except Exception as e:
    print(f"❌ Error durante el entrenamiento: {e}")
    exit()

# Evaluar el modelo
try:
    loss, accuracy = model.evaluate(X_test, y_test)
    print(f"Precisión del modelo: {accuracy * 100:.2f}%")
except Exception as e:
    print(f"❌ Error durante la evaluación: {e}")
    exit()

# Matriz de confusión y reporte de clasificación
try:
    y_pred = model.predict(X_test)
    y_pred_classes = np.argmax(y_pred, axis=1)
    y_true_classes = np.argmax(y_test, axis=1)

    # Obtener las clases únicas presentes en y_true_classes
    unique_classes = np.unique(y_true_classes)
    print("Clases presentes en y_true_classes:", unique_classes)

    # Filtrar target_names para que coincida con las clases presentes
    target_names = label_encoder.classes_[unique_classes]
    print("Nombres de las clases presentes:", target_names)

    # Generar la matriz de confusión
    conf_matrix = confusion_matrix(y_true_classes, y_pred_classes)
    sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='Blues', xticklabels=target_names, yticklabels=target_names)
    plt.xlabel('Predicho')
    plt.ylabel('Real')
    plt.show()

    # Generar el reporte de clasificación
    print(classification_report(y_true_classes, y_pred_classes, labels=unique_classes, target_names=target_names))
except Exception as e:
    print(f"❌ Error durante la generación de métricas: {e}")
    exit()

# Guardar el modelo entrenado
try:
    model.save("modelo_entrenado.keras")
    print("✅ Modelo guardado correctamente como 'modelo_entrenado.keras'.")
except Exception as e:
    print(f"❌ Error al guardar el modelo: {e}")