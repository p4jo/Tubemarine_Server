import socket

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 6767  # Port to listen on (non-privileged ports are > 1023)

print("started")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:  # `with` ruft close() auf, wenn der Block vorbei ist.
    s.bind((HOST, PORT))
    s.listen()  # make s a listening socket
    print("now listening")
    s.settimeout(3)
    while True:
        try:
            conn, addr = s.accept()  # wait for client to connect
        except socket.timeout:
            print("timeout bei accept")
            continue
        except Exception as e:
            print(e)
        with conn:  # new socket (closes when `with` is over)

            print('Connected by', addr)
            while True:
                data = conn.recv(4)
                if not data:
                    print("received empty data")
                    break
                # conn.sendall(data)
                print("received", data)
