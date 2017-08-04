import os
import sys
import datetime
import json
import socket
import threading
try:
    import socketserver
except ImportError:
    import SocketServer as socketserver

import pytz

import pytest

PY3 = sys.version_info.major >= 3

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_PATH, 'data')

TZ_NAME_APC = 'US/Eastern'
TZ_NAME_LOCAL = 'US/Central'

@pytest.fixture(autouse=True)
def temp_logfile(tmpdir, monkeypatch):
    lf = tmpdir.join('apclinev.log')
    monkeypatch.setattr('upslogger.logger.LOG_FILENAME', str(lf))
    return lf

@pytest.fixture
def tz_override(monkeypatch):
    monkeypatch.setenv('TZ', TZ_NAME_LOCAL)
    monkeypatch.setattr('upslogger.timezone.TZ', None)
    import tzlocal
    tzlocal.reload_localzone()
    tz_dict = {
        'local':pytz.timezone(TZ_NAME_LOCAL),
        'apc':pytz.timezone(TZ_NAME_APC),
    }
    assert tz_dict['local'] == tzlocal.get_localzone()
    yield tz_dict
    monkeypatch.delenv('TZ')
    tzlocal.reload_localzone()

@pytest.fixture
def existing_logfile():
    return os.path.join(DATA_PATH, 'apclinevlog.txt')


class NISHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request.recv(1024)
        if b'\x00\x06status' in data:
            self.send_status_response()
    def send_status_response(self):
        resp = self.server.apcaccess_generator.build_status_response()
        if PY3:
            resp = bytes(resp, 'UTF-8')
        self.request.sendall(resp)

class NISServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, apcaccess_generator):
        self.apcaccess_generator = apcaccess_generator
        server_address = (apcaccess_generator.hostname, 0)
        socketserver.TCPServer.__init__(self, server_address, NISHandler)

class ApcAccessGenerator(object):
    _template_attrs = ['DATE', 'STARTTIME', 'LINEV', 'LINEFREQ']
    def __init__(self, **kwargs):
        tz = self.tz = kwargs.get('timezone', pytz.timezone(TZ_NAME_APC))
        kwargs.setdefault('DATE', datetime.datetime.now())
        kwargs.setdefault('STARTTIME', datetime.datetime.now())
        kwargs.setdefault('LINEV', 115.2)
        kwargs.setdefault('LINEFREQ', 60.)
        self.DATE = kwargs['DATE']
        self.STARTTIME = kwargs['STARTTIME']
        self.LINEV = kwargs['LINEV']
        self.LINEFREQ = kwargs['LINEFREQ']
        self._check_datetimes()

        fn = os.path.join(DATA_PATH, 'NIS-output.json')
        with open(fn, 'r') as f:
            self.tmpl_data = json.loads(f.read())

        self.hostname = kwargs.get('hostname', '127.0.0.1')
        self.server = NISServer(self)
        self.hostport = self.server.server_address[1]
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
    def stop(self):
        self.server.shutdown()
        self.server.server_close()
    def _check_datetimes(self):
        for key in ['DATE', 'STARTTIME']:
            dt = getattr(self, key)
            if dt.microsecond > 0:
                dt = dt.replace(microsecond=0)
                setattr(self, key, dt)
            if dt.tzinfo is None:
                dt = self.tz.localize(dt)
                setattr(self, key, dt)
            elif dt.tzinfo != self.tz:
                dt = self.tz.normalize(dt)
                setattr(self, key, dt)
    def get_template_dict(self):
        self._check_datetimes()
        return {attr:getattr(self, attr) for attr in self._template_attrs}
    def build_status_response(self):
        d = self.get_template_dict()
        outlines = []
        for data_line in self.tmpl_data:
            line = data_line['value'].format(**d)
            line = ': '.join([data_line['field'], line])

            # len + newline
            line_len = len(line) + 1
            line = ''.join(['\x00', chr(line_len), line])
            outlines.append(line)
        response = '\n'.join(outlines)
        return response
    def send_status_request(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.hostname, self.hostport))
        sock.sendall(b'\x00\x06status')
        resp = sock.recv(1024)
        return response


@pytest.fixture
def apcaccess_gen(monkeypatch):
    g = ApcAccessGenerator()
    monkeypatch.setattr('upslogger.apcdata.APC_HOSTPORT', g.hostport)
    print('ApcAccessGenerator running on port {}'.format(g.hostport))
    yield g
    print('teardown ApcAccessGenerator')
    g.stop()
    print('teardown complete')
