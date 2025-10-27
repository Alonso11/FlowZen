"""
Módulo F8: Controlador Inteligente de Semáforos
Responsabilidad: Gestionar la lógica de control de semáforos basada en detecciones
"""
import logging
import time
from enum import Enum

logger = logging.getLogger(__name__)


class TrafficLightState(Enum):
    """Estados posibles de los semáforos"""
    VEHICULAR_GREEN = "vehicular_verde"
    VEHICULAR_YELLOW = "vehicular_amarillo"
    VEHICULAR_RED = "vehicular_rojo"
    PEDESTRIAN_GREEN = "peatonal_verde"
    PEDESTRIAN_RED = "peatonal_rojo"


class TrafficLightController:
    """
    Controlador inteligente de semáforos que gestiona estados basándose en:
    - Conteo de vehículos
    - Conteo de peatones
    - Tiempo en cada estado
    - Reglas de priorización
    """

    def __init__(self,
                 min_green_time=10,
                 max_green_time=60,
                 yellow_time=3,
                 high_traffic_threshold=5,
                 congestion_time_threshold=45,
                 no_traffic_wait_time=15):
        """
        Inicializa el controlador de semáforos.

        Args:
            min_green_time: Tiempo mínimo en verde (segundos)
            max_green_time: Tiempo máximo en verde (segundos)
            yellow_time: Duración del amarillo (segundos)
            high_traffic_threshold: Umbral para considerar alto tráfico
            congestion_time_threshold: Tiempo para considerar congestión prolongada
            no_traffic_wait_time: Tiempo de espera sin tráfico antes de cambiar
        """
        self.min_green_time = min_green_time
        self.max_green_time = max_green_time
        self.yellow_time = yellow_time
        self.high_traffic_threshold = high_traffic_threshold
        self.congestion_time_threshold = congestion_time_threshold
        self.no_traffic_wait_time = no_traffic_wait_time

        # Estado actual del sistema
        self.vehicular_state = TrafficLightState.VEHICULAR_GREEN
        self.pedestrian_state = TrafficLightState.PEDESTRIAN_RED

        # Contadores de tiempo
        self.state_start_time = time.time()
        self.yellow_start_time = None
        self.in_transition = False

        # Contadores de tráfico actuales
        self.vehicle_count = 0
        self.pedestrian_count = 0

        # Histórico de cambios
        self.state_history = []

        logger.info("Controlador de semáforos inicializado")
        logger.info(f"Configuración: min_green={min_green_time}s, max_green={max_green_time}s, "
                   f"yellow={yellow_time}s, threshold={high_traffic_threshold}")

    def update_traffic_counts(self, vehicle_count, pedestrian_count):
        """
        Actualiza los conteos de tráfico desde los detectores.

        Args:
            vehicle_count: Número de vehículos detectados actualmente
            pedestrian_count: Número de peatones detectados actualmente
        """
        self.vehicle_count = vehicle_count
        self.pedestrian_count = pedestrian_count

    def get_time_in_current_state(self):
        """Retorna el tiempo transcurrido en el estado actual (segundos)"""
        return time.time() - self.state_start_time

    def is_vehicular_green(self):
        """Retorna True si el semáforo vehicular está en verde"""
        return self.vehicular_state == TrafficLightState.VEHICULAR_GREEN

    def is_pedestrian_green(self):
        """Retorna True si el semáforo peatonal está en verde"""
        return self.pedestrian_state == TrafficLightState.PEDESTRIAN_GREEN

    def _change_to_vehicular_green(self):
        """Cambia a semáforo vehicular en verde, peatonal en rojo"""
        self.vehicular_state = TrafficLightState.VEHICULAR_GREEN
        self.pedestrian_state = TrafficLightState.PEDESTRIAN_RED
        self.state_start_time = time.time()
        self.in_transition = False

        self.state_history.append({
            'timestamp': time.time(),
            'state': 'vehicular_green',
            'vehicle_count': self.vehicle_count,
            'pedestrian_count': self.pedestrian_count
        })

        logger.info(f"🚗 CAMBIO: Vehicular VERDE | Peatonal ROJO "
                   f"(Vehículos: {self.vehicle_count}, Peatones: {self.pedestrian_count})")

    def _change_to_pedestrian_green(self):
        """Cambia a semáforo peatonal en verde, vehicular en rojo"""
        self.vehicular_state = TrafficLightState.VEHICULAR_RED
        self.pedestrian_state = TrafficLightState.PEDESTRIAN_GREEN
        self.state_start_time = time.time()
        self.in_transition = False

        self.state_history.append({
            'timestamp': time.time(),
            'state': 'pedestrian_green',
            'vehicle_count': self.vehicle_count,
            'pedestrian_count': self.pedestrian_count
        })

        logger.info(f"🚶 CAMBIO: Vehicular ROJO | Peatonal VERDE "
                   f"(Vehículos: {self.vehicle_count}, Peatones: {self.pedestrian_count})")

    def _start_yellow_transition(self):
        """Inicia la transición de amarillo antes de cambiar a rojo"""
        if self.vehicular_state == TrafficLightState.VEHICULAR_GREEN:
            self.vehicular_state = TrafficLightState.VEHICULAR_YELLOW
            self.yellow_start_time = time.time()
            self.in_transition = True
            logger.info("⚠️  TRANSICIÓN: Vehicular AMARILLO")

    def _should_prioritize_vehicles(self):
        """
        Escenario 1: Prioridad vehicular por congestión peatonal prolongada
        Si hay alto tráfico vehicular y el semáforo peatonal lleva mucho tiempo en verde
        """
        if not self.is_pedestrian_green():
            return False

        time_in_state = self.get_time_in_current_state()
        has_high_vehicle_traffic = self.vehicle_count >= self.high_traffic_threshold
        pedestrian_congestion = time_in_state >= self.congestion_time_threshold

        return has_high_vehicle_traffic and pedestrian_congestion

    def _should_prioritize_pedestrians(self):
        """
        Escenario 2: Prioridad peatonal por acumulación de espera
        Si hay muchos peatones esperando y el vehicular lleva mucho tiempo en verde
        """
        if not self.is_vehicular_green():
            return False

        time_in_state = self.get_time_in_current_state()
        has_high_pedestrian_traffic = self.pedestrian_count >= self.high_traffic_threshold
        vehicular_congestion = time_in_state >= self.congestion_time_threshold

        return has_high_pedestrian_traffic and vehicular_congestion

    def _should_optimize_no_vehicles(self):
        """
        Escenario 3: Optimización sin tráfico vehicular
        Si no hay vehículos, vehicular está en verde, hay peatones esperando y peatonal está en rojo
        """
        no_vehicles = self.vehicle_count == 0
        has_waiting_pedestrians = self.pedestrian_count > 0
        vehicular_is_green = self.is_vehicular_green()
        time_in_state = self.get_time_in_current_state()
        waited_enough = time_in_state >= self.no_traffic_wait_time

        return no_vehicles and has_waiting_pedestrians and vehicular_is_green and waited_enough

    def _should_optimize_no_pedestrians(self):
        """
        Escenario 4: Optimización sin tráfico peatonal
        Si no hay peatones, vehicular está en rojo y hay vehículos esperando
        """
        no_pedestrians = self.pedestrian_count == 0
        has_waiting_vehicles = self.vehicle_count > 0
        pedestrian_is_green = self.is_pedestrian_green()
        time_in_state = self.get_time_in_current_state()
        waited_enough = time_in_state >= self.no_traffic_wait_time

        return no_pedestrians and has_waiting_vehicles and pedestrian_is_green and waited_enough

    def _has_exceeded_max_time(self):
        """Verifica si se ha excedido el tiempo máximo en el estado actual"""
        return self.get_time_in_current_state() >= self.max_green_time

    def _has_met_min_time(self):
        """Verifica si se ha cumplido el tiempo mínimo en el estado actual"""
        return self.get_time_in_current_state() >= self.min_green_time

    def update(self):
        """
        Actualiza el estado del controlador basándose en las reglas de priorización.
        Debe llamarse periódicamente (ej. cada frame o cada segundo).

        Returns:
            dict: Estado actual del sistema con información de los semáforos
        """
        # Si estamos en transición amarilla, verificar si terminó
        if self.in_transition and self.vehicular_state == TrafficLightState.VEHICULAR_YELLOW:
            yellow_elapsed = time.time() - self.yellow_start_time
            if yellow_elapsed >= self.yellow_time:
                # Completar transición a peatonal verde
                self._change_to_pedestrian_green()
                return self.get_state()

        # No hacer cambios si no se ha cumplido el tiempo mínimo
        if not self._has_met_min_time() and not self.in_transition:
            return self.get_state()

        # Aplicar reglas de priorización en orden

        # Regla 1: Priorizar vehículos si peatones llevan mucho tiempo
        if self._should_prioritize_vehicles():
            logger.info("📊 Aplicando Regla 1: Prioridad vehicular por congestión peatonal prolongada")
            self._change_to_vehicular_green()
            return self.get_state()

        # Regla 2: Priorizar peatones si vehículos llevan mucho tiempo
        if self._should_prioritize_pedestrians():
            logger.info("📊 Aplicando Regla 2: Prioridad peatonal por acumulación de espera")
            self._start_yellow_transition()
            return self.get_state()

        # Regla 3: Optimizar cuando no hay vehículos
        if self._should_optimize_no_vehicles():
            logger.info("📊 Aplicando Regla 3: Optimización sin tráfico vehicular")
            self._start_yellow_transition()
            return self.get_state()

        # Regla 4: Optimizar cuando no hay peatones
        if self._should_optimize_no_pedestrians():
            logger.info("📊 Aplicando Regla 4: Optimización sin tráfico peatonal")
            self._change_to_vehicular_green()
            return self.get_state()

        # Forzar cambio si se excedió el tiempo máximo
        if self._has_exceeded_max_time() and not self.in_transition:
            logger.info("⏰ Tiempo máximo excedido, forzando cambio de estado")
            if self.is_vehicular_green():
                self._start_yellow_transition()
            else:
                self._change_to_vehicular_green()

        return self.get_state()

    def get_state(self):
        """
        Retorna el estado actual del sistema de semáforos.

        Returns:
            dict: Información completa del estado actual
        """
        return {
            'vehicular_state': self.vehicular_state.value,
            'pedestrian_state': self.pedestrian_state.value,
            'vehicle_count': self.vehicle_count,
            'pedestrian_count': self.pedestrian_count,
            'time_in_state': self.get_time_in_current_state(),
            'in_transition': self.in_transition,
            'vehicular_is_green': self.is_vehicular_green(),
            'pedestrian_is_green': self.is_pedestrian_green()
        }

    def get_statistics(self):
        """
        Retorna estadísticas del controlador.

        Returns:
            dict: Estadísticas de cambios de estado
        """
        return {
            'total_state_changes': len(self.state_history),
            'state_history': self.state_history[-10:],  # Últimos 10 cambios
            'current_state': self.get_state()
        }

    def reset(self):
        """Reinicia el controlador al estado inicial"""
        self.vehicular_state = TrafficLightState.VEHICULAR_GREEN
        self.pedestrian_state = TrafficLightState.PEDESTRIAN_RED
        self.state_start_time = time.time()
        self.yellow_start_time = None
        self.in_transition = False
        self.vehicle_count = 0
        self.pedestrian_count = 0
        self.state_history = []
        logger.info("Controlador reiniciado al estado inicial")
