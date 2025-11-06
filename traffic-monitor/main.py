#!/usr/bin/env python3
"""
Sistema de Monitoreo Inteligente de Tránsito - Integra todos los módulos del pipeline
"""
import argparse
import logging
import signal
import sys
import time
import threading
from pathlib import Path
import config
from modules import (
    VideoCapture,
    Preprocessor,
    TFLiteDetector,
    PostProcessor,
    IoUTracker,
    StatsCollector,
    FFmpegStreamer,
    TrafficLightController
)

import web_app

# Configurar logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TrafficMonitorSystem:
    """
    Sistema principal que orquesta todos los componentes del pipeline.
    """

    def __init__(self, video_source=0, enable_streaming=True, enable_traffic_lights=False):
        """
        Inicializa el sistema.
        """
        self.video_source = video_source
        self.enable_streaming = enable_streaming
        self.enable_traffic_lights = enable_traffic_lights
        self.running = False

        # Componentes del pipeline principal (tráfico vehicular)
        self.video_capture_vehicular = None
        self.preprocessor = None
        self.detector = None
        self.postprocessor = None
        self.tracker_vehicular = None
        self.stats_collector = None
        self.streamer = None
        self.streamer_vehicular = None  # Streamer para video vehicular
        self.streamer_pedestrian = None  # Streamer para video peatonal

        # Componentes adicionales para tráfico peatonal (modo semáforos)
        self.video_capture_pedestrian = None
        self.tracker_pedestrian = None
        self.traffic_light_controller = None

        # Thread del servidor web
        self.web_thread = None

        logger.info("="*60)
        logger.info("Sistema de Monitoreo Inteligente de Tránsito")
        if enable_traffic_lights:
            logger.info("MODO: Control Inteligente de Semáforos")
        logger.info("="*60)

    def initialize(self):
        """
        Inicializa todos los componentes del sistema.
        """
        logger.info("Inicializando componentes...")

        try:
            # Determinar fuente de video según el modo
            if self.enable_traffic_lights:
                # Modo semáforos: dos fuentes de video
                video_source_vehicular = config.VIDEO_SOURCE_VEHICULAR
                video_source_pedestrian = config.VIDEO_SOURCE_PEDESTRIAN
                logger.info(f"Modo semáforos: Vehicular={video_source_vehicular}, Peatonal={video_source_pedestrian}")
            else:
                # Modo simple: una fuente de video
                video_source_vehicular = self.video_source
                logger.info(f"Modo simple: Video={video_source_vehicular}")

            # F1: Captura de video vehicular
            self.video_capture_vehicular = VideoCapture(
                source=video_source_vehicular,
                width=config.FRAME_WIDTH,
                height=config.FRAME_HEIGHT,
                fps=config.TARGET_FPS
            )
            if not self.video_capture_vehicular.open():
                logger.error("Error al abrir fuente de video vehicular")
                return False

            # F1b: Captura de video peatonal (solo en modo semáforos)
            if self.enable_traffic_lights:
                self.video_capture_pedestrian = VideoCapture(
                    source=video_source_pedestrian,
                    width=config.FRAME_WIDTH,
                    height=config.FRAME_HEIGHT,
                    fps=config.TARGET_FPS
                )
                if not self.video_capture_pedestrian.open():
                    logger.error("Error al abrir fuente de video peatonal")
                    return False

            # F2: Preprocesamiento
            self.preprocessor = Preprocessor(
                input_size=config.MODEL_INPUT_SIZE,
                normalize=config.NORMALIZE
            )

            # F3: Inferencia TFLite
            self.detector = TFLiteDetector(
                model_path=config.MODEL_PATH,
                num_threads=config.NUM_THREADS
            )
            if not self.detector.load():
                logger.error("Error al cargar modelo TFLite")
                return False

            # F4: Post-procesamiento
            self.postprocessor = PostProcessor(
                conf_threshold=config.CONFIDENCE_THRESHOLD,
                nms_threshold=config.NMS_THRESHOLD,
                frame_width=config.FRAME_WIDTH,
                frame_height=config.FRAME_HEIGHT,
                class_map=config.RELEVANT_CLASSES
            )

            # F5: Tracking vehicular
            self.tracker_vehicular = IoUTracker(
                iou_threshold=config.IOU_THRESHOLD,
                max_age=config.MAX_AGE,
                min_hits=config.MIN_HITS
            )

            # F5b: Tracking peatonal (solo en modo semáforos)
            if self.enable_traffic_lights:
                self.tracker_pedestrian = IoUTracker(
                    iou_threshold=config.IOU_THRESHOLD,
                    max_age=config.MAX_AGE,
                    min_hits=config.MIN_HITS
                )

            # F6: Almacenamiento
            self.stats_collector = StatsCollector(
                results_dir=config.RESULTS_DIR
            )
            self.stats_collector.start_session()

            # F8: Controlador de semáforos (solo en modo semáforos)
            if self.enable_traffic_lights:
                self.traffic_light_controller = TrafficLightController(
                    min_green_time=config.MIN_GREEN_TIME,
                    max_green_time=config.MAX_GREEN_TIME,
                    yellow_time=config.YELLOW_TIME,
                    high_traffic_threshold=config.HIGH_TRAFFIC_THRESHOLD,
                    congestion_time_threshold=config.CONGESTION_TIME_THRESHOLD,
                    no_traffic_wait_time=config.NO_TRAFFIC_WAIT_TIME
                )
                logger.info("Controlador de semáforos inicializado")

            # F7: Streaming (opcional)
            if self.enable_streaming and config.ENABLE_STREAMING:
                if self.enable_traffic_lights:
                    # Modo dual: dos streamers independientes
                    logger.info("Inicializando streaming dual...")

                    # Streamer vehicular
                    self.streamer_vehicular = FFmpegStreamer(
                        width=config.FRAME_WIDTH,
                        height=config.FRAME_HEIGHT,
                        fps=config.TARGET_FPS,
                        output_dir=config.STREAM_DIR,
                        use_gpu=config.USE_GPU_ENCODING,
                        bitrate=config.VIDEO_BITRATE,
                        hls_time=config.HLS_SEGMENT_DURATION,
                        stream_name='vehicular'
                    )
                    if not self.streamer_vehicular.start():
                        logger.warning("No se pudo iniciar streaming vehicular")
                        self.streamer_vehicular = None

                    # Streamer peatonal (diferente playlist)
                    self.streamer_pedestrian = FFmpegStreamer(
                        width=config.FRAME_WIDTH,
                        height=config.FRAME_HEIGHT,
                        fps=config.TARGET_FPS,
                        output_dir=config.STREAM_DIR,
                        use_gpu=config.USE_GPU_ENCODING,
                        bitrate=config.VIDEO_BITRATE,
                        hls_time=config.HLS_SEGMENT_DURATION,
                        stream_name='pedestrian'
                    )
                    if not self.streamer_pedestrian.start():
                        logger.warning("No se pudo iniciar streaming peatonal")
                        self.streamer_pedestrian = None
                else:
                    # Modo simple: un solo streamer
                    self.streamer = FFmpegStreamer(
                        width=config.FRAME_WIDTH,
                        height=config.FRAME_HEIGHT,
                        fps=config.TARGET_FPS,
                        output_dir=config.STREAM_DIR,
                        use_gpu=config.USE_GPU_ENCODING,
                        bitrate=config.VIDEO_BITRATE,
                        hls_time=config.HLS_SEGMENT_DURATION
                    )
                    if not self.streamer.start():
                        logger.warning("No se pudo iniciar streaming, continuando sin él")
                        self.streamer = None

            logger.info("Todos los componentes inicializados correctamente")
            return True

        except Exception as e:
            logger.error(f"Error durante la inicialización: {e}")
            return False

    def start_web_server(self):
        """
        Inicia el servidor web Flask en un thread separado.
        """
        logger.info("Iniciando servidor web...")

        # Inicializar Flask con el stats collector y controlador de semáforos
        web_app.init_app(
            self.stats_collector,
            config.STREAM_DIR,
            self.traffic_light_controller
        )

        # Crear thread para el servidor
        self.web_thread = threading.Thread(
            target=web_app.run_server,
            kwargs={
                'host': config.FLASK_HOST,
                'port': config.FLASK_PORT,
                'debug': config.FLASK_DEBUG
            },
            daemon=True
        )
        self.web_thread.start()

        logger.info(f"Servidor web disponible en http://{config.FLASK_HOST}:{config.FLASK_PORT}")

    def process_frame(self, frame, tracker):
        """
        Procesa un frame completo a través del pipeline.

        Args:
            frame: Frame de video a procesar
            tracker: Tracker IoU a utilizar

        Returns:
            tuple: (frame_procesado, objetos_trackeados, tiempo_inferencia)
        """
        # F2: Preprocesamiento
        input_tensor = self.preprocessor.process(frame)
        if input_tensor is None:
            return frame, [], 0.0

        # F3: Inferencia
        detection_results = self.detector.detect(input_tensor)
        if detection_results is None:
            return frame, [], 0.0

        inference_time = detection_results['inference_time']

        # F4: Post-procesamiento
        detections = self.postprocessor.process(detection_results)

        # F5: Tracking
        tracked_objects = tracker.update(detections)

        # Dibujar detecciones en el frame
        if config.DRAW_BBOXES:
            frame = self.postprocessor.draw_detections(
                frame,
                tracked_objects,
                colors=config.CLASS_COLORS
            )

        return frame, tracked_objects, inference_time

    def count_by_category(self, tracked_objects, category_classes):
        """
        Cuenta objetos detectados según categoría.

        Args:
            tracked_objects: Lista de objetos trackeados
            category_classes: Lista de clases a contar

        Returns:
            int: Número de objetos de la categoría
        """
        count = 0
        for obj in tracked_objects:
            if obj['class'] in category_classes:
                count += 1
        return count

    def run(self):
        """
        Loop principal del sistema.
        """
        if self.enable_traffic_lights:
            self._run_traffic_light_mode()
        else:
            self._run_simple_mode()

    def _run_simple_mode(self):
        """
        Loop principal en modo simple (una fuente de video).
        """
        self.running = True
        logger.info("Iniciando loop principal (modo simple)...")
        logger.info("Presione Ctrl+C para detener")

        fps_start_time = time.time()
        fps_frame_count = 0

        try:
            while self.running:
                # Capturar frame
                ret, frame = self.video_capture_vehicular.read()
                if not ret:
                    logger.warning("No se pudo leer frame, finalizando...")
                    break

                # Procesar frame
                processed_frame, tracked_objects, inference_time = self.process_frame(
                    frame, self.tracker_vehicular
                )

                # F6: Actualizar estadísticas
                self.stats_collector.update(tracked_objects, inference_time)

                # F7: Enviar a streaming
                if self.streamer and self.streamer.is_alive():
                    self.streamer.write_frame(processed_frame)

                # Calcular y mostrar FPS
                fps_frame_count += 1
                elapsed = time.time() - fps_start_time

                if elapsed >= config.FPS_UPDATE_INTERVAL:
                    fps = fps_frame_count / elapsed
                    self.stats_collector.update_fps(fps)

                    if config.PRINT_FPS:
                        logger.info(f"FPS: {fps:.2f} | "
                                  f"Detecciones: {len(tracked_objects)} | "
                                  f"Inferencia: {inference_time:.1f}ms")

                    fps_start_time = time.time()
                    fps_frame_count = 0

        except KeyboardInterrupt:
            logger.info("\nInterrupción recibida, deteniendo sistema...")
        except Exception as e:
            logger.error(f"Error en loop principal: {e}")
        finally:
            self.stop()

    def _run_traffic_light_mode(self):
        """
        Loop principal en modo semáforos (dos fuentes de video).
        """
        self.running = True
        logger.info("Iniciando loop principal (modo semáforos optimizado)...")
        logger.info("Alternando procesamiento IA entre videos para mejor rendimiento")
        logger.info("Presione Ctrl+C para detener")

        fps_start_time = time.time()
        fps_frame_count = 0
        frame_counter = 0

        last_processed_vehicular = None
        last_processed_pedestrian = None
        last_tracked_vehicular = []
        last_tracked_pedestrian = []
        last_vehicle_count = 0
        last_pedestrian_count = 0
        last_inference_time_v = 0
        last_inference_time_p = 0

        try:
            while self.running:
                # Capturar frames de ambas fuentes
                ret_vehicular, frame_vehicular = self.video_capture_vehicular.read()
                ret_pedestrian, frame_pedestrian = self.video_capture_pedestrian.read()

                if not ret_vehicular or not ret_pedestrian:
                    logger.warning("No se pudo leer frame, finalizando...")
                    break

                frame_counter += 1

                # Alternar procesamiento: frames pares -> vehicular, frames impares -> peatonal
                process_vehicular = (frame_counter % 2 == 0)
                process_pedestrian = (frame_counter % 2 == 1)

                # Procesar frame vehicular (con IA o usando cache)
                if process_vehicular:
                    processed_vehicular, tracked_vehicular, inference_time_v = self.process_frame(
                        frame_vehicular, self.tracker_vehicular
                    )
                    last_processed_vehicular = processed_vehicular
                    last_tracked_vehicular = tracked_vehicular
                    last_inference_time_v = inference_time_v
                else:
                    self.tracker_vehicular.update([])

                    # Usar frame anterior con detecciones previas
                    if last_processed_vehicular is not None:
                        if config.DRAW_BBOXES and last_tracked_vehicular:
                            processed_vehicular = self.postprocessor.draw_detections(
                                frame_vehicular.copy(),
                                last_tracked_vehicular,
                                colors=config.CLASS_COLORS
                            )
                        else:
                            processed_vehicular = frame_vehicular.copy()
                        tracked_vehicular = last_tracked_vehicular
                    else:
                        processed_vehicular = frame_vehicular.copy()
                        tracked_vehicular = []

                # Procesar frame peatonal (con IA o usando cache)
                if process_pedestrian:
                    processed_pedestrian, tracked_pedestrian, inference_time_p = self.process_frame(
                        frame_pedestrian, self.tracker_pedestrian
                    )
                    last_processed_pedestrian = processed_pedestrian
                    last_tracked_pedestrian = tracked_pedestrian
                    last_inference_time_p = inference_time_p
                else:
                    self.tracker_pedestrian.update([])

                    # Usar frame anterior con detecciones previas
                    if last_processed_pedestrian is not None:
                        if config.DRAW_BBOXES and last_tracked_pedestrian:
                            processed_pedestrian = self.postprocessor.draw_detections(
                                frame_pedestrian.copy(),
                                last_tracked_pedestrian,
                                colors=config.CLASS_COLORS
                            )
                        else:
                            processed_pedestrian = frame_pedestrian.copy()
                        tracked_pedestrian = last_tracked_pedestrian
                    else:
                        processed_pedestrian = frame_pedestrian.copy()
                        tracked_pedestrian = []

                # Contar vehículos y peatones (usar los tracked actuales)
                vehicle_count = self.count_by_category(tracked_vehicular, config.VEHICLE_CLASSES)
                pedestrian_count = self.count_by_category(tracked_pedestrian, config.PEDESTRIAN_CLASSES)

                # Actualizar cache de conteos
                if process_vehicular:
                    last_vehicle_count = vehicle_count
                if process_pedestrian:
                    last_pedestrian_count = pedestrian_count

                # F8: Actualizar controlador de semáforos
                self.traffic_light_controller.update_traffic_counts(vehicle_count, pedestrian_count)
                traffic_light_state = self.traffic_light_controller.update()

                # F6: Actualizar estadísticas
                all_tracked = tracked_vehicular + tracked_pedestrian
                avg_inference_time = (last_inference_time_v + last_inference_time_p) / 2
                self.stats_collector.update(all_tracked, avg_inference_time)
                self.stats_collector.update_traffic_light_state(traffic_light_state)

                # F7: Enviar a streaming (ambos frames a sus streamers respectivos)
                if self.streamer_vehicular and self.streamer_vehicular.is_alive():
                    self.streamer_vehicular.write_frame(processed_vehicular)

                if self.streamer_pedestrian and self.streamer_pedestrian.is_alive():
                    self.streamer_pedestrian.write_frame(processed_pedestrian)

                # Calcular y mostrar FPS
                fps_frame_count += 1
                elapsed = time.time() - fps_start_time

                if elapsed >= config.FPS_UPDATE_INTERVAL:
                    fps = fps_frame_count / elapsed
                    self.stats_collector.update_fps(fps)

                    if config.PRINT_FPS:
                        logger.info(f"FPS: {fps:.2f} | "
                                  f"Vehículos: {vehicle_count} | Peatones: {pedestrian_count} | "
                                  f"Semáforo: V={traffic_light_state['vehicular_state']}, "
                                  f"P={traffic_light_state['pedestrian_state']}")

                    fps_start_time = time.time()
                    fps_frame_count = 0

        except KeyboardInterrupt:
            logger.info("\nInterrupción recibida, deteniendo sistema...")
        except Exception as e:
            logger.error(f"Error en loop principal: {e}")
        finally:
            self.stop()

    def stop(self):
        """
        Detiene el sistema y libera recursos.
        """
        logger.info("Deteniendo sistema...")
        self.running = False

        # Detener componentes de captura
        if self.video_capture_vehicular:
            self.video_capture_vehicular.release()

        if self.video_capture_pedestrian:
            self.video_capture_pedestrian.release()

        if self.streamer:
            self.streamer.stop()

        if self.streamer_vehicular:
            self.streamer_vehicular.stop()

        if self.streamer_pedestrian:
            self.streamer_pedestrian.stop()

        if self.detector:
            self.detector.cleanup()

        # Guardar estadísticas finales
        if self.stats_collector and config.SAVE_STATS_ON_EXIT:
            logger.info("Generando estadísticas finales...")
            stats_file = self.stats_collector.save_stats(
                filename_prefix=config.STATS_FILENAME_PREFIX
            )
            if stats_file:
                logger.info(f"Estadísticas guardadas en: {stats_file}")

        logger.info("Sistema detenido correctamente")

    def signal_handler(self, signum, frame):
        """
        Manejador de señales (Ctrl+C).
        """
        logger.info("\nSeñal de interrupción recibida")
        self.stop()
        sys.exit(0)


