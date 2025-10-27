"""
F6: Módulo de Almacenamiento
Responsabilidad: Generar estadísticas al finalizar la ejecución
"""
import json
import logging
from datetime import datetime
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


class StatsCollector:
    """
    Recolecta estadísticas en RAM durante la ejecución y genera
    un archivo JSON al finalizar.
    """

    def __init__(self, results_dir='results'):
        """
        Inicializa el recolector de estadísticas.
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        self.start_time = None
        self.end_time = None
        # Contadores
        self.detections_count = defaultdict(int)  # {class_name: count}
        self.unique_tracks = defaultdict(set)  # {class_name: {track_ids}}
        self.frames_processed = 0
        self.total_inference_time = 0.0  # ms
        # Métricas de rendimiento
        self.fps_history = []

        # Estadísticas de semáforos
        self.traffic_light_state_history = []
        self.current_traffic_light_state = None

        logger.info(f"StatsCollector inicializado: results_dir={results_dir}")

    def start_session(self):
        """
        Inicia una nueva sesión de recolección.
        """
        self.start_time = datetime.now()
        self.detections_count.clear()
        self.unique_tracks.clear()
        self.frames_processed = 0
        self.total_inference_time = 0.0
        self.fps_history.clear()

        logger.info(f"Sesión iniciada: {self.start_time.isoformat()}")

    def update(self, tracked_objects, inference_time=0.0):
        """
        Actualiza estadísticas con los objetos del frame actual.
        """
        self.frames_processed += 1
        self.total_inference_time += inference_time

        for obj in tracked_objects:
            class_name = obj['class']
            track_id = obj['track_id']

            # Contar detección
            self.detections_count[class_name] += 1

            # Registrar track único
            self.unique_tracks[class_name].add(track_id)

    def update_fps(self, fps):
        """
        Registra una medición de FPS.
        """
        self.fps_history.append(fps)

    def update_traffic_light_state(self, state_info):
        """
        Actualiza el estado actual del sistema de semáforos.

        Args:
            state_info: dict con información del estado de los semáforos
        """
        self.current_traffic_light_state = state_info

        # Registrar cambios de estado significativos en el historial
        if state_info.get('state_changed', False):
            self.traffic_light_state_history.append({
                'timestamp': datetime.now().isoformat(),
                'vehicular_state': state_info.get('vehicular_state'),
                'pedestrian_state': state_info.get('pedestrian_state'),
                'vehicle_count': state_info.get('vehicle_count', 0),
                'pedestrian_count': state_info.get('pedestrian_count', 0)
            })

    def get_current_stats(self):
        """
        Retorna estadísticas actuales (para API en tiempo real).
        """
        duration = 0
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()

        current_fps = 0
        if self.fps_history:
            current_fps = self.fps_history[-1]

        avg_fps = 0
        if self.fps_history:
            avg_fps = sum(self.fps_history) / len(self.fps_history)

        avg_inference = 0
        if self.frames_processed > 0:
            avg_inference = self.total_inference_time / self.frames_processed

        stats = {
            'detections': dict(self.detections_count),
            'unique_objects': {
                class_name: len(track_ids)
                for class_name, track_ids in self.unique_tracks.items()
            },
            'performance': {
                'fps': round(current_fps, 2),
                'avg_fps': round(avg_fps, 2),
                'elapsed_time': self._format_duration(duration),
                'elapsed_seconds': int(duration),
                'frames_processed': self.frames_processed,
                'avg_inference_ms': round(avg_inference, 2)
            }
        }

        # Agregar información del sistema de semáforos si está disponible
        if self.current_traffic_light_state:
            stats['traffic_lights'] = self.current_traffic_light_state

        return stats

    def save_stats(self, filename_prefix='stats'):
        """
        Guarda las estadísticas en un archivo JSON.
        """
        self.end_time = datetime.now()

        if self.start_time is None:
            logger.warning("No se puede guardar estadísticas: sesión no iniciada")
            return None

        duration = (self.end_time - self.start_time).total_seconds()

        avg_fps = 0
        if self.fps_history:
            avg_fps = sum(self.fps_history) / len(self.fps_history)

        avg_inference = 0
        if self.frames_processed > 0:
            avg_inference = self.total_inference_time / self.frames_processed

        stats = {
            'session_info': {
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat(),
                'duration_seconds': int(duration),
                'duration_formatted': self._format_duration(duration),
                'frames_processed': self.frames_processed
            },
            'detections': {
                'total_by_class': dict(self.detections_count),
                'unique_objects_by_class': {
                    class_name: len(track_ids)
                    for class_name, track_ids in self.unique_tracks.items()
                }
            },
            'performance': {
                'average_fps': round(avg_fps, 2),
                'min_fps': round(min(self.fps_history), 2) if self.fps_history else 0,
                'max_fps': round(max(self.fps_history), 2) if self.fps_history else 0,
                'average_inference_ms': round(avg_inference, 2),
                'total_inference_time_seconds': round(self.total_inference_time / 1000, 2)
            },
            'summary': {
                'total_detections': sum(self.detections_count.values()),
                'total_unique_objects': sum(len(tracks) for tracks in self.unique_tracks.values()),
                'classes_detected': list(self.detections_count.keys())
            }
        }

        # Agregar historial de estados de semáforos si existe
        if self.traffic_light_state_history:
            stats['traffic_lights'] = {
                'total_state_changes': len(self.traffic_light_state_history),
                'state_history': self.traffic_light_state_history
            }

        timestamp = self.start_time.strftime('%Y%m%d_%H%M%S')
        filename = f"{filename_prefix}_{timestamp}.json"
        filepath = self.results_dir / filename

        # Guardar JSON
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)

            logger.info(f"Estadísticas guardadas: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error al guardar estadísticas: {e}")
            return None

    @staticmethod
    def _format_duration(seconds):
        """
        Formatea duración en formato legible.
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def reset(self):
        """
        Reinicia todas las estadísticas.
        """
        self.start_time = None
        self.end_time = None
        self.detections_count.clear()
        self.unique_tracks.clear()
        self.frames_processed = 0
        self.total_inference_time = 0.0
        self.fps_history.clear()
        self.traffic_light_state_history.clear()
        self.current_traffic_light_state = None
        logger.info("Estadísticas reiniciadas")
