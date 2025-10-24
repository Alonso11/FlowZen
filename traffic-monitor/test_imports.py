#!/usr/bin/env python3
"""
Script de prueba para verificar que todas las dependencias están instaladas
y que los módulos se pueden importar correctamente.
"""
import sys

def test_imports():
    """
    Prueba que todos los módulos se pueden importar.
    """
    print("="*60)
    print("Verificando dependencias del sistema...")
    print("="*60)

    errors = []
    warnings = []

    # Test 1: Python version
    print(f"\n✓ Python version: {sys.version}")
    if sys.version_info < (3, 8):
        errors.append("Python 3.8+ es requerido")

    # Test 2: NumPy
    try:
        import numpy as np
        print(f"✓ NumPy: {np.__version__}")
    except ImportError as e:
        errors.append(f"NumPy no encontrado: {e}")

    # Test 3: OpenCV
    try:
        import cv2
        print(f"✓ OpenCV: {cv2.__version__}")
    except ImportError as e:
        errors.append(f"OpenCV no encontrado: {e}")

    # Test 4: Flask
    try:
        import flask
        print(f"✓ Flask: {flask.__version__}")
    except ImportError as e:
        errors.append(f"Flask no encontrado: {e}")

    # Test 5: TensorFlow Lite
    try:
        import tflite_runtime.interpreter as tflite
        print(f"✓ TFLite Runtime: disponible")
    except ImportError:
        try:
            import tensorflow as tf
            print(f"✓ TensorFlow: {tf.__version__}")
            warnings.append("Usando TensorFlow completo en lugar de tflite-runtime (OK para desarrollo)")
        except ImportError as e:
            errors.append(f"TensorFlow Lite/TensorFlow no encontrado: {e}")

    # Test 6: Módulos locales
    print("\n" + "="*60)
    print("Verificando módulos del proyecto...")
    print("="*60 + "\n")

    try:
        import config
        print("✓ config.py")
    except ImportError as e:
        errors.append(f"config.py no se pudo importar: {e}")

    try:
        from modules import VideoCapture
        print("✓ modules.capture (VideoCapture)")
    except ImportError as e:
        errors.append(f"modules.capture: {e}")

    try:
        from modules import Preprocessor
        print("✓ modules.preprocess (Preprocessor)")
    except ImportError as e:
        errors.append(f"modules.preprocess: {e}")

    try:
        from modules import TFLiteDetector
        print("✓ modules.inference (TFLiteDetector)")
    except ImportError as e:
        errors.append(f"modules.inference: {e}")

    try:
        from modules import PostProcessor
        print("✓ modules.postprocess (PostProcessor)")
    except ImportError as e:
        errors.append(f"modules.postprocess: {e}")

    try:
        from modules import IoUTracker
        print("✓ modules.tracker (IoUTracker)")
    except ImportError as e:
        errors.append(f"modules.tracker: {e}")

    try:
        from modules import StatsCollector
        print("✓ modules.storage (StatsCollector)")
    except ImportError as e:
        errors.append(f"modules.storage: {e}")

    try:
        from modules import FFmpegStreamer
        print("✓ modules.streaming (FFmpegStreamer)")
    except ImportError as e:
        errors.append(f"modules.streaming: {e}")

    try:
        import web_app
        print("✓ web_app")
    except ImportError as e:
        errors.append(f"web_app: {e}")

    # Test 7: FFmpeg (sistema)
    print("\n" + "="*60)
    print("Verificando herramientas del sistema...")
    print("="*60 + "\n")

    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'],
                              capture_output=True,
                              text=True,
                              timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✓ FFmpeg: {version_line}")
        else:
            warnings.append("FFmpeg encontrado pero con problemas")
    except FileNotFoundError:
        warnings.append("FFmpeg no encontrado (requerido para streaming)")
    except Exception as e:
        warnings.append(f"Error al verificar FFmpeg: {e}")

    # Resumen
    print("\n" + "="*60)
    print("RESUMEN")
    print("="*60 + "\n")

    if errors:
        print("✗ ERRORES CRÍTICOS:")
        for error in errors:
            print(f"  - {error}")
        print("\nInstalar dependencias con:")
        print("  pip3 install -r requirements.txt")
        print("  sudo apt install ffmpeg")
        return False

    if warnings:
        print("⚠ ADVERTENCIAS:")
        for warning in warnings:
            print(f"  - {warning}")
        print()

    print("✓ Todas las dependencias están instaladas correctamente!")
    print("\nPuedes ejecutar el sistema con:")
    print("  1. Descargar modelo: ./download_model.sh")
    print("  2. Ejecutar: python3 main.py --input 0")

    return True


if __name__ == '__main__':
    success = test_imports()
    sys.exit(0 if success else 1)
