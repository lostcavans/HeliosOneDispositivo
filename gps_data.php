<?php
$host = "localhost";
$dbname = "bd_helios";
$username = "root";
$password = "";

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // Mostrar los datos recibidos para depuración
    echo "Datos recibidos: ";
    print_r($_POST);

    // Obtener datos POST
    $id_user   = isset($_POST['id_user']) ? $_POST['id_user'] : null;
    $latitude  = isset($_POST['latitude']) ? $_POST['latitude'] : null;
    $longitude = isset($_POST['longitude']) ? $_POST['longitude'] : null;
    $speed     = isset($_POST['speed']) ? $_POST['speed'] : null;
    $altitude  = isset($_POST['altitude']) ? $_POST['altitude'] : null;
    $satelites = isset($_POST['satelites']) ? $_POST['satelites'] : null;

    if ($id_user !== null && $latitude !== null && $longitude !== null && $speed !== null && $altitude !== null && $satelites !== null) {
        $sql = "INSERT INTO gps_data (id_user, latitude, longitude, speed, altitude, satelites, timestamp) 
                VALUES (:id_user, :latitude, :longitude, :speed, :altitude, :satelites, NOW())";
        $stmt = $pdo->prepare($sql);
        $stmt->execute([
            ':id_user' => $id_user,
            ':latitude' => $latitude,
            ':longitude' => $longitude,
            ':speed' => $speed,
            ':altitude' => $altitude,
            ':satelites' => $satelites
        ]);

        echo "Data inserted successfully!";
    } else {
        echo "Error: Faltan datos en la solicitud POST.";
    }
} catch (PDOException $e) {
    echo "Error: " . $e->getMessage();
}
?>
