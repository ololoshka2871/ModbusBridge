import serial.tools.list_ports


def get_serial_ports():
    return [port for port in serial.tools.list_ports.comports() if port[2] != 'n/a']
