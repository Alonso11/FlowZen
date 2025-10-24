"""
F3: Módulo de Inferencia TFLite
Responsabilidad: Ejecutar el modelo de ML para detectar objetos
"""
import numpy as np
import logging
import time

logger = logging.getLogger(__name__)


class TFLiteDetector:
    """
    Ejecuta inferencia con modelo TensorFlow Lite (MobileNet-SSD v2).
    """
    def __init__(self, model_path, num_threads=4):
        """
        Inicializa el detector TFLite.
        """
        self.model_path = model_path
        self.num_threads = num_threads
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.inference_time = 0.0

    def load(self):
        """
        Carga el modelo TFLite.
        """
        try:
            # Importar TFLite runtime
            try:
                import tflite_runtime.interpreter as tflite
            except ImportError:
                logger.warning("tflite_runtime no encontrado, usando tensorflow.lite")
                import tensorflow as tf
                tflite = tf.lite

            # Cargar modelo
            self.interpreter = tflite.Interpreter(
                model_path=self.model_path,
                num_threads=self.num_threads
            )
            self.interpreter.allocate_tensors()

            # Obtener detalles de entrada/salida
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()

            logger.info(f"Modelo TFLite cargado: {self.model_path}")
            logger.info(f"Input shape: {self.input_details[0]['shape']}")
            logger.info(f"Output tensors: {len(self.output_details)}")
            logger.info(f"Threads: {self.num_threads}")

            return True

        except Exception as e:
            logger.error(f"Error al cargar modelo TFLite: {e}")
            return False

    def detect(self, input_tensor):
        """
        Ejecuta detección en un frame preprocesado.
        """
        if self.interpreter is None:
            logger.error("Modelo no cargado. Llame a load() primero.")
            return None

        try:
            start_time = time.time()

            # Configurar tensor de entrada
            self.interpreter.set_tensor(
                self.input_details[0]['index'],
                input_tensor
            )
            # Ejecutar inferencia
            self.interpreter.invoke()
            boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]  # (N, 4)
            classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]  # (N,)
            scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]  # (N,)
            count = int(self.interpreter.get_tensor(self.output_details[3]['index'])[0])  # scalar

            self.inference_time = (time.time() - start_time) * 1000  # ms

            return {
                'boxes': boxes,
                'classes': classes.astype(int),
                'scores': scores,
                'count': count,
                'inference_time': self.inference_time
            }

        except Exception as e:
            logger.error(f"Error durante inferencia: {e}")
            return None

    def get_inference_time(self):
        """
        Retorna el tiempo de la última inferencia.
        """
        return self.inference_time

    def get_input_shape(self):
        """
        Retorna el shape esperado del input.
        """
        if self.input_details:
            return tuple(self.input_details[0]['shape'])
        return None

    def cleanup(self):
        """
        Libera recursos del modelo.
        """
        if self.interpreter is not None:
            logger.info("Liberando recursos del modelo TFLite")
            self.interpreter = None
            self.input_details = None
            self.output_details = None
