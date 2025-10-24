# Sistema de Monitoreo Inteligente de Tránsito

Sistema embebido de detección, clasificación y tracking de objetos en tiempo real utilizando Edge AI sobre Raspberry Pi 4 con Linux embebido (Yocto Project).

**Proyecto:** Cruces Inteligentes con EDGE AI Embebido
**Institución:** Tecnológico de Costa Rica
**Curso:** Taller de Sistemas Embebidos
**Equipo:** Lizzy González, Andrés Bonilla, Fabián Gómez

---

## Características Principales

- **Detección en tiempo real** de vehículos, peatones y fauna
- **Edge Computing** - Todo el procesamiento ocurre en la Raspberry Pi
- **Streaming HLS** con codificación GPU (h264_omx)
- **Dashboard web** accesible desde navegador
- **Tracking de objetos** con IDs únicos
- **Estadísticas detalladas** exportadas a JSON
- **Modelo headless** - No requiere monitor, teclado ni mouse

---

## Arquitectura del Sistema

### Pipeline de Procesamiento

```
┌─────────────┐    ┌──────────────┐    ┌────────────┐    ┌───────────────┐
│   Cámara    │───▶│ Preproceso   │───▶│ Inferencia │───▶│ Postproceso   │
│ (640x480)   │    │ (300x300 RGB)│    │  TFLite    │    │  (NMS, IoU)   │
└─────────────┘    └──────────────┘    └────────────┘    └───────────────┘
                                                                  │
                    ┌──────────────────────────────────────────┘
                    ▼
        ┌───────────────────┐    ┌──────────────┐    ┌──────────────────┐
        │    Tracking       │───▶│ Estadísticas │    │  Streaming HLS   │
        │   (IoU Tracker)   │    │   (JSON)     │    │  (FFmpeg + GPU)  │
        └───────────────────┘    └──────────────┘    └──────────────────┘
                                                                  │
                                                                  ▼
                                                        ┌──────────────────┐
                                                        │  Dashboard Web   │
                                                        │ (Flask + HLS.js) │
                                                        └──────────────────┘
```

### Módulos Funcionales

| Módulo | Archivo | Responsabilidad |
|--------|---------|-----------------|
| **F1** | `modules/capture.py` | Captura de video desde cámara o archivo |
| **F2** | `modules/preprocess.py` | Redimensionamiento y normalización |
| **F3** | `modules/inference.py` | Inferencia con MobileNet-SSD v2 (TFLite) |
| **F4** | `modules/postprocess.py` | Filtrado, NMS, conversión de coordenadas |
| **F5** | `modules/tracker.py` | Tracking IoU con IDs únicos |
| **F6** | `modules/storage.py` | Acumulación de stats en RAM y export JSON |
| **F7** | `modules/streaming.py` | Streaming FFmpeg HLS |
| **Web** | `web_app.py` | Servidor Flask + API REST |

---

## Requisitos

### Hardware

- **Raspberry Pi 4** (2GB RAM mínimo, 4GB recomendado)
- **Cámara** (CSI o USB)
- **Tarjeta SD** (16GB mínimo, 32GB recomendado)
- **Conectividad WiFi** o Ethernet

### Software (Desarrollo en PC)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip ffmpeg

# Instalar dependencias Python
pip3 install -r requirements.txt
```

### Software (Raspberry Pi con Yocto)

Ver `YOCTO_DEPENDENCIES.md` para instrucciones completas de integración.

---

## Instalación y Configuración

### 1. Descargar el Modelo TFLite

```bash
cd traffic-monitor/models/

# Opción A: MobileNet-SSD v1 (cuantizado, más rápido)
wget https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
unzip coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
mv detect.tflite .

# Opción B: MobileNet-SSD v2 (mayor precisión)
# Descargar desde TensorFlow Hub y convertir a TFLite
```

### 2. Configuración del Sistema

Editar `config.py` según necesidades:

```python
# Fuente de video
VIDEO_SOURCE = 0  # 0 = cámara, o ruta a archivo MP4

# Resolución
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# FPS objetivo
TARGET_FPS = 15

# Confianza mínima para detecciones
CONFIDENCE_THRESHOLD = 0.5

