"""Route a second launcher to the running process without competing JSON writers."""
import hashlib
import json
from PyQt6.QtCore import QTimer
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


def server_name(data_path):
    return 'goottikalenteri-' + hashlib.sha256(str(data_path).encode()).hexdigest()[:24]


def request_mode(name, mode):
    socket = QLocalSocket()
    socket.connectToServer(name)
    if not socket.waitForConnected(2000):
        return False
    socket.write(json.dumps({'mode': mode}).encode() + b'\n')
    socket.flush()
    if not socket.waitForReadyRead(3000):
        return False
    return bytes(socket.readAll()) == b'ok\n'


def start_server(name, owner, callback):
    # Caller must already hold the data lock before removing a stale endpoint.
    QLocalServer.removeServer(name)
    server = QLocalServer(owner)
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    if not server.listen(name):
        raise OSError(server.errorString())

    def accept():
        while server.hasPendingConnections():
            socket = server.nextPendingConnection()
            buffer = bytearray()
            timeout = QTimer(socket)
            timeout.setSingleShot(True)
            timeout.timeout.connect(socket.abort)
            timeout.start(3000)
            socket.disconnected.connect(socket.deleteLater)

            def receive(s=socket, content=buffer, timer=timeout):
                content.extend(bytes(s.readAll()))
                if len(content) > 1024:
                    s.abort()
                    return
                if b'\n' not in content:
                    return
                timer.stop()
                try:
                    mode = json.loads(bytes(content).split(b'\n', 1)[0])['mode']
                    if mode not in ('calendar', 'widget', 'both'):
                        raise ValueError('Invalid launcher mode')
                except (ValueError, KeyError, TypeError):
                    s.abort()
                    return
                callback(mode)
                s.write(b'ok\n')
                s.flush()
                s.disconnectFromServer()
            socket.readyRead.connect(receive)
            if socket.bytesAvailable():
                receive()
    server.newConnection.connect(accept)
    return server
