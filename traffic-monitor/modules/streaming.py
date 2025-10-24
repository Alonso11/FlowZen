"""
F7: Módulo de Streaming con FFmpeg
Responsabilidad: Transmitir video procesado a navegador web vía HLS
"""
import subprocess
import logging
import cv2
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class FFmpegStreamer:
    """
    Gestiona streaming de video usando FFmpeg con HLS.
    """
    def __init__(self, width=640, height=480, fps=15,
                 output_dir='/tmp', use_gpu=True, bitrate='1500k'):
        """
        Inicializa el streamer FFmpeg.
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.output_dir = Path(output_dir)
        self.use_gpu = use_gpu
        self.bitrate = bitrate

        self.process = None
        self.is_running = False

        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"FFmpegStreamer inicializado: {width}x{height}@{fps}fps, "
                   f"gpu={use_gpu}, bitrate={bitrate}")

    def start(self):
        """
        Inicia el proceso FFmpeg.
        """
        if self.is_running:
            logger.warning("Streamer ya está corriendo")
            return False

        try:
            import glob
            import os
            old_files = glob.glob(str(self.output_dir / 'stream*'))
            for old_file in old_files:
                try:
                    os.remove(old_file)
                    logger.debug(f"Archivo HLS antiguo eliminado: {old_file}")
                except Exception as e:
                    logger.warning(f"No se pudo eliminar {old_file}: {e}")

            if old_files:
                logger.info(f"Limpiados {len(old_files)} archivos HLS antiguos")

            if self.use_gpu:
                codec = 'h264_omx'  # GPU en Raspberry Pi
            else:
                codec = 'libx264'  # CPU

            output_path = str(self.output_dir / 'stream.m3u8')

            command = [
                'ffmpeg',
                '-y',  
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-s', f'{self.width}x{self.height}',
                '-r', str(self.fps),
                '-i', '-',  
                
                # Configuración de video
                '-c:v', codec,
                '-profile:v', 'baseline', 
                '-level', '3.0',          
                '-pix_fmt', 'yuv420p',  
                '-b:v', self.bitrate,
                '-preset', 'ultrafast',
                '-tune', 'zerolatency',
                '-g', str(self.fps * 2),   # GOP = 2 segundos
                
                # Configuración HLS
                '-f', 'hls',
                '-hls_time', '2', 
                '-hls_list_size', '10', 
                '-hls_flags', 'delete_segments',  
                '-hls_delete_threshold', '1',  
                '-hls_segment_type', 'mpegts',
                '-hls_segment_filename', str(self.output_dir / 'stream%03d.ts'),
                output_path
            ]

            # Iniciar proceso
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            self.is_running = True
            logger.info(f"FFmpeg iniciado: PID={self.process.pid}")
            logger.info(f"Codec usado: {codec}")
            logger.info(f"Salida HLS: {output_path}")

            # Verificar que el proceso arrancó correctamente
            import time
            time.sleep(0.5)
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                logger.error(f"FFmpeg falló al iniciar:")
                logger.error(f"STDOUT: {stdout.decode('utf-8', errors='ignore')}")
                logger.error(f"STDERR: {stderr.decode('utf-8', errors='ignore')}")
                self.is_running = False
                return False

            return True

        except Exception as e:
            logger.error(f"Error al iniciar FFmpeg: {e}")
            self.is_running = False
            return False

    def write_frame(self, frame):
        """
        Envía un frame a FFmpeg.
        """
        if not self.is_running or self.process is None:
            return False

        try:
            if frame.shape[1] != self.width or frame.shape[0] != self.height:
                frame = cv2.resize(frame, (self.width, self.height))

            self.process.stdin.write(frame.tobytes())
            return True

        except (BrokenPipeError, IOError) as e:
            logger.error(f"Error al escribir frame: {e}")
            self.is_running = False
            return False

    def stop(self):
        """
        Detiene el proceso FFmpeg.
        """
        if not self.is_running or self.process is None:
            return

        try:
            if self.process.stdin:
                self.process.stdin.close()

            self.process.wait(timeout=5)
            logger.info("FFmpeg detenido correctamente")

        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg no respondió, terminando forzadamente")
            self.process.kill()
            self.process.wait()

        except Exception as e:
            logger.error(f"Error al detener FFmpeg: {e}")

        finally:
            self.process = None
            self.is_running = False

    def is_alive(self):
        """
        Verifica si el proceso FFmpeg está corriendo.
        """
        if self.process is None:
            return False
        return self.process.poll() is None

    def get_playlist_path(self):
        """
        Retorna la ruta del archivo playlist HLS.
        """
        return self.output_dir / 'stream.m3u8'

    def __enter__(self):
        """
        Context manager: entrada.
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager: salida.
        """
        self.stop()
        return False
