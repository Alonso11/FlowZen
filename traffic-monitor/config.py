"""
Configuración del Sistema de Monitoreo de Tránsito
"""
import os

# =============================================================================
# CONFIGURACIÓN GENERAL
# =============================================================================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'results')
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')

# Crear directorios si no existen
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# =============================================================================
# F1: CAPTURA DE VIDEO
# =============================================================================
# Fuente de video: 0 para cámara, o ruta a archivo MP4
VIDEO_SOURCE = 0  # Por defecto usa cámara
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 15  # FPS objetivo para captura

# =============================================================================
# F2: PREPROCESAMIENTO
# =============================================================================
MODEL_INPUT_SIZE = (300, 300)  # Tamaño de entrada para MobileNet-SSD v2
NORMALIZE = False  # NO normalizar - el modelo cuantizado espera UINT8 [0-255]

# =============================================================================
# F3: INFERENCIA TFLITE
# =============================================================================
MODEL_PATH = os.path.join(MODELS_DIR, 'detect.tflite')
LABELS_PATH = os.path.join(MODELS_DIR, 'labelmap.txt')

# Clases COCO relevantes 
RELEVANT_CLASSES = {
    0: 'person',
    1: 'bicycle',
    2: 'car',
    3: 'motorcycle',
    5: 'bus',
    7: 'truck',
    15: 'cat',
    16: 'dog'
}

# Número de threads para inferencia
NUM_THREADS = 4

# =============================================================================
# F4: POST-PROCESAMIENTO
# =============================================================================
CONFIDENCE_THRESHOLD = 0.5  # Confianza mínima para considerar detección
NMS_THRESHOLD = 0.5  # Threshold para Non-Maximum Suppression (IoU)

# =============================================================================
# F5: TRACKING
# =============================================================================
IOU_THRESHOLD = 0.3  # Threshold IoU para asociar detecciones entre frames
MAX_AGE = 30  # Frames máximos sin detección antes de eliminar track
MIN_HITS = 3  # Detecciones mínimas para considerar track válido

# =============================================================================
# F6: ALMACENAMIENTO
# =============================================================================
SAVE_STATS_ON_EXIT = True
STATS_FILENAME_PREFIX = 'stats'

# =============================================================================
# F7: STREAMING FFMPEG
# =============================================================================
ENABLE_STREAMING = True
STREAM_DIR = '/tmp'  # Directorio para archivos HLS
HLS_SEGMENT_DURATION = 2  # Duración de cada segmento HLS en segundos
HLS_LIST_SIZE = 5  # Número de segmentos en la playlist

# Configuración de codec
USE_GPU_ENCODING = False  # False para PC (libx264), True para Raspberry Pi (h264_omx)
VIDEO_BITRATE = '1500k'  # Bitrate del stream

# =============================================================================
# SERVIDOR WEB (FLASK)
# =============================================================================
FLASK_HOST = '0.0.0.0'  # Accesible desde toda la red
FLASK_PORT = 5000
FLASK_DEBUG = False

# =============================================================================
# VISUALIZACIÓN
# =============================================================================
DRAW_BBOXES = True  # Dibujar bounding boxes en frames
BBOX_THICKNESS = 2
FONT_SCALE = 0.6
FONT_THICKNESS = 2

# Colores para cada clase (BGR)
CLASS_COLORS = {
    'person': (0, 255, 0),      # Verde
    'bicycle': (255, 255, 0),   # Cyan
    'car': (255, 0, 0),         # Azul
    'motorcycle': (255, 0, 255),# Magenta
    'bus': (0, 165, 255),       # Naranja
    'truck': (0, 0, 255),       # Rojo
    'cat': (255, 255, 255),     # Blanco
    'dog': (128, 128, 128)      # Gris
}

# =============================================================================
# LOGGING
# =============================================================================
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
PRINT_FPS = True  # Mostrar FPS en consola
FPS_UPDATE_INTERVAL = 1.0  # Segundos entre actualizaciones de FPS
