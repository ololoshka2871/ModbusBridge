# -*- coding: utf8 -*-


import logging
import socket

from zeroconf import IPVersion, ServiceInfo, Zeroconf


class mDNSanoncer:
    zeroconf = Zeroconf(ip_version=IPVersion.All)
    _log = logging.getLogger("mDNSanoncer")

    def __init__(self):
        self.ip_version = IPVersion.All
        self.service = "_http._tcp.local."
        self.name = "name._tcp.local."
        self.port = 80
        self.addresses =[socket.inet_aton("127.0.0.1")]
        self.desc = dict()
        self.server = ""
        
        self._info = None 
        
    def start(self):
        self._info = ServiceInfo(
            self.service,
            self.name,
            addresses  = self.addresses ,
            port = self.port,
            properties = self.desc,
            server = self.server
        )
        mDNSanoncer._log.warning('Anouncing service {}'.format(self._info))
        mDNSanoncer.zeroconf.register_service(self._info)
        
    def stop(self):
        if self._info:
            mDNSanoncer._log.warning('Unredistring mDNS record {}'.format(self._info))
            mDNSanoncer.zeroconf.unregister_service(self._info)
            self._info = None

    @staticmethod
    def close():
        mDNSanoncer.zeroconf.close()
