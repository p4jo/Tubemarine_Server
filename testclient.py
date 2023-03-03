import socket, sys


class MySocket:
    """demonstration class only
      - coded for clarity, not efficiency
    """
    sock = None

    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock

    def connect(self, host, port):
        self.sock.connect((host, port))

    def mysend(self, msg):
        global MSGLEN
        totalsent = 0
        MSGLEN = len(msg)
        while totalsent < MSGLEN:
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent

    def myreceive(self, MSGLEN=100):
        chunks = []
        bytes_recd = 0
        while bytes_recd < MSGLEN:
            chunk = self.sock.recv(min(MSGLEN - bytes_recd, 2048))
            if chunk == b'':
                raise RuntimeError("socket connection broken")
            chunks.append(chunk)
            print(chunk)
            bytes_recd += len(chunk)
        return b''.join(chunks)


a = MySocket()
# a.sock.timeout = 1
print((sys.argv[1] if len(sys.argv) > 1 else "localhost"))
a.connect((sys.argv[1] if len(sys.argv) > 1 else "localhost"), 6767)
print("connected")
# a.connect("johannes-dektop", 6776)
a.mysend(bytes((sys.argv[2] if len(sys.argv) > 2 else "test"), "utf-8"))
print("sent")
# a.sock.
# print(a.myreceive())