# Streaming
ENABLE_STREAMING = True
USE_GPU_ENCODING = True  # h264_omx en Raspberry Pi
```

---

## Uso

### Modo 1: Raspberry Pi Headless (Producción)

**Paso 1: Conectar vía SSH**
```bash
# Desde tu laptop (en la misma red WiFi que la Raspberry Pi)
ssh root@192.168.1.100  # Reemplazar con IP real
```

**Paso 2: Iniciar aplicación**
```bash
cd /usr/share/traffic-monitor
python3 main.py
```

La aplicación inicia automáticamente:
- Pipeline de detección
- Streaming FFmpeg (archivos HLS en `/tmp`)
- Servidor web Flask en puerto 5000

**Paso 3: Visualizar desde navegador**
```
http://192.168.1.100:5000
```

**Paso 4: Detener y generar estadísticas**
```bash
# En la terminal SSH, presionar Ctrl+C
# Se genera automáticamente: results/stats_{timestamp}.json
```

### Modo 2: Desarrollo en PC (Testing)

```bash
# Procesar video pregrabado
python3 main.py --input ../Video1.mp4

# Usar cámara web USB
python3 main.py --input 0

# Deshabilitar streaming (más ligero para testing)
python3 main.py --input ../Video1.mp4 --no-streaming

# Usar modelo custom
python3 main.py --model /path/to/custom_model.tflite
```

### Opciones de Línea de Comandos

```
usage: main.py [-h] [--input INPUT] [--no-streaming] [--no-web] [--model MODEL]

Sistema de Monitoreo Inteligente de Tránsito

optional arguments:
  -h, --help            Mostrar ayuda
  --input INPUT, -i INPUT
                        Fuente de video: 0 para cámara, o ruta a MP4
  --no-streaming        Deshabilitar streaming FFmpeg
  --no-web             Deshabilitar servidor web
  --model MODEL        Ruta al modelo TFLite (sobreescribe config)
```

---

## Estructura del Proyecto

```
traffic-monitor/
├── main.py                    # Orquestador principal
├── config.py                  # Configuración del sistema
├── web_app.py                 # Servidor Flask
├── modules/
│   ├── __init__.py
│   ├── capture.py            # F1: Captura de video
│   ├── preprocess.py         # F2: Preprocesamiento
│   ├── inference.py          # F3: Inferencia TFLite
│   ├── postprocess.py        # F4: Post-procesamiento
│   ├── tracker.py            # F5: Tracking IoU
│   ├── storage.py            # F6: Estadísticas
│   └── streaming.py          # F7: Streaming FFmpeg
├── templates/
│   └── index.html            # Dashboard web
├── static/                   # (opcional) CSS/JS externos
├── models/
│   ├── detect.tflite         # Modelo MobileNet-SSD v2
│   └── labelmap.txt          # (opcional) Mapeo de clases
├── results/                  # Estadísticas JSON generadas
├── requirements.txt          # Dependencias Python
├── YOCTO_DEPENDENCIES.md     # Guía de integración Yocto
└── README.md                 # Este archivo
```

---

## Endpoints API

### `GET /`
Página principal del dashboard

### `GET /api/stats`
Estadísticas en tiempo real (actualizado cada 1 segundo)

**Respuesta JSON:**
```json
{
  "detections": {
    "car": 45,
    "person": 12,
    "motorcycle": 3,
    "bicycle": 5,
    "bus": 1,
    "truck": 2,
    "dog": 0,
    "cat": 0
  },
  "unique_objects": {
    "car": 23,
    "person": 8,
    ...
  },
  "performance": {
    "fps": 15.2,
    "avg_fps": 14.8,
    "elapsed_time": "00:05:23",
    "elapsed_seconds": 323,
    "frames_processed": 4869,
    "avg_inference_ms": 165.3
  }
}
```

### `GET /stream.m3u8`
Playlist HLS (generada por FFmpeg)

### `GET /stream{N}.ts`
Segmentos de video HLS

### `GET /health`
Health check del servidor

---

## Formato de Estadísticas (JSON)

Al detener la aplicación con `Ctrl+C`, se genera `results/stats_{timestamp}.json`:

```json
{
  "session_info": {
    "start_time": "2025-10-23T14:30:45",
    "end_time": "2025-10-23T14:35:12",
    "duration_seconds": 267,
    "duration_formatted": "00:04:27",
    "frames_processed": 4005
  },
  "detections": {
    "total_by_class": {
      "car": 1245,
      "person": 67,
      "motorcycle": 12,
      "bicycle": 8,
      "bus": 3,
      "truck": 5,
      "dog": 2,
      "cat": 1
    },
    "unique_objects_by_class": {
      "car": 85,
      "person": 23,
      ...
    }
  },
  "performance": {
    "average_fps": 15.0,
    "min_fps": 12.3,
    "max_fps": 17.8,
    "average_inference_ms": 167.2,
    "total_inference_time_seconds": 669.5
  },
  "summary": {
    "total_detections": 1343,
    "total_unique_objects": 125,
    "classes_detected": ["car", "person", "motorcycle", ...]
  }
}
```

---

## Clases Detectables

El sistema detecta las siguientes 8 clases del dataset COCO:

| ID | Clase | Color (BGR) |
|----|-------|-------------|
| 0 | `person` | Verde (0, 255, 0) |
| 1 | `bicycle` | Cyan (255, 255, 0) |
| 2 | `car` | Azul (255, 0, 0) |
| 3 | `motorcycle` | Magenta (255, 0, 255) |
| 5 | `bus` | Naranja (0, 165, 255) |
| 7 | `truck` | Rojo (0, 0, 255) |
| 15 | `cat` | Blanco (255, 255, 255) |
| 16 | `dog` | Gris (128, 128, 128) |

---

## Troubleshooting

### Error: "No se pudo abrir la fuente de video"

**Solución:**
```bash
# Verificar cámaras disponibles
ls /dev/video*

