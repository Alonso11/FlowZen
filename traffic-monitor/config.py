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
TARGET_FPS = 15  # FPS objetivo para captura y streaming

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
CONFIDENCE_THRESHOLD = 0.6  # Confianza mínima para considerar detección
NMS_THRESHOLD = 0.5  # Threshold para Non-Maximum Suppression (IoU)

# =============================================================================
# F5: TRACKING
# =============================================================================
IOU_THRESHOLD = 0.1  # Threshold IoU para asociar detecciones entre frames
MAX_AGE = 40  # Frames máximos sin detección antes de eliminar track
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
HLS_SEGMENT_DURATION = 2  # Duración de cada segmento HLS en segundos (corto para reducir latencia)
HLS_LIST_SIZE = 10  # Número de segmentos en la playlist

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

# =============================================================================
# F8: CONTROL DE SEMÁFOROS INTELIGENTES
# =============================================================================
# Habilitar sistema de control de semáforos
ENABLE_TRAFFIC_LIGHTS = True

# Fuentes de video para el sistema de semáforos
# MODO PC: Ambos videos pregrabados (sin cámara)
VIDEO_SOURCE_VEHICULAR = '../Video1.mp4' # Video pregrabado para tráfico vehicular
VIDEO_SOURCE_PEDESTRIAN = '../peatones4.mp4'  # Video pregrabado para tráfico peatonal

# MODO RASPBERRY PI: Descomentar cuando esté en la Raspberry Pi
# VIDEO_SOURCE_VEHICULAR = 0  # Cámara Raspberry Pi para tráfico vehicular
# VIDEO_SOURCE_PEDESTRIAN = '../Video1.mp4'  # Video pregrabado para tráfico peatonal

# Configuración de tiempos del controlador (segundos)
MIN_GREEN_TIME = 5  # Tiempo mínimo que debe permanecer un semáforo en verde
MAX_GREEN_TIME = 20  # Tiempo máximo que puede permanecer un semáforo en verde
YELLOW_TIME = 2  # Duración del semáforo amarillo
HIGH_TRAFFIC_THRESHOLD = 5  # Número de objetos para considerar alto tráfico
CONGESTION_TIME_THRESHOLD = 15  # Tiempo para considerar congestión prolongada (segundos)
NO_TRAFFIC_WAIT_TIME = 10  # Tiempo de espera sin tráfico antes de cambiar (segundos)

# Rutas de imágenes de semáforos
TRAFFIC_LIGHT_IMAGES = {
    'vehicular_verde': os.path.join(PROJECT_ROOT, 'images', 'vehicular_verde.png'),
    'vehicular_amarillo': os.path.join(PROJECT_ROOT, 'images', 'vehicular_amarillo.png'),
    'vehicular_rojo': os.path.join(PROJECT_ROOT, 'images', 'vehicular_rojo.png'),
    'peatonal_verde': os.path.join(PROJECT_ROOT, 'images', 'peatonal_verde.png'),
    'peatonal_rojo': os.path.join(PROJECT_ROOT, 'images', 'peatonal_rojo.png')
}

# Clases consideradas como vehículos
VEHICLE_CLASSES = ['car', 'motorcycle', 'bus', 'truck', 'bicycle']

# Clases consideradas como peatones
PEDESTRIAN_CLASSES = ['person']
