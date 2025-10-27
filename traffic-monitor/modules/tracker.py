"""
F5: Módulo de Tracking
Responsabilidad: Seguir objetos entre frames y asignar IDs únicos
"""
import numpy as np
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class IoUTracker:
    """
    Tracker basado en Intersection over Union (IoU).
    Asigna IDs únicos a objetos detectados y los sigue entre frames
    basándose en la superposición de sus bounding boxes.
    """

    def __init__(self, iou_threshold=0.3, max_age=30, min_hits=3):
        """
        Inicializa el tracker.
        """
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.min_hits = min_hits

        self.next_id = 1
        self.tracks = {}  # {track_id: Track}
        self.frame_count = 0

        logger.info(f"IoUTracker inicializado: iou={iou_threshold}, "
                   f"max_age={max_age}, min_hits={min_hits}")

    def update(self, detections):
        """
        Actualiza el tracker con nuevas detecciones.
        """
        self.frame_count += 1

        # Si no hay tracks existentes, crear nuevos para todas las detecciones
        if not self.tracks:
            for det in detections:
                self._create_track(det)
            return self._get_confirmed_tracks()

        # Calcular matriz de IoU entre tracks existentes y detecciones
        track_ids = list(self.tracks.keys())
        iou_matrix = np.zeros((len(track_ids), len(detections)))

        for i, track_id in enumerate(track_ids):
            track = self.tracks[track_id]
            for j, det in enumerate(detections):
                iou_matrix[i, j] = self._calculate_iou(track.bbox, det['bbox'])

        matched_tracks = set()
        matched_detections = set()
        matches = []

        while True:
            if iou_matrix.size == 0:
                break

            max_iou = np.max(iou_matrix)
            if max_iou < self.iou_threshold:
                break

            i, j = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)

            track_id = track_ids[i]
            matches.append((track_id, j))
            matched_tracks.add(track_id)
            matched_detections.add(j)

            iou_matrix[i, :] = 0
            iou_matrix[:, j] = 0

        # Actualizar tracks asociados
        for track_id, det_idx in matches:
            self.tracks[track_id].update(detections[det_idx], self.frame_count)

        # Crear nuevos tracks para detecciones no asociadas
        for j, det in enumerate(detections):
            if j not in matched_detections:
                self._create_track(det)

        # Marcar tracks no asociados como perdidos
        for track_id in track_ids:
            if track_id not in matched_tracks:
                self.tracks[track_id].mark_missed(self.frame_count)

        # Eliminar tracks antiguos
        self._cleanup_tracks()

        return self._get_confirmed_tracks()

    def _create_track(self, detection):
        """
        Crea un nuevo track.
        """
        track_id = self.next_id
        self.next_id += 1

        self.tracks[track_id] = Track(
            track_id=track_id,
            initial_detection=detection,
            frame_count=self.frame_count
        )

    def _cleanup_tracks(self):
        """
        Elimina tracks que han estado demasiado tiempo sin detección.
        """
        to_remove = []
        for track_id, track in self.tracks.items():
            if track.time_since_update > self.max_age:
                to_remove.append(track_id)

        for track_id in to_remove:
            del self.tracks[track_id]

    def _get_confirmed_tracks(self):
        """
        Retorna solo los tracks confirmados con suficientes detecciones.
        """
        confirmed = []
        for track in self.tracks.values():
            # Solo considerar confirmados si:
            # 1. Tienen suficientes hits Y están activos (detectados recientemente)
            if track.hits >= self.min_hits and track.time_since_update <= 5:
                confirmed.append({
                    'track_id': track.track_id,
                    'class': track.class_name,
                    'class_id': track.class_id,
                    'confidence': track.confidence,
                    'bbox': track.bbox
                })
        return confirmed

    @staticmethod
    def _calculate_iou(bbox1, bbox2):
        """
        Calcula Intersection over Union (IoU) entre dos bounding boxes.
        Usa distancia de centroides como métrica adicional para objetos en movimiento.
        """
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        # Calcular dimensiones de ambos boxes
        w1 = x2_1 - x1_1
        h1 = y2_1 - y1_1
        w2 = x2_2 - x1_2
        h2 = y2_2 - y1_2

        # Calcular centroides
        cx1 = (x1_1 + x2_1) / 2
        cy1 = (y1_1 + y2_1) / 2
        cx2 = (x1_2 + x2_2) / 2
        cy2 = (y1_2 + y2_2) / 2

        # Calcular área de intersección
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)

        if x2_i < x1_i or y2_i < y1_i:
            # No hay intersección, usar distancia de centroides
            diagonal_avg = (np.sqrt(w1**2 + h1**2) + np.sqrt(w2**2 + h2**2)) / 2
            distance = np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)

            # Aceptar hasta 3x la diagonal del objeto
            if distance < 3 * diagonal_avg:
                score = max(0.05, 0.3 * (1 - distance / (3 * diagonal_avg)))
                return score
            return 0.0

        intersection = (x2_i - x1_i) * (y2_i - y1_i)

        # Calcular área de unión
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection

        if union == 0:
            return 0.0

        iou = intersection / union

        # Si el IoU es bajo pero los centroides están cerca, dar bonus
        w_avg = (w1 + w2) / 2
        h_avg = (h1 + h2) / 2
        distance = np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)

        if distance < (w_avg + h_avg) / 2:
            # Centroides muy cercanos, aumentar score
            iou = max(iou, 0.15)

        return iou

    def get_statistics(self):
        """
        Retorna estadísticas del tracker.
        """
        stats = {
            'total_tracks': self.next_id - 1,
            'active_tracks': len(self.tracks),
            'tracks_by_class': defaultdict(int)
        }

        for track in self.tracks.values():
            if track.hits >= self.min_hits:
                stats['tracks_by_class'][track.class_name] += 1

        return stats

    def reset(self):
        """
        Reinicia el tracker.
        """
        self.next_id = 1
        self.tracks = {}
        self.frame_count = 0
        logger.info("Tracker reiniciado")


class Track:
    """
    Representa un objeto trackeado a lo largo de múltiples frames.
    """
    def __init__(self, track_id, initial_detection, frame_count):
        """
        Inicializa un track.
        """
        self.track_id = track_id
        self.class_name = initial_detection['class']
        self.class_id = initial_detection['class_id']
        self.confidence = initial_detection['confidence']
        self.bbox = initial_detection['bbox']
        self.hits = 1  # Número de detecciones asociadas
        self.time_since_update = 0  # Frames desde última detección
        self.last_frame = frame_count

    def update(self, detection, frame_count):
        """
        Actualiza el track con una nueva detección.
        """
        self.bbox = detection['bbox']
        self.confidence = detection['confidence']
        self.hits += 1
        self.time_since_update = 0
        self.last_frame = frame_count

    def mark_missed(self, frame_count):
        """
        Marca el track como no detectado en este frame.
        """
        self.time_since_update = frame_count - self.last_frame
