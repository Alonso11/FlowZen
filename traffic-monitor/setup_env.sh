#!/bin/bash
# Script para configurar el entorno con micromamba

set -e  # Detener si hay errores

if ! command -v micromamba &> /dev/null; then
    echo " ERROR: micromamba no encontrado"
    exit 1
fi

# Crear entorno desde environment.yml
echo ""
echo "1️⃣  Creando entorno 'rasp_project' desde environment.yml..."
micromamba create -f environment.yml -y

# Verificar instalación
echo ""
echo "2️⃣  Verificando dependencias instaladas..."
micromamba run -n rasp_project python -c "import numpy; print(f'✓ NumPy {numpy.__version__}')"
micromamba run -n rasp_project python -c "import cv2; print(f'✓ OpenCV {cv2.__version__}')"
micromamba run -n rasp_project python -c "import flask; print(f'✓ Flask {flask.__version__}')"
micromamba run -n rasp_project python -c "import tflite_runtime; print('✓ TFLite Runtime OK')"

echo ""
echo " Entorno configurado correctamente"
echo ""
