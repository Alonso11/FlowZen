"""
Servidor Web Flask
Responsabilidad: Servir dashboard web y endpoints API
"""
from flask import Flask, render_template, Response, jsonify, send_from_directory
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)

stats_collector = None
stream_dir = '/tmp'
traffic_light_controller = None


def init_app(stats_collector_instance, stream_directory='/tmp', traffic_light_controller_instance=None):
    """
    Inicializa la aplicación Flask con el collector de estadísticas y controlador de semáforos.

    Args:
        stats_collector_instance: Instancia de StatsCollector
        stream_directory: Directorio donde se guardan los archivos HLS
        traffic_light_controller_instance: Instancia de TrafficLightController (opcional)
    """
    global stats_collector, stream_dir, traffic_light_controller
    stats_collector = stats_collector_instance
    stream_dir = stream_directory
    traffic_light_controller = traffic_light_controller_instance
    logger.info("Aplicación Flask inicializada")
    if traffic_light_controller:
        logger.info("Sistema de semáforos habilitado en API")


@app.route('/')
def index():
    """
    Página principal del dashboard.
    """
    return render_template('index.html')


@app.route('/api/stats')
def get_stats():
    """
    Endpoint para obtener estadísticas en tiempo real.
    """
    if stats_collector is None:
        return jsonify({'error': 'Stats collector not initialized'}), 500

    stats = stats_collector.get_current_stats()
    return jsonify(stats)


@app.route('/stream.m3u8')
def serve_playlist():
    """
    Sirve el archivo playlist HLS (para compatibilidad con modo simple).
    """
    try:
        from flask import make_response
        response = make_response(send_from_directory(stream_dir, 'stream.m3u8',
                                  mimetype='application/vnd.apple.mpegurl'))
        # Deshabilitar cache para forzar actualizaciones
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        logger.error(f"Error sirviendo playlist: {e}")
        return jsonify({'error': 'Playlist not found'}), 404


@app.route('/<stream_name>.m3u8')
def serve_named_playlist(stream_name):
    """
    Sirve playlists HLS con nombres personalizados (vehicular.m3u8, pedestrian.m3u8).
    """
    try:
        from flask import make_response
        filename = f'{stream_name}.m3u8'
        response = make_response(send_from_directory(stream_dir, filename,
                                  mimetype='application/vnd.apple.mpegurl'))
        # Deshabilitar cache para forzar actualizaciones
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        logger.error(f"Error sirviendo playlist {stream_name}: {e}")
        return jsonify({'error': f'Playlist {stream_name} not found'}), 404


@app.route('/<stream_name><segment>.ts')
def serve_segment(stream_name, segment):
    """
    Sirve los segmentos de video HLS (soporta nombres personalizados).
    Ejemplos: stream001.ts, vehicular001.ts, pedestrian001.ts
    """
    try:
        from flask import make_response
        filename = f'{stream_name}{segment}.ts'
        logger.debug(f"Sirviendo segmento: {filename}")
        response = make_response(send_from_directory(stream_dir, filename,
                                  mimetype='video/mp2t'))
        # Deshabilitar cache para segmentos
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        logger.error(f"Error sirviendo segmento {stream_name}{segment}: {e}")
        return jsonify({'error': f'Segment {stream_name}{segment} not found'}), 404


@app.route('/health')
def health():
    """
    Endpoint de health check.
    """
    return jsonify({'status': 'ok'}), 200


@app.route('/api/traffic-lights/state')
def get_traffic_lights_state():
    """
    Obtiene el estado actual del sistema de semáforos.
    """
    if traffic_light_controller is None:
        return jsonify({'error': 'Traffic light system not enabled'}), 404

    state = traffic_light_controller.get_state()
    return jsonify(state)


@app.route('/api/traffic-lights/statistics')
def get_traffic_lights_statistics():
    """
    Obtiene estadísticas del sistema de semáforos.
    """
    if traffic_light_controller is None:
        return jsonify({'error': 'Traffic light system not enabled'}), 404

    statistics = traffic_light_controller.get_statistics()
    return jsonify(statistics)


@app.route('/api/traffic-lights/images/<state>')
def get_traffic_light_image(state):
    """
    Sirve las imágenes de los estados de semáforos.

    Args:
        state: Estado del semáforo (vehicular_verde, vehicular_amarillo, vehicular_rojo,
               peatonal_verde, peatonal_rojo)
    """
    import config
    from flask import send_file
    import os

    # Validar estado
    valid_states = ['vehicular_verde', 'vehicular_amarillo', 'vehicular_rojo',
                    'peatonal_verde', 'peatonal_rojo']

    if state not in valid_states:
        return jsonify({'error': 'Invalid traffic light state'}), 400

    # Obtener ruta de la imagen
    image_path = config.TRAFFIC_LIGHT_IMAGES.get(state)

    if not image_path or not os.path.exists(image_path):
        return jsonify({'error': 'Traffic light image not found'}), 404

    try:
        return send_file(image_path, mimetype='image/png')
    except Exception as e:
        logger.error(f"Error sirviendo imagen de semáforo {state}: {e}")
        return jsonify({'error': 'Error loading image'}), 500


@app.errorhandler(404)
def not_found(error):
    """
    Manejador de error 404.
    """
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """
    Manejador de error 500.
    """
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


def run_server(host='0.0.0.0', port=5000, debug=False):
    """
    Inicia el servidor Flask.
    """
    logger.info(f"Iniciando servidor Flask en {host}:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)
