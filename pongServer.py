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
roles = {}    # dictionary mapping socket.socket to string, maps clients to position (left, right, spectator)
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480

gameInfo = {}   # dictionary to send each client the game information needed to run playGame or watchGame
gameInfo['width'] = SCREEN_WIDTH
gameInfo['height'] = SCREEN_HEIGHT

 # =====================================================================
# Author: Kiara Johnson
# Purpose: Handle all communication with connected clients, receive
#          game updates, and broadcast them to the correct players or
#          spectators based on the grouping.
# Pre:  Server socket must be established.
# Post: Processes messages, updates shared game state, and relays updates
#       to the appropriate clients. Removes the client if it disconnects.
# =====================================================================
def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr}")
    if clients[0] == conn:              # first client uses left paddle
        roles[conn] = 'left'
    elif clients[1] == conn:            # second client uses right paddle
        roles[conn] = 'right'
    else:
        roles[conn] = 'spectator'       # all other clients are spectators
    gameInfo['role'] = roles[conn]
    gameInfoStr = json.dumps(gameInfo)  # stringifies gameInfo dictionary to be sent
    while len(clients) < 2:             # don't send game information until there are enough players
        continue
    conn.send((gameInfoStr + "\n").encode())    # add newline to prevent json extra data error
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
    conn, addr = server.accept()    # accept new client
    clients.append(conn)            # add new client to list of clients
    thread = threading.Thread(target=handle_client, args=(conn, addr))  # use threads to handle multiple clients
    thread.start()