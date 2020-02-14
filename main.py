#!/user/bin/env python
# -*- coding: utf8 -*-

import os
import sys

from collections import namedtuple

from serial_enumerator import get_serial_ports

from flask import Flask, render_template, redirect, url_for, request, send_from_directory

app = Flask(__name__)

speeds = (9600, 38400, 57600, 115200)
modes = ['8{}{}'.format(parity, stop) for parity in ('N', 'E', 'O') for stop in (1, 2)]

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
    "tcp_timeout": 60,
    "server_is_running": False
}


@app.route('/', methods=['GET'])
def index():
    ports = get_serial_ports()
    return render_template('index.html', ports=ports, speeds=speeds, modes=modes, **settings)


@app.route('/control', methods=['POST'])
def control():
    global settings

    _settings = validate_server_settings(request.form)

    settings["server_is_running"] = not settings["server_is_running"]
    return redirect(url_for('index'))


@app.route('/static/<path:path>', methods=['GET'])
def serve_static(path):
    return send_from_directory('static', path)


def validate_server_settings(form_values):
    return True


if __name__ == "__main__":
    app.run(debug=True, use_debugger=False, use_reloader=False, passthrough_errors=True)
