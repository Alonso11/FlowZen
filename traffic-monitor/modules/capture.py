"""
F1: Módulo de Captura de Video
Responsabilidad: Obtener frames de la cámara o video pregrabado
"""
import cv2
import time
import logging

logger = logging.getLogger(__name__)


class VideoCapture:
    """
    Captura frames desde cámara o archivo de video.
    """

    def __init__(self, source=0, width=640, height=480, fps=15):
        """
        Inicializa el capturador de video.
        """
        self.source = source
        self.width = width
        self.height = height
        self.target_fps = fps
        self.cap = None
        self.is_camera = isinstance(source, int)
        self.frame_count = 0
        self.start_time = None

    def open(self):
        """
        Abre la fuente de video.
        """
        try:
            self.cap = cv2.VideoCapture(self.source)

            if not self.cap.isOpened():
                logger.error(f"No se pudo abrir la fuente de video: {self.source}")
                return False

            # Configurar resolución si es cámara
            if self.is_camera:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)

            # Verificar resolución real
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

            source_type = "cámara" if self.is_camera else "archivo"
            logger.info(f"Fuente de video abierta ({source_type}): {self.source}")
            logger.info(f"Resolución: {actual_width}x{actual_height}")
            logger.info(f"FPS: {actual_fps}")

            self.start_time = time.time()
            self.frame_count = 0

            return True

        except Exception as e:
            logger.error(f"Error al abrir fuente de video: {e}")
            return False

    def read(self):
        """
        Lee el siguiente frame.
        """
        if self.cap is None or not self.cap.isOpened():
            return False, None

        ret, frame = self.cap.read()

        # Si es un archivo y llegó al final, reiniciar (loop infinito)
        if not ret and not self.is_camera:
            logger.info("Video terminado, reiniciando desde el inicio (loop)")
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()

        if ret:
            self.frame_count += 1
            # Redimensionar si es necesario
            if frame.shape[1] != self.width or frame.shape[0] != self.height:
                frame = cv2.resize(frame, (self.width, self.height))

        return ret, frame

    def get_fps(self):
        """
        Calcula el FPS real de captura.
        """
        if self.start_time is None or self.frame_count == 0:
            return 0.0

        elapsed = time.time() - self.start_time
        return self.frame_count / elapsed if elapsed > 0 else 0.0

    def get_frame_count(self):
        """
        Retorna el número de frames procesados.
        """
        return self.frame_count

    def get_elapsed_time(self):
        """
        Retorna el tiempo transcurrido desde el inicio.
        """
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def release(self):
        """
        Libera los recursos del capturador.
        """
        if self.cap is not None:
            self.cap.release()
            logger.info(f"Fuente de video liberada. Frames procesados: {self.frame_count}")
            self.cap = None

    def __enter__(self):
        """
        Context manager: entrada.
        """
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager: salida.
        """
        self.release()
        return False
