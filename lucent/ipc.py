"""One running Lucent, controllable from the command line.

`lucent --toggle-click-through` talks to the running instance. That is the
portable answer to "global shortcut" on Wayland: bind that command to a key in
your desktop's keyboard settings. Launching `lucent file.pdf` while Lucent is
already running opens the file in the existing instance.
"""
from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

SERVER_NAME = "lucent-ipc-v1"


def send(lines, timeout_ms: int = 400) -> bool:
    """Deliver commands to a running instance. False if none is running."""
    sock = QLocalSocket()
    sock.connectToServer(SERVER_NAME)
    if not sock.waitForConnected(timeout_ms):
        return False
    sock.write(("\n".join(lines) + "\n").encode("utf-8"))
    sock.flush()
    sock.waitForBytesWritten(timeout_ms)
    sock.disconnectFromServer()
    from PySide6.QtCore import QCoreApplication
    if QCoreApplication.instance():
        QCoreApplication.processEvents()
    return True




class Server(QObject):
    command = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server = QLocalServer(self)
        QLocalServer.removeServer(SERVER_NAME)   # clears a stale socket after a crash
        self.ok = self._server.listen(SERVER_NAME)
        self._server.newConnection.connect(self._on_connection)

    def _on_connection(self):
        while self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            sock.readyRead.connect(lambda s=sock: self._read(s))
            sock.disconnected.connect(sock.deleteLater)
            if sock.bytesAvailable():
                self._read(sock)

    def _read(self, sock):
        for line in bytes(sock.readAll()).decode("utf-8", errors="replace").splitlines():
            if line.strip():
                self.command.emit(line.strip())
