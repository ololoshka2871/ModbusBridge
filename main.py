#!/usr/bin/env python
# -*- coding: utf8 -*-

from serial_enumerator import get_serial_ports
from BrigeController import BridgeController
from threading import Timer
import atexit

from flask import Flask, render_template, redirect, url_for, request, send_from_directory
import webbrowser

app = Flask(__name__)

speeds = (9600, 38400, 57600, 115200)
modes = ['8{}{}'.format(parity, stop) for parity in ('N', 'E', 'O') for stop in (1, 2)]
last_error = "Сервер не запущен"

bridge = BridgeController()

settings = {
    "default_port": None,
    "default_speed": None,
    "default_mode": None,
    "default_use_rts": True,
    "tcp_port_selector": 502,
    "tcp_max_connections": 3,
    "rtu_max_trys": 0,
    "rtu_min_delay": 1,
    "rtu_rx_timeout": 10,
    "tcp_timeout": 60
}


@app.route('/', methods=['GET'])
def index():
    ports = get_serial_ports()
    return render_template('index.html', ports=ports, speeds=speeds, modes=modes, last_error=last_error,
                           server_is_running=bridge.status(), **settings)


@app.route('/control', methods=['POST'])
def control():
    global settings
    global last_error

    if bridge.status() or len(request.form) == 0:
        bridge.stop()
        last_error = bridge.last_error()
    else:
        res = parse_form(request.form)

        if type(res) is str:
            last_error = res
            return redirect(url_for('index'))
        else:
            settings = res

            bridge.port = settings['default_port']
            bridge.speed = settings['default_speed']
            bridge.mode = settings['default_mode']
            bridge.use_rts = settings['default_use_rts']
            bridge.tcp_port = settings['tcp_port_selector']
            bridge.max_con = settings['tcp_max_connections']
            bridge.max_retries = settings['rtu_max_trys']
            bridge.pause = settings['rtu_min_delay']
            bridge.wait = settings['rtu_rx_timeout']
            bridge.tcp_timeout = settings['tcp_timeout']

            if not bridge.start():
                last_error = bridge.last_error().replace('\n', '<p>')
            else:
                last_error = None

    return redirect(url_for('index'))


@app.route('/static/<path:path>', methods=['GET'])
def serve_static(path):
    return send_from_directory('static', path)


def parse_form(form_values):
    new_settings = dict()

    new_settings['default_port'] = form_values['serial_port']
    if new_settings['default_port'] not in [p.device for p in get_serial_ports()]:
        return 'Invalid device selected ({})'.format(new_settings['default_port'])

    new_settings['default_speed'] = form_values['serial_speed']
    if new_settings['default_speed'] not in [str(s) for s in speeds]:
        return 'Invalid speed selected ({})'.format(new_settings['default_speed'])
    else:
        new_settings['default_speed'] = int(new_settings['default_speed'])

    new_settings['default_mode'] = form_values['serial_mode']
    if new_settings['default_mode'] not in modes:
        return 'Invalid mode selected ({})'.format(new_settings['default_mode'])

    try:
        new_settings['default_use_rts'] = bool(form_values['serial_rts'])
        new_settings['tcp_port_selector'] = int(form_values['tcp_port'])
        new_settings['tcp_max_connections'] = int(form_values['tcp_max_connections'])
        new_settings['rtu_max_trys'] = int(form_values['rtu_max_trys'])
        new_settings['rtu_min_delay'] = int(form_values['rtu_min_delay'])
        new_settings['rtu_rx_timeout'] = int(form_values['rtu_rx_timeout'])
        new_settings['tcp_timeout'] = int(form_values['tcp_timeout'])
    except Exception as e:
        return str(e)

    return new_settings


def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/')


if __name__ == "__main__":
    Timer(1, open_browser).start()
    atexit.register(lambda: bridge.stop())
    app.run(debug=True, use_debugger=False, use_reloader=False, passthrough_errors=True)
