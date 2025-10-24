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


def init_app(stats_collector_instance, stream_directory='/tmp'):
    """
    Inicializa la aplicación Flask con el collector de estadísticas.
    """
    global stats_collector, stream_dir
    stats_collector = stats_collector_instance
    stream_dir = stream_directory
    logger.info("Aplicación Flask inicializada")


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
    Sirve el archivo playlist HLS.
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


@app.route('/stream<int:segment>.ts')
def serve_segment(segment):
    """
    Sirve los segmentos de video HLS.
    """
    try:
        from flask import make_response
        filename = f'stream{segment:03d}.ts'
        logger.debug(f"Sirviendo segmento: {filename}")
        response = make_response(send_from_directory(stream_dir, filename,
                                  mimetype='video/mp2t'))
        # Deshabilitar cache para segmentos
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        logger.error(f"Error sirviendo segmento {segment}: {e}")
        return jsonify({'error': f'Segment {segment} not found'}), 404


@app.route('/health')
def health():
    """
    Endpoint de health check.
    """
    return jsonify({'status': 'ok'}), 200


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
