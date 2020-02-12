#!/user/bin/env python
# -*- coding: utf8 -*-

import os, sys
from collections import namedtuple

from flask import Flask, render_template, redirect, url_for, request, send_from_directory

# if getattr(sys, 'frozen', False):
    # template_folder = os.path.join(sys._MEIPASS, 'templates')
    # static_folder = os.path.join(sys._MEIPASS, 'static')
    # app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
# else:
app = Flask(__name__)

#Controller = namedtuple('Controller', 'label, type, name')

#controllers = [
#    Controller('COM-порт', 'text', 'serial_port'),
#    Controller('Скорость', 'number', 'speed')
#    Controller()
#]


@app.route('/', methods=['GET'])
def settings():
    return render_template('index.html')


@app.route('/control', methods=['POST'])
def control():
    print(request.form)
    return redirect(url_for('settings'))


@app.route('/css/<path:path>', methods=['GET'])
def serve_css(path):
    return send_from_directory('css', path)
	
if __name__ == "__main__":
    app.run()
