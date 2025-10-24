#!/bin/bash
# Script para descargar el modelo TFLite MobileNet-SSD

set -e

echo "Descargando modelo TFLite MobileNet-SSD"

# Crear directorio de modelos si no existe
mkdir -p models
cd models

# URL del modelo
MODEL_URL="https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip"
ZIP_FILE="coco_ssd_mobilenet_v1.zip"

# Descargar modelo
echo "Descargando desde: $MODEL_URL"
wget -O "$ZIP_FILE" "$MODEL_URL"

# Extraer
echo "Extrayendo archivos..."
unzip -o "$ZIP_FILE"

# Verificar que el modelo existe
if [ -f "detect.tflite" ]; then
    echo "Modelo descargado correctamente: detect.tflite"
    ls -lh detect.tflite
else
    echo "Error: detect.tflite no encontrado"
    exit 1
fi

rm "$ZIP_FILE"

if [ -f "labelmap.txt" ]; then
    echo "Labelmap encontrado: labelmap.txt"
else
    echo "Advertencia: labelmap.txt no encontrado (opcional)"
fi

cd ..

echo ""
echo "Descarga completada"
echo ""
