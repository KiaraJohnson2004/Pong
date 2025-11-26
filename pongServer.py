# =================================================================================================
# Contributing Authors:	    Kiara Johnson, Andy Zheng
# Email Addresses:          kdjo267@uky.edu, azh242@uky.edu
# Date:                     11/25/2025
# Purpose:                  Relays game state updates between clients
# Misc:                     <Not Required.  Anything else you might want to include>
# =================================================================================================

import socket
import threading
import json
import time

# Use this file to write your server logic
# You will need to support at least two clients
# You will need to keep track of where on the screen (x,y coordinates) each paddle is, the score 
# for each player and where the ball is, and relay that to each client
# I suggest you use the sync variable in pongClient.py to determine how out of sync your two
# clients are and take actions to resync the games

clients = []  # list of connected clients
roles = {}    # dictionary mapping socket.socket to string, maps clients to position (left, right, spectator)
rematchRequests = {'left': False, 'right': False}
bothPlayersConnected = False # Track when both players have joined
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480

gameInfo = {}   # dictionary to send each client the game information needed to run playGame or watchGame
gameInfo['width'] = SCREEN_WIDTH
gameInfo['height'] = SCREEN_HEIGHT

 # =====================================================================
# Author: Kiara Johnson, Andy Zheng
# Purpose: Handle all communication with connected clients, receive
#          game updates, and broadcast them to the correct players or
#          spectators based on the grouping.
# Pre:  Server socket must be established.
# Post: Processes messages, updates shared game state, and relays updates
#       to the appropriate clients. Removes the client if it disconnects.
# =====================================================================
def handle_client(conn, addr):
    global bothPlayersConnected

    print(f"[NEW CONNECTION] {addr}")
    if clients[0] == conn:              # first client uses left paddle
        roles[conn] = 'left'
    elif clients[1] == conn:            # second client uses right paddle
        roles[conn] = 'right'
        bothPlayersConnected = True
    else:
        roles[conn] = 'spectator'       # all other clients are spectators
    gameInfo['role'] = roles[conn]
    gameInfoStr = json.dumps(gameInfo)  # stringifies gameInfo dictionary to be sent
    conn.send((gameInfoStr + "\n").encode())
    while not bothPlayersConnected:
        time.sleep(0.1)
     # Send start signal to begin countdown
    startSignal = json.dumps({"start_game": True}) + "\n"
    conn.send(startSignal.encode())
    
    # Wait 3 seconds for countdown on client side
    time.sleep(3.5)
    while True:
        # receive messages from clients
        try:
            raw = conn.recv(1024)
            if not raw:
                break
        
            try:
                data = json.loads(raw.decode().strip())
            except:
                continue

            # player wants to play again
            if 'rematch' in data:
                playerRole = roles[conn]

                # record their request
                rematchRequests[playerRole] = True

                # wait until both players want to play again
                if rematchRequests['left'] and rematchRequests['right']:
                
                    # send approval to both
                    approval = json.dumps({"rematch": True}) + "\n"
                    for c in clients:
                        c.send(approval.encode())

                    # reset flags for next round
                    rematchRequests['left'] = False
                    rematchRequests['right'] = False

                continue

            else:
                # game update
                for c in clients:
                    if c != conn:
                        c.send((json.dumps(data) + "\n").encode())

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

print("Server listening on port 65432 ...")

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