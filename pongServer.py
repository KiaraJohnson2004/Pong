# =================================================================================================
# Contributing Authors:	    Kiara Johnson
# Email Addresses:          kdjo267@uky.edu
# Date:                     11/19/2025
# Purpose:                  Relays game state updates between clients
# Misc:                     <Not Required.  Anything else you might want to include>
# =================================================================================================

import socket
import threading
import json

# Use this file to write your server logic
# You will need to support at least two clients
# You will need to keep track of where on the screen (x,y coordinates) each paddle is, the score 
# for each player and where the ball is, and relay that to each client
# I suggest you use the sync variable in pongClient.py to determine how out of sync your two
# clients are and take actions to resync the games

clients = []  # list of connected clients
roles = {}
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480

gameInfo = {}
gameInfo['width'] = SCREEN_WIDTH
gameInfo['height'] = SCREEN_HEIGHT

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr}")
    if clients[0] == conn:
        roles[conn] = 'left'
    elif clients[1] == conn:
        roles[conn] = 'right'
    else:
        roles[conn] = 'spectator'
    gameInfo['role'] = roles[conn]
    gameInfoStr = json.dumps(gameInfo)
    while len(clients) < 2:
        continue
    conn.send((gameInfoStr + "\n").encode())
    while True:
        try:
            msg = conn.recv(1024)
            if not msg:  # client disconnected
                break
            # broadcast message to everyone except the sender
            for c in clients:
                if c != conn:
                    c.send(msg)
        except:
            break
    # cleanup after disconnect
    conn.close()
    if conn in clients:
        clients.remove(conn)
    print(f"[DISCONNECTED] {addr}")

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server.bind(("0.0.0.0", 65432))   # listen on all interfaces, port 65432
server.listen()

print("Server listening on port 65432...")

# print current IP for clients to use in command line
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))  
print("IP: " + s.getsockname()[0])
s.close()


while True:
    conn, addr = server.accept()
    clients.append(conn)
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()