<?php
/**
 * Script para obtener datos de estaciones meteorológicas EcoWitt
 * Guarda los resultados en archivo de texto
 */

require_once __DIR__ . '/config.php';

$estaciones = [
    'INTA_SANMARTIN' => '30:83:98:A6:B3:AA',
    'INTA_POCITO' => '30:83:98:A7:43:1B',
    'VALLE_FERTIL' => '30:83:98:A7:1E:10',
    'LOS_PIONEROS' => '30:83:98:A7:09:CD',
    'CUESTA_Viento' => '30:83:98:A5:52:40',
    'ULLUM_EMBALSE' => '30:83:98:A5:CB:17',
    'PUNTA_NEGRA' => '30:83:98:A6:BB:72',
    'CARACOLES' => '30:83:98:A7:47:39',
];

$estacion_ecohumus = [
    'ECOHUMUS' => 'BC:FF:4D:F7:DF:DA'
];

function obtenerDatosAPI($macAddress, $appKey, $apiKey) {
    $url = sprintf(
        'https://api.ecowitt.net/api/v3/device/real_time?application_key=%s&api_key=%s&mac=%s&call_back=all&temp_unitid=1&pressure_unitid=3&wind_speed_unitid=7&rainfall_unitid=12&solar_irradiance_unitid=16',
        urlencode($appKey),
        urlencode($apiKey),
        urlencode($macAddress)
    );
    
    try {
        $json = file_get_contents($url);
        if ($json === false) {
            throw new Exception("Error al obtener datos de la API para MAC: {$macAddress}");
        }
        
        $data = json_decode($json, true);
        
        if ($data === null || !isset($data['time'])) {
            throw new Exception("Error al decodificar JSON para MAC: {$macAddress}");
        }
        
        return $data;
    } catch (Exception $e) {
        echo "Error: " . $e->getMessage() . "\n";
        return null;
    }
}

function extraerDatosMeteorologicos($data, $estacion) {
    return [
        'estacion' => $estacion,
        'time_unix' => $data['time'],
        'fecha' => date("Y-m-d", $data['time']),
        'hora' => date("H:i", $data['time']),
        'temp' => $data['data']['outdoor']['temperature']['value'] ?? null,
        'humedad' => $data['data']['outdoor']['humidity']['value'] ?? null,
        'viento' => $data['data']['wind']['wind_speed']['value'] ?? null,
        'viento_rafaga' => $data['data']['wind']['wind_gust']['value'] ?? null,
        'direcc' => $data['data']['wind']['wind_direction']['value'] ?? null,
        'presion_relativa' => $data['data']['pressure']['relative']['value'] ?? null,
        'presion_absoluta' => $data['data']['pressure']['absolute']['value'] ?? null,
        'rain_daily' => $data['data']['rainfall']['daily']['value'] ?? null,
        'rain_monthly' => $data['data']['rainfall']['monthly']['value'] ?? null,
        'solar' => $data['data']['solar_and_uvi']['solar']['value'] ?? null,
        'termica' => $data['data']['outdoor']['feels_like']['value'] ?? null,
        'rocio' => $data['data']['outdoor']['dew_point']['value'] ?? null,
    ];
}

function formatearLinea($datos) {
    $lineas = [];
    foreach ($datos as $key => $value) {
        $lineas[] = "$key: " . (is_null($value) ? 'N/A' : $value);
    }
    return implode("\n", $lineas);
}

$output = "";
$output .= "===========================================\n";
$output .= "DATOS METEOROLOGICOS - " . date("Y-m-d H:i:s") . "\n";
$output .= "===========================================\n\n";

foreach ($estaciones as $nombre => $mac) {
    $output .= "-------------------------------------------\n";
    $output .= "ESTACION: $nombre (MAC: $mac)\n";
    $output .= "-------------------------------------------\n";
    
    $data = obtenerDatosAPI($mac, API_APPLICATION_KEY, API_KEY);
    
    if ($data === null) {
        $output .= "Error: No se pudieron obtener datos.\n\n";
        continue;
    }
    
    $datos = extraerDatosMeteorologicos($data, $nombre);
    $output .= formatearLinea($datos) . "\n\n";
}

foreach ($estacion_ecohumus as $nombre => $mac) {
    $output .= "-------------------------------------------\n";
    $output .= "ESTACION: $nombre (MAC: $mac)\n";
    $output .= "-------------------------------------------\n";
    
    $data = obtenerDatosAPI($mac, API_APPLICATION_KEY_ECOHUMUS, API_KEY_ECOHUMUS);
    
    if ($data === null) {
        $output .= "Error: No se pudieron obtener datos.\n\n";
        continue;
    }
    
    $datos = extraerDatosMeteorologicos($data, $nombre);
    $output .= formatearLinea($datos) . "\n\n";
}

$output .= "===========================================\n";
$output .= "FIN DEL REPORTE\n";
$output .= "===========================================\n";

$archivo = __DIR__ . '/datos_meteorologicos.txt';
file_put_contents($archivo, $output);

echo $output;
echo "\n>> Datos guardados en: $archivo\n";
