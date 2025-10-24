"""
F4: Módulo de Post-procesamiento
Responsabilidad: Convertir salidas crudas del modelo en detecciones útiles
"""
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


class PostProcessor:
    """
    Post-procesa las salidas del modelo TFLite.
    """
    def __init__(self, conf_threshold=0.5, nms_threshold=0.5,
                 frame_width=640, frame_height=480, class_map=None):
        """
        Inicializa el post-procesador.
        """
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.class_map = class_map or {}

        logger.info(f"PostProcessor inicializado: conf={conf_threshold}, "
                   f"nms={nms_threshold}, size=({frame_width}x{frame_height})")

    def process(self, detection_results):
        """
        Post-procesa resultados de detección.
        """
        if detection_results is None:
            return []

        boxes = detection_results['boxes']
        classes = detection_results['classes']
        scores = detection_results['scores']
        count = detection_results['count']

        detections = []

        # 1. Filtrar por confianza y clases relevantes
        for i in range(count):
            score = scores[i]
            class_id = int(classes[i])

            if score < self.conf_threshold:
                continue

            if class_id not in self.class_map:
                continue

            y1, x1, y2, x2 = boxes[i]
            x1_px = int(x1 * self.frame_width)
            y1_px = int(y1 * self.frame_height)
            x2_px = int(x2 * self.frame_width)
            y2_px = int(y2 * self.frame_height)

            x1_px = max(0, min(x1_px, self.frame_width))
            y1_px = max(0, min(y1_px, self.frame_height))
            x2_px = max(0, min(x2_px, self.frame_width))
            y2_px = max(0, min(y2_px, self.frame_height))

            detections.append({
                'class': self.class_map[class_id],
                'class_id': class_id,
                'confidence': float(score),
                'bbox': [x1_px, y1_px, x2_px, y2_px]
            })

        # 2. Aplicar Non-Maximum Suppression
        if len(detections) > 1:
            detections = self._apply_nms(detections)

        return detections

    def _apply_nms(self, detections):
        """
        Aplica Non-Maximum Suppression para eliminar detecciones duplicadas.
        """
        if len(detections) == 0:
            return []

        # Preparar datos para cv2.dnn.NMSBoxes
        boxes = []
        scores = []
        class_ids = []

        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            boxes.append([x1, y1, x2 - x1, y2 - y1])  
            scores.append(det['confidence'])
            class_ids.append(det['class_id'])

        # Aplicar NMS
        indices = cv2.dnn.NMSBoxes(
            boxes,
            scores,
            self.conf_threshold,
            self.nms_threshold
        )

        # Filtrar detecciones
        filtered_detections = []
        if len(indices) > 0:
            if isinstance(indices, tuple):
                indices = indices[0]

            for i in indices.flatten():
                filtered_detections.append(detections[i])

        return filtered_detections

    def draw_detections(self, frame, detections, colors=None):
        """
        Dibuja bounding boxes y labels en el frame.
        """
        frame_copy = frame.copy()

        for det in detections:
            class_name = det['class']
            confidence = det['confidence']
            x1, y1, x2, y2 = det['bbox']

            # Color de la clase
            if colors and class_name in colors:
                color = colors[class_name]
            else:
                color = (0, 255, 0)  

            # Dibujar bounding box
            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), color, 2)

            # Dibujar label
            label = f"{class_name}: {confidence:.2f}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            label_w, label_h = label_size

            # Fondo para el texto
            cv2.rectangle(
                frame_copy,
                (x1, y1 - label_h - 10),
                (x1 + label_w, y1),
                color,
                -1
            )

            # Texto
            cv2.putText(
                frame_copy,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1
            )

        return frame_copy

    def update_frame_size(self, width, height):
        """
        Actualiza el tamaño del frame para conversión de coordenadas.
        """
        self.frame_width = width
        self.frame_height = height
        logger.info(f"Tamaño de frame actualizado: {width}x{height}")
