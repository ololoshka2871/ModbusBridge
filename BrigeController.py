# -*- coding: utf8 -*-

import logging
import os
import sys
import subprocess


class BridgeController:
    def __init__(self):
        self.executable = os.path.join(sys._MEIPASS, 'bin', 'mbusd') \
            if getattr(sys, 'frozen', False) else 'bin/mbusd'
        self.port = None
        self.speed = 57600
        self.mode = '8N1'
        self.tcp_port = 502
        self.use_rts = True
        self.max_con = 3
        self.max_retries = 0
        self.pause = 1
        self.wait = 10
        self.tcp_timeout = 60

        self._status = False
        self._last_error = None

        self.log = logging.getLogger("BridgeController")

        self.process = None

    def status(self):
        return self._status

    def last_error(self):
        return self._last_error

    def start(self):
        parameters = [
            self.executable,
            '-d',
            '-L', '-',
            '-p', self.port,
            '-s', self.speed,
            '-m', self.mode,
            '-P', self.tcp_port,
            '-C', self.max_con,
            '-N', self.max_retries,
            '-R', self.pause,
            '-W', self.wait,
            '-T', self.tcp_timeout
        ]
        if self.use_rts:
            parameters.append('-t')

        parameters = tuple(map(str, parameters))
        self.log.warning('Starting bridge with parameters: %s', ' '.join(parameters))

        self.process = subprocess.Popen(parameters, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            o, e = self.process.communicate(timeout=0.5)
        except subprocess.TimeoutExpired:
            # success
            self._status = True
            return True

        exit_code = self.process.poll()
        self._last_error = 'Error starting daemon:\n{}\n(exit code {})'.format(e.decode(), exit_code)
        self.process = None
        self._status = False
        return False

    def stop(self):
        self.log.warning('Stopping bridge...')
        if self.process:
            self.process.terminate()
            try:
                self.process.communicate(timeout=1)
                self._last_error = None
            except subprocess.TimeoutExpired:
                err = 'Stopping daemon failed, zombie created'
                self.log.warning(err)
                self._last_error = err

            self.process = None

        self._status = False
