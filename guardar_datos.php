<?php
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST");
header("Access-Control-Allow-Headers: Content-Type");

// Configuración de la base de datos
$host = "localhost"; // Cambia si es necesario
$dbname = "bd_helios"; // Nombre de la base de datos
$username = "root"; // Usuario de la base de datos
$password = ""; // Contraseña de la base de datos

// Conexión con la base de datos usando PDO
try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    die(json_encode(["status" => "error", "message" => "Error de conexión: " . $e->getMessage()]));
}

// Verificar si se enviaron los datos correctamente
if ($_SERVER["REQUEST_METHOD"] === "POST") {
    // Leer los datos recibidos desde el ESP8266/ESP32
    $id_user = isset($_POST['id_user']) ? intval($_POST['id_user']) : null;
    $bpm = isset($_POST['bpm']) ? floatval($_POST['bpm']) : null;
    $spo2 = isset($_POST['SPo2']) ? floatval($_POST['SPo2']) : null;

    // Verificar que los valores no sean nulos y sean válidos
    if ($id_user !== null && $bpm !== null && $spo2 !== null && $bpm > 0 && $spo2 > 0) {
        try {
            // Preparar la consulta SQL
            $stmt = $pdo->prepare("INSERT INTO bpm_data (id_user, bpm, SPo2, timestamp) VALUES (:id_user, :bpm, :spo2, :timestamp)");

            // Bind de los valores
            $stmt->bindValue(":id_user", $id_user, PDO::PARAM_INT);
            $stmt->bindValue(":bpm", $bpm, PDO::PARAM_STR);
            $stmt->bindValue(":spo2", $spo2, PDO::PARAM_STR);
            $stmt->bindValue(":timestamp", date('Y-m-d H:i:s'), PDO::PARAM_STR);

            // Ejecutar la consulta
            $stmt->execute();

            // Respuesta exitosa
            echo json_encode(["status" => "success", "message" => "Datos insertados correctamente."]);
        } catch (PDOException $e) {
            echo json_encode(["status" => "error", "message" => "Error al insertar los datos: " . $e->getMessage()]);
        }
    } else {
        echo json_encode(["status" => "error", "message" => "Datos BPM, SPo2 o ID de usuario no válidos."]);
    }
} else {
    echo json_encode(["status" => "error", "message" => "Método no permitido."]);
}
?>