def parse_arguments():
    """
    Parsea argumentos de línea de comandos.
    """
    parser = argparse.ArgumentParser(
        description='Sistema de Monitoreo Inteligente de Tránsito'
    )

    parser.add_argument(
        '--input', '-i',
        type=str,
        default='0',
        help='Fuente de video: 0 para cámara, o ruta a archivo MP4 (default: 0)'
    )

    parser.add_argument(
        '--no-streaming',
        action='store_true',
        help='Deshabilitar streaming FFmpeg'
    )

    parser.add_argument(
        '--no-web',
        action='store_true',
        help='Deshabilitar servidor web'
    )

    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help='Ruta al modelo TFLite (sobreescribe config)'
    )

    parser.add_argument(
        '--traffic-lights',
        action='store_true',
        help='Habilitar modo de control inteligente de semáforos (dos cámaras)'
    )

    return parser.parse_args()


def main():
    """
    Función principal.
    """
    args = parse_arguments()

    # Determinar fuente de video
    video_source = args.input
    if video_source.isdigit():
        video_source = int(video_source)

    if args.model:
        config.MODEL_PATH = args.model

    enable_traffic_lights = args.traffic_lights or config.ENABLE_TRAFFIC_LIGHTS

    system = TrafficMonitorSystem(
        video_source=video_source,
        enable_streaming=not args.no_streaming,
        enable_traffic_lights=enable_traffic_lights
    )

    signal.signal(signal.SIGINT, system.signal_handler)
    signal.signal(signal.SIGTERM, system.signal_handler)

    if not system.initialize():
        logger.error("Error en la inicialización, abortando")
        sys.exit(1)

    # Iniciar servidor web 
    if not args.no_web:
        system.start_web_server()
        logger.info("Espere 2 segundos para que el servidor web inicie...")
        time.sleep(2)
    system.run()

if __name__ == '__main__':
    main()