# Verificar permisos
sudo usermod -a -G video $USER

# Si es archivo, verificar ruta
ls -lh /path/to/video.mp4
```

### Error: "Modelo TFLite no encontrado"

**Solución:**
```bash
# Verificar que el modelo existe
ls -lh traffic-monitor/models/detect.tflite

# Si no existe, descargarlo (ver sección Instalación)
```

### Error: "FFmpeg: h264_omx not found"

**Solución en desarrollo (PC):**
```python
# En config.py, cambiar:
USE_GPU_ENCODING = False  # Usar libx264 en lugar de h264_omx
```

**Solución en Raspberry Pi:**
```bash
# Verificar que FFmpeg tiene soporte OMX
ffmpeg -encoders | grep h264_omx

# Si no está, recompilar FFmpeg o usar imagen Yocto correcta
```

### FPS muy bajo (< 10)

**Soluciones:**
1. Reducir resolución en `config.py`: `FRAME_WIDTH = 320, FRAME_HEIGHT = 240`
2. Aumentar threshold de confianza: `CONFIDENCE_THRESHOLD = 0.7`
3. Deshabilitar tracking temporalmente
4. Verificar temperatura de la Raspberry Pi: `vcgencmd measure_temp`

### Dashboard no se actualiza

**Solución:**
```bash
# Verificar que Flask está corriendo
curl http://localhost:5000/api/stats

# Verificar logs
# Buscar errores en la salida de main.py

# Verificar firewall (si aplica)
sudo ufw allow 5000
```

---

## Rendimiento Esperado

### Raspberry Pi 4 (4GB)

| Configuración | FPS | Latencia Inferencia |
|---------------|-----|---------------------|
| 640x480, MobileNet-SSD v1 (quant) | 12-15 | 150-180 ms |
| 640x480, MobileNet-SSD v2 | 10-12 | 180-220 ms |
| 320x240, MobileNet-SSD v1 (quant) | 18-22 | 120-150 ms |

### PC/Laptop (Testing)

| Configuración | FPS | Latencia Inferencia |
|---------------|-----|---------------------|
| 640x480, MobileNet-SSD v1 | 30+ | 30-50 ms |

---

## Créditos y Referencias

### Modelo de Machine Learning
- **MobileNet-SSD v2** - Google Research
- Dataset: COCO (Common Objects in Context)
- Framework: TensorFlow Lite

### Librerías Utilizadas
- **OpenCV** - Captura y procesamiento de video
- **TensorFlow Lite** - Inferencia en edge devices
- **Flask** - Servidor web
- **FFmpeg** - Streaming de video

### Documentación
- [TensorFlow Lite Guide](https://www.tensorflow.org/lite/guide)
- [OpenCV Documentation](https://docs.opencv.org/)
- [Yocto Project](https://www.yoctoproject.org/)
- [FFmpeg HLS Streaming](https://ffmpeg.org/ffmpeg-formats.html#hls)

---


## Changelog

### v1.0.0 (2025-10-23)
- Implementación inicial del sistema completo
- Pipeline F1-F7 funcional
- Dashboard web con HLS streaming
- Tracking IoU con IDs únicos
- Export de estadísticas JSON
- Documentación completa
