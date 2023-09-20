import socket


def validate_host_and_port(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        if result != 0:
            raise Exception(f"Port: {port} is not open on the host: {host}")

    except socket.gaierror as e:
        sock.close()
        raise Exception(f"{host}: {str(e)}")
    finally:
        sock.close()
