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
    FFmpegStreamer
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

    def __init__(self, video_source=0, enable_streaming=True):
        """
        Inicializa el sistema.
        """
        self.video_source = video_source
        self.enable_streaming = enable_streaming
        self.running = False
        # Componentes del pipeline
        self.video_capture = None
        self.preprocessor = None
        self.detector = None
        self.postprocessor = None
        self.tracker = None
        self.stats_collector = None
        self.streamer = None
        # Thread del servidor web
        self.web_thread = None

        logger.info("="*60)
        logger.info("Sistema de Monitoreo Inteligente de Tránsito")
        logger.info("="*60)

    def initialize(self):
        """
        Inicializa todos los componentes del sistema.
        """
        logger.info("Inicializando componentes...")

        try:
            # F1: Captura de video
            self.video_capture = VideoCapture(
                source=self.video_source,
                width=config.FRAME_WIDTH,
                height=config.FRAME_HEIGHT,
                fps=config.TARGET_FPS
            )
            if not self.video_capture.open():
                logger.error("Error al abrir fuente de video")
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

            # F5: Tracking
            self.tracker = IoUTracker(
                iou_threshold=config.IOU_THRESHOLD,
                max_age=config.MAX_AGE,
                min_hits=config.MIN_HITS
            )

            # F6: Almacenamiento
            self.stats_collector = StatsCollector(
                results_dir=config.RESULTS_DIR
            )
            self.stats_collector.start_session()

            # F7: Streaming (opcional)
            if self.enable_streaming and config.ENABLE_STREAMING:
                self.streamer = FFmpegStreamer(
                    width=config.FRAME_WIDTH,
                    height=config.FRAME_HEIGHT,
                    fps=config.TARGET_FPS,
                    output_dir=config.STREAM_DIR,
                    use_gpu=config.USE_GPU_ENCODING,
                    bitrate=config.VIDEO_BITRATE
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

        # Inicializar Flask con el stats collector
        web_app.init_app(self.stats_collector, config.STREAM_DIR)

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

    def process_frame(self, frame):
        """
        Procesa un frame completo a través del pipeline.
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
        tracked_objects = self.tracker.update(detections)

        # Dibujar detecciones en el frame
        if config.DRAW_BBOXES:
            frame = self.postprocessor.draw_detections(
                frame,
                tracked_objects,
                colors=config.CLASS_COLORS
            )

        return frame, tracked_objects, inference_time

    def run(self):
        """
        Loop principal del sistema.
        """
        self.running = True
        logger.info("Iniciando loop principal...")
        logger.info("Presione Ctrl+C para detener")

        fps_start_time = time.time()
        fps_frame_count = 0

        try:
            while self.running:
                # Capturar frame
                ret, frame = self.video_capture.read()
                if not ret:
                    logger.warning("No se pudo leer frame, finalizando...")
                    break

                # Procesar frame
                processed_frame, tracked_objects, inference_time = self.process_frame(frame)

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

    def stop(self):
        """
        Detiene el sistema y libera recursos.
        """
        logger.info("Deteniendo sistema...")
        self.running = False

        # Detener componentes
        if self.video_capture:
            self.video_capture.release()

        if self.streamer:
            self.streamer.stop()

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

    system = TrafficMonitorSystem(
        video_source=video_source,
        enable_streaming=not args.no_streaming
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
