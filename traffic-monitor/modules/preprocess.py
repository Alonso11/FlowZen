"""
F2: Módulo de Preprocesamiento
Responsabilidad: Adaptar frames al formato requerido por el modelo TFLite
"""
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


class Preprocessor:
    """
    Preprocesa frames para inferencia con TensorFlow Lite.
    """

    def __init__(self, input_size=(300, 300), normalize=True):
        """
        Inicializa el preprocesador.
        """
        self.input_size = input_size
        self.normalize = normalize
        logger.info(f"Preprocesador inicializado: input_size={input_size}, normalize={normalize}")

    def process(self, frame):
        """
        Preprocesa un frame para inferencia.
        """
        if frame is None or frame.size == 0:
            logger.warning("Frame vacío recibido en preprocesador")
            return None

        try:
            # 1. Redimensionar a tamaño de entrada del modelo
            resized = cv2.resize(frame, self.input_size)

            # 2. Convertir BGR a RGB
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

            # 3. Normalizar si es necesario
            if self.normalize:
                processed = rgb_frame.astype(np.float32) / 255.0
            else:
                processed = rgb_frame.astype(np.uint8)

            # 4. Agregar dimensión batch
            input_tensor = np.expand_dims(processed, axis=0)

            return input_tensor

        except Exception as e:
            logger.error(f"Error en preprocesamiento: {e}")
            return None

    def process_batch(self, frames):
        """
        Preprocesa un batch de frames.
        """
        processed_frames = []

        for frame in frames:
            tensor = self.process(frame)
            if tensor is not None:
                processed_frames.append(tensor[0])

        if not processed_frames:
            return None

        return np.stack(processed_frames, axis=0)

    def get_output_shape(self):
        """
        Retorna el shape del tensor de salida.
        """
        return (1, self.input_size[1], self.input_size[0], 3)
