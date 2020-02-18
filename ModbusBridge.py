#!/usr/bin/env python
# -*- coding: utf8 -*-

from threading import Timer
from collections import namedtuple
import atexit
import re
import os
import sys
import webbrowser
import socket
import platform

import netifaces
from flask import Flask, render_template, redirect, url_for, request, send_from_directory

from serial_enumerator import get_serial_ports
from BrigeController import BridgeController
from mDNSanoncer import mDNSanoncer

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

www_port = 7123
speeds = (9600, 38400, 57600, 115200)
modes = ['8{}{}'.format(parity, stop) for parity in ('N', 'E', 'O') for stop in (1, 2)]
last_error = "Сервер не запущен"

bridge = BridgeController()

http_anoncer = mDNSanoncer()
modbus_tcp_anoncer = mDNSanoncer()

COM_pattern = re.compile('COM(\d+)')

# Defaults
settings = {
    "default_port": None,
    "default_speed": 57600,
    "default_mode": '8N1',
    "default_use_rts": True,
    "tcp_port_selector": 502,
    "tcp_max_connections": 3,
    "rtu_max_trys": 1,
    "rtu_min_delay": 2,
    "rtu_rx_timeout": 25,
    "tcp_timeout": 60
}

Portrecord = namedtuple('Portrecord', 'device description inaccesable')


@app.route('/', methods=['GET'])
def index():
    ports = get_serial_ports()
    return render_template('index.html', ports=filter_ports(ports),
                           speeds=speeds, modes=modes, last_error=last_error,
                           server_is_running=bridge.status(), **settings)


@app.route('/control', methods=['POST'])
def control():
    global settings
    global last_error

    if bridge.status() or len(request.form) == 0:
        bridge.stop()
        modbus_tcp_anoncer.stop()
        last_error = bridge.last_error()
    else:
        res = parse_form(request.form)

        if type(res) is str:
            last_error = res
            return redirect(url_for('index'))
        else:
            settings = res

            bridge.port = patch_portname(settings['default_port'])
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
                modbus_tcp_anoncer.port = bridge.tcp_port
                modbus_tcp_anoncer.start()
                last_error = None

    return redirect(url_for('index'))


def filter_ports(portlist):
    newports = []
    if platform.system() == 'Linux':
        return [Portrecord(
            device=p.device,
            description='{} ({})'.format(p.description, p.device),
            inaccesable=False) for p in portlist]
    else:
        for port in portlist:
            match = COM_pattern.match(port.device)
            inaccesable = int(match[1]) > 64
            p = Portrecord(
                device=port.device,
                description='{} (недоступно)'.format(port.description) if inaccesable else port.description,
                inaccesable=inaccesable
            )
            newports.append(p)

        return newports


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


def patch_portname(comport):
    if platform.system() == 'Linux':
        return comport
    else:
        # for msys
        match = COM_pattern.match(comport)
        return '/dev/ttyS{}'.format(int(match[1]) - 1)


def all_my_ips():
    interfaces = netifaces.interfaces()

    ip4 = [netifaces.ifaddresses(iface)[netifaces.AF_INET][0]['addr']
           for iface in interfaces
           if netifaces.AF_INET in netifaces.ifaddresses(iface)]
    ip6 = [netifaces.ifaddresses(iface)[netifaces.AF_INET6][0]['addr'].split('%')[0]
           for iface in interfaces
           if netifaces.AF_INET6 in netifaces.ifaddresses(iface)]

    ip4 = filter(lambda ip: ip != '127.0.0.1' and not ip.startswith('169.254.'), ip4)
    ip6 = filter(lambda ip: ip != '::1' and not ip.startswith('fe80:'), ip6)
    return [socket.inet_pton(socket.AF_INET, ip) for ip in ip4] + \
           [socket.inet_pton(socket.AF_INET6, ip) for ip in ip6]


def register_mdns_records():
    hostname = socket.gethostname()

    ips = all_my_ips()

    http_anoncer.service = "_http._tcp.local.".format(hostname)
    http_anoncer.name = "Modbus TCP to RTU bridge configurator on {}._http._tcp.local.".format(hostname)
    http_anoncer.port = www_port
    http_anoncer.address = ips
    http_anoncer.desc = {'path': '/'}
    http_anoncer.server = "{}-conf.modbusbridge.local.".format(hostname)

    modbus_tcp_anoncer.service = "_mbtcp._tcp.local.".format(hostname)
    modbus_tcp_anoncer.name = "Modbus TCP to RTU bridge on {}._mbtcp._tcp.local.".format(hostname)
    # modbus_tcp_anoncer.port # after configuration done
    modbus_tcp_anoncer.address = ips
    modbus_tcp_anoncer.server = "{}.modbusbridge.local.".format(hostname)


def open_browser():
    webbrowser.open_new('http://127.0.0.1:{}/'.format(www_port))


def at_stop():
    bridge.stop()
    http_anoncer.stop()
    modbus_tcp_anoncer.stop()
    mDNSanoncer.close()


if __name__ == "__main__":
    Timer(1, open_browser).start()
    atexit.register(at_stop)
    register_mdns_records()
    http_anoncer.start()
    app.run(debug=True, use_debugger=False, use_reloader=False, passthrough_errors=True,
            port=www_port, host='0.0.0.0')
