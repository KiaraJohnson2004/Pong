# =================================================================================================
# Contributing Authors:	    Kiara Johnson, Andy Zheng, Owen Louis
# Email Addresses:          kdjo267@uky.edu, azh242@uky.edu, omlo227@uky.edu
# Date:                     11/25/2025
# Purpose:                  Implement game logic, receive updates from server, write to server
# Misc:                     <Not Required.  Anything else you might want to include>
# =================================================================================================


import pygame
import tkinter as tk
import sys
import socket
import json
from enum import Enum

class State(Enum):
    INITIAL = 0
    PLAYING = 1
    WIN = 2
    REMATCH = 3

from assets.code.helperCode import *

clientBuffer = ""       # buffer to hold received updates
# colors
WHITE = (255,255,255)
BG_COLOR = (24, 61, 26)
RED = (255,0,0)
BLUE = (0,0,255)

curState = State.INITIAL



# =====================================================================
# Author: Kiara Johnson
# Purpose: Read any available messages from the server, assemble them
#          using a buffer, and return complete newline-terminated JSON
#          messages to the caller.
# Pre: The client socket must be connected and set to non-blocking mode.
#      The buffer string passed in must contain any previously incomplete data.
# Post: Returns a list of fully assembled messages and an updated buffer.
#       Does not modify any global game state.
# =====================================================================
def checkServer(client: socket.socket, buffer: str) -> tuple[list[str], str]:
    try:                                    # try to receive data from server
        data = client.recv(4096).decode()       
        if not data:
            return [], buffer  

        buffer += data                      # add new update to buffer
        updates = []

        while "\n" in buffer:
            msg, buffer = buffer.split("\n", 1)
            if msg.strip():
                updates.append(msg)

        return updates, buffer

    except BlockingIOError:
        return [], buffer  

# =====================================================================
# Author: Andy Zheng
# Purpose: Display a screen showing the player which side they've been 
#          assigned to. Waits for server signal that both players are 
#          connected before starting countdown.
# Pre: The client socket must be connected. Role must be "left", "right",
#      or "spectator". The tk app window must exist.
# Post: Displays role assignment screen, waits for start signal from 
#       server, shows 3-second countdown, then closes window to begin game.
# =====================================================================

def showRoleScreen(role: str, app: tk.Tk, client: socket.socket) -> None:
    # Create new window for role display
    roleWindow = tk.Toplevel(app)
    roleWindow.title("Player Assignment")
    roleWindow.geometry("400x300")
    
    # Role-specific colors and text
    if role == "left":
        bg_color = "#ffcccc"  # Light red
        role_text = "You are Player 1 (LEFT)"
        color_text = "RED Paddle"
        controls = "Controls: W/UP (move up), S/DOWN (move down)"
    elif role == "right":
        bg_color = "#ccccff"  # Light blue
        role_text = "You are Player 2 (RIGHT)"
        color_text = "BLUE Paddle"
        controls = "Controls: W/UP (move up), S/DOWN (move down)"
    else:  # spectator
        bg_color = "#f0f0f0"  # Light gray
        role_text = "You are a SPECTATOR"
        color_text = "Watch the game!"
        controls = "Enjoy the match!"
    
    roleWindow.configure(bg=bg_color)
    
    # Title label
    titleLabel = tk.Label(
        roleWindow, 
        text=role_text,
        font=("Arial", 24, "bold"),
        bg=bg_color,
        fg="black"
    )
    titleLabel.pack(pady=20)
    
    # Color/role description
    colorLabel = tk.Label(
        roleWindow,
        text=color_text,
        font=("Arial", 16),
        bg=bg_color,
        fg="black"
    ) 
    colorLabel.pack(pady=10)
    
    # Controls text
    controlsLabel = tk.Label(
        roleWindow,
        text=controls,
        font=("Arial", 12),
        bg=bg_color,
        fg="black"
    )
    controlsLabel.pack(pady=10)
    
    # Waiting message
    waitLabel = tk.Label(
        roleWindow,
        text="Waiting for other player to connect...",
        font=("Arial", 10, "italic"),
        bg=bg_color,
        fg="gray"
    )
    waitLabel.pack(pady=20)
    
    # Countdown label (hidden initially)
    countdownLabel = tk.Label(
        roleWindow,
        text="",
        font=("Arial", 16, "bold"),
        bg=bg_color,
        fg="black"
    )
    countdownLabel.pack(pady=10)
    
    # Update the window
    roleWindow.update()
    
    # Function to check for server start signal
    def check_for_start():
        try:
            data = client.recv(1024).decode()
            if data:
                msg = json.loads(data.strip())
                if 'start_game' in msg and msg['start_game']:
                    # Both players connected, start countdown
                    waitLabel.config(text="Both players connected!")
                    countdown(3)
                    return
        except BlockingIOError:
            pass
        except:
            pass
        
        # Check again in 100ms
        roleWindow.after(100, check_for_start)
    
    # Countdown function
    def countdown(seconds):
        if seconds > 0:
            countdownLabel.config(text=f"Starting in {seconds}...")
            roleWindow.after(1000, lambda: countdown(seconds - 1))
        else:
            countdownLabel.config(text="GO!")
            roleWindow.after(500, roleWindow.destroy)
    
    # Start checking for server signal
    check_for_start()
    
    # Keep window open until countdown finishes
    roleWindow.wait_window()

# This is the main game loop.  For the most part, you will not need to modify this.  The sections
# where you should add to the code are marked.  Feel free to change any part of this project
# to suit your needs.
# =====================================================================
# Author: Kiara Johnson
# Purpose: Run one full game instance through handling of user input,
#          performance of game logic, state transition, and display of
#          output.
# Pre:     The client socket must be connected and non-blocking.
#          screenWidth and screenHeight must match the server-provided
#          dimensions. playerPaddle must be "left" or "right".
# Post:    Sends continuous game state updates to the server.
#          Returns only when the user quits the window.   
# =====================================================================

def playGame(screenWidth:int, screenHeight:int, playerPaddle:str, client:socket.socket) -> None:
    
    clientBuffer = ""   # buffer used for checking server
    # Pygame inits
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()

    # Constants
    clock = pygame.time.Clock()
    scoreFont = pygame.font.Font("./assets/fonts/pong-score.ttf", 32)
    winFont = pygame.font.Font("./assets/fonts/visitor.ttf", 48)
    pointSound = pygame.mixer.Sound("./assets/sounds/point.wav")
    bounceSound = pygame.mixer.Sound("./assets/sounds/bounce.wav")

    # Display objects
    screen = pygame.display.set_mode((screenWidth, screenHeight))
    winMessage = pygame.Rect(0,0,0,0)
    topWall = pygame.Rect(-10,0,screenWidth+20, 10)
    bottomWall = pygame.Rect(-10, screenHeight-10, screenWidth+20, 10)
    centerLine = []
    for i in range(0, screenHeight, 10):
        centerLine.append(pygame.Rect((screenWidth/2)-5,i,5,5))

    # Paddle properties and init
    paddleHeight = 50
    paddleWidth = 10
    paddleStartPosY = (screenHeight/2)-(paddleHeight/2)
    leftPaddle = Paddle(pygame.Rect(10,paddleStartPosY, paddleWidth, paddleHeight))
    rightPaddle = Paddle(pygame.Rect(screenWidth-20, paddleStartPosY, paddleWidth, paddleHeight))

    ball = Ball(pygame.Rect(screenWidth/2, screenHeight/2, 5, 5), -5, 0)

    if playerPaddle == "left":
        opponentPaddleObj = rightPaddle
        playerPaddleObj = leftPaddle
    else:
        opponentPaddleObj = leftPaddle
        playerPaddleObj = rightPaddle

    # game state information
    lScore = 0
    rScore = 0
    sync = 0
    gameState = {}
    requestSent = False
    curState = State.PLAYING

    while True:
        # game loop
        if curState == State.PLAYING: 
            # Wiping the screen
            screen.fill(BG_COLOR)

            # Getting keypress events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        playerPaddleObj.moving = "down"

                    elif event.key == pygame.K_UP or event.key == pygame.K_w:
                        playerPaddleObj.moving = "up"

                elif event.type == pygame.KEYUP:
                    playerPaddleObj.moving = ""

            # =========================================================================================
            # Get updates from server
            updates, clientBuffer = checkServer(client, clientBuffer)
            for newGameState in updates:
                newStateJSON = json.loads(newGameState)

                # parse received information
                oppBallX = newStateJSON['ballX']
                oppBallY = newStateJSON['ballY']
                oppX = newStateJSON['paddleX']
                oppY = newStateJSON['paddleY']
                oppLscore = newStateJSON['lScore']
                oppRScore = newStateJSON['rScore']
                oppSync = newStateJSON['sync']

                # update opponent's paddle coordinates regardless of sync
                opponentPaddleObj.rect.x = oppX
                opponentPaddleObj.rect.y = oppY

                # update ball position, scores, and sync only if received sync is greater than client's sync
                if oppSync > sync:
                    ball.rect.x = oppBallX
                    ball.rect.y = oppBallY
                    lScore = oppLscore
                    rScore = oppRScore
                    sync = oppSync
            # =========================================================================================

            # Update the player paddle and opponent paddle's location on the screen
            for paddle in [playerPaddleObj, opponentPaddleObj]:
                if paddle.moving == "down":
                    if paddle.rect.bottomleft[1] < screenHeight-10:
                        paddle.rect.y += paddle.speed
                elif paddle.moving == "up":
                    if paddle.rect.topleft[1] > 10:
                        paddle.rect.y -= paddle.speed

            # If the game is over, display the win message
            if lScore > 4 or rScore > 4:
                curState = State.WIN

            else:

                # ==== Ball Logic =====================================================================
                ball.updatePos()

                # If the ball makes it past the edge of the screen, update score, etc.
                if ball.rect.x > screenWidth:
                    lScore += 1
                    pointSound.play()
                    ball.reset(nowGoing="left")
                elif ball.rect.x < 0:
                    rScore += 1
                    pointSound.play()
                    ball.reset(nowGoing="right")
                
                # If the ball hits a paddle
                if ball.rect.colliderect(playerPaddleObj.rect):
                    bounceSound.play()
                    ball.hitPaddle(playerPaddleObj.rect.center[1])
                elif ball.rect.colliderect(opponentPaddleObj.rect):
                    bounceSound.play()
                    ball.hitPaddle(opponentPaddleObj.rect.center[1])
                
                # If the ball hits a wall
                if ball.rect.colliderect(topWall) or ball.rect.colliderect(bottomWall):
                    bounceSound.play()
                    ball.hitWall()
            
                
                # ==== End Ball Logic =================================================================
            # Drawing
            pygame.draw.rect(screen, WHITE, ball)
            # Drawing the dotted line in the center
            for i in centerLine:
                pygame.draw.rect(screen, WHITE, i)
        
            # Drawing the player's new location
            pygame.draw.rect(screen, RED, leftPaddle)
            pygame.draw.rect(screen, BLUE, rightPaddle)

            pygame.draw.rect(screen, WHITE, topWall)
            pygame.draw.rect(screen, WHITE, bottomWall)
            scoreRect = updateScore(lScore, rScore, screen, WHITE, scoreFont)
            #pygame.display.update([topWall, bottomWall, ball, leftPaddle, rightPaddle, scoreRect, winMessage])
            pygame.display.flip()

            clock.tick(60)
        
            # This number should be synchronized between you and your opponent.  If your number is larger
            # then you are ahead of them in time, if theirs is larger, they are ahead of you, and you need to
            # catch up (use their info)
            sync += 1
            # =========================================================================================
            # Send your server update here at the end of the game loop to sync your game with your
            # opponent's game

            # pack game state information into a dictionary
            gameState['ballX'] = ball.rect.x
            gameState['ballY'] = ball.rect.y
            gameState['paddleX'] = playerPaddleObj.rect.x
            gameState['paddleY'] = playerPaddleObj.rect.y
            gameState['lScore'] = lScore
            gameState['rScore'] = rScore
            gameState['role'] = playerPaddle
            gameState['sync'] = sync
            gameStateStr = json.dumps(gameState)    # stringify dictionary and send to server
            client.send((gameStateStr + "\n").encode())

        elif curState == State.WIN:
            pygame.draw.rect(screen, WHITE, ball)
            # Drawing the dotted line in the center
            for i in centerLine:
                pygame.draw.rect(screen, WHITE, i)
        
            # Drawing the player's new location
            pygame.draw.rect(screen, RED, leftPaddle)
            pygame.draw.rect(screen, BLUE, rightPaddle)

            pygame.draw.rect(screen, WHITE, topWall)
            pygame.draw.rect(screen, WHITE, bottomWall)
            scoreRect = updateScore(lScore, rScore, screen, WHITE, scoreFont)
            winText = "Player 1 Wins! " if lScore > 4 else "Player 2 Wins! "
            winColor = RED if lScore > 4 else BLUE
            textSurface = winFont.render(winText, False, winColor, BG_COLOR)
            textRect = textSurface.get_rect()
            textRect.center = ((screenWidth/2), screenHeight/2)
            winMessage = screen.blit(textSurface, textRect)
            pygame.display.flip()
            pygame.time.wait(3000)
            curState = State.REMATCH
            clock.tick(60)

        elif curState == State.REMATCH:
             # Drawing
            pygame.draw.rect(screen, WHITE, ball)
            # Drawing the dotted line in the center
            for i in centerLine:
                pygame.draw.rect(screen, WHITE, i)
        
            # Drawing the player's new location
            pygame.draw.rect(screen, RED, leftPaddle)
            pygame.draw.rect(screen, BLUE, rightPaddle)

            pygame.draw.rect(screen, WHITE, topWall)
            pygame.draw.rect(screen, WHITE, bottomWall)
            scoreRect = updateScore(lScore, rScore, screen, WHITE, scoreFont)
            winText = "Press space to play again"
            textSurface = winFont.render(winText, False, WHITE, BG_COLOR)
            textRect = textSurface.get_rect()
            textRect.center = ((screenWidth/2), screenHeight/2)
            winMessage = screen.blit(textSurface, textRect)
            pygame.display.flip()

            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and requestSent == False:
                        # send signal to server to play again
                        rematchRequest = {}
                        rematchRequest['rematch'] = True
                        rematchRequest['role'] = playerPaddle
                        rematchStr = json.dumps(rematchRequest)
                        client.send((rematchStr + "\n").encode())
                        requestSent = True
            if requestSent:
                updates, clientBuffer = checkServer(client, clientBuffer)

                for rematchInfo in updates:
                    rematchJSON = json.loads(rematchInfo)
                    if 'rematch' in rematchJSON and rematchJSON['rematch']:
                        lScore = 0
                        rScore = 0
                        sync = 0
                        gameState = {}
                        ball.reset("left")
                        opponentPaddleObj.rect.y = paddleStartPosY
                        playerPaddleObj.rect.y = paddleStartPosY
                        curState = State.PLAYING
                        requestSent = False
                        break   # break out of the for loop
            clock.tick(60)

                   


# =====================================================================
# Author: Kiara Johnson
# Purpose: Run a spectator view of the Pong game, receiving updates from
#          the server and rendering the current game state without
#          sending any inputs back.
# Pre:  Client socket must be connected.
# Post: Continuously displays the latest server game state until the user
#       closes the window, then exits the program.
# =====================================================================
def watchGame(screenWidth:int, screenHeight:int, client:socket.socket) -> None:
    
    clientBuffer = ""   # buffer for checking server
    # Pygame inits
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()

    # Constants
    
    clock = pygame.time.Clock()
    scoreFont = pygame.font.Font("./assets/fonts/pong-score.ttf", 32)
    winFont = pygame.font.Font("./assets/fonts/visitor.ttf", 48)
    pointSound = pygame.mixer.Sound("./assets/sounds/point.wav")
    bounceSound = pygame.mixer.Sound("./assets/sounds/bounce.wav")

    # Display objects
    screen = pygame.display.set_mode((screenWidth, screenHeight))
    winMessage = pygame.Rect(0,0,0,0)
    topWall = pygame.Rect(-10,0,screenWidth+20, 10)
    bottomWall = pygame.Rect(-10, screenHeight-10, screenWidth+20, 10)
    centerLine = []
    for i in range(0, screenHeight, 10):
        centerLine.append(pygame.Rect((screenWidth/2)-5,i,5,5))

    # Paddle properties and init
    paddleHeight = 50
    paddleWidth = 10
    paddleStartPosY = (screenHeight/2)-(paddleHeight/2)
    leftPaddle = Paddle(pygame.Rect(10,paddleStartPosY, paddleWidth, paddleHeight))
    rightPaddle = Paddle(pygame.Rect(screenWidth-20, paddleStartPosY, paddleWidth, paddleHeight))

    ball = Ball(pygame.Rect(screenWidth/2, screenHeight/2, 5, 5), -5, 0)

    # game state information
    lScore = 0
    rScore = 0
    sync = 0    # used to ensure client is up-to-date, won't be sent to server
    

    while True:
        # Wiping the screen
        screen.fill(BG_COLOR)

        # Getting keypress events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()


        # =========================================================================================
        # Get updates from server
        updates, clientBuffer = checkServer(client, clientBuffer)  # get an update from the server
        for newGameState in updates:
            newStateJSON = json.loads(newGameState)
            # new game starting
            if 'rematch' in newStateJSON and newStateJSON['rematch']:
                lScore = 0
                rScore = 0
                sync = 0
                gameState = {}
                ball.reset("left")
                leftPaddle.rect.y = paddleStartPosY
                rightPaddle.rect.y = paddleStartPosY

            # update for existing game
            else:
                # parse received information
                ballX = newStateJSON['ballX']
                ballY = newStateJSON['ballY']
                paddleX = newStateJSON['paddleX']
                paddleY = newStateJSON['paddleY']
                newLscore = newStateJSON['lScore']
                newRScore = newStateJSON['rScore']
                newSync = newStateJSON['sync']
                side = newStateJSON['role']

                # update paddle coordinates regardless of sync
                if side == 'left':
                    leftPaddle.rect.x = paddleX
                    leftPaddle.rect.y = paddleY
                elif side == 'right':
                    rightPaddle.rect.x = paddleX
                    rightPaddle.rect.y = paddleY

                # update ball coordinates, score, and sync only if received sync is greater than client's sync
                if newSync > sync:
                    ball.rect.x = ballX
                    ball.rect.y = ballY
                    lScore = newLscore
                    rScore = newRScore
                    sync = newSync
        # =========================================================================================


        # If the game is over, display the win message
        if lScore > 4 or rScore > 4:
            winText = "Player 1 Wins! " if lScore > 4 else "Player 2 Wins! "
            winColor = RED if lScore > 4 else BLUE
            textSurface = winFont.render(winText, False, winColor, BG_COLOR)
            textRect = textSurface.get_rect()
            textRect.center = ((screenWidth/2), screenHeight/2)
            winMessage = screen.blit(textSurface, textRect)

        else:

            # ==== Ball Logic =====================================================================
            ball.updatePos()

            # If the ball makes it past the edge of the screen, update score, etc.
            if ball.rect.x > screenWidth:
                lScore += 1
                pointSound.play()
                ball.reset(nowGoing="left")
            elif ball.rect.x < 0:
                rScore += 1
                pointSound.play()
                ball.reset(nowGoing="right")
                
            # If the ball hits a paddle
            if ball.rect.colliderect(leftPaddle.rect):
                bounceSound.play()
                ball.hitPaddle(leftPaddle.rect.center[1])
            elif ball.rect.colliderect(rightPaddle.rect):
                bounceSound.play()
                ball.hitPaddle(rightPaddle.rect.center[1])
                
            # If the ball hits a wall
            if ball.rect.colliderect(topWall) or ball.rect.colliderect(bottomWall):
                bounceSound.play()
                ball.hitWall()
            
            pygame.draw.rect(screen, WHITE, ball)
            # ==== End Ball Logic =================================================================

        # Drawing the dotted line in the center
        for i in centerLine:
            pygame.draw.rect(screen, WHITE, i)
        
        # Drawing the player's new location
        pygame.draw.rect(screen, RED, leftPaddle)
        pygame.draw.rect(screen, BLUE, rightPaddle)
            

        pygame.draw.rect(screen, WHITE, topWall)
        pygame.draw.rect(screen, WHITE, bottomWall)
        scoreRect = updateScore(lScore, rScore, screen, WHITE, scoreFont)
        #pygame.display.update([topWall, bottomWall, ball, leftPaddle, rightPaddle, scoreRect, winMessage])
        pygame.display.flip()

        clock.tick(60)
        




# This is where you will connect to the server to get the info required to call the game loop.  Mainly
# the screen width, height and player paddle (either "left" or "right")
# If you want to hard code the screen's dimensions into the code, that's fine, but you will need to know
# which client is which
def joinServer(ip:str, port:str, errorLabel:tk.Label, app:tk.Tk) -> None:
    # Purpose:      This method is fired when the join button is clicked
    # Arguments:
    # ip            A string holding the IP address of the server
    # port          A string holding the port the server is using
    # errorLabel    A tk label widget, modify it's text to display messages to the user (example below)
    # app           The tk window object, needed to kill the window
    
    
    # Create a socket and connect to the server
    # You don't have to use SOCK_STREAM, use what you think is best
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((ip, int(port)))
    # Get the required information from your server (screen width, height & player paddle, "left or "right)
    jsonData = client.recv(1024).decode()
    data = json.loads(jsonData)
    screenWidth = data['width']
    screenHeight = data['height']
    position = data['role']

    # Show the role assignment beofre going into the game
    showRoleScreen(position, app, client)

    client.setblocking(False)
    # If you have messages you'd like to show the user use the errorLabel widget like so
    #errorLabel.config(text=f"You input: IP: {ip}, Port: {port}")
    # You may or may not need to call this, depending on how many times you update the label
    #errorLabel.update()     

    # Close this window and start the game with the info passed to you from the server
    app.withdraw()     # Hides the window (we'll kill it later)
    if (position == 'left' or position == 'right'):
        playGame(screenWidth, screenHeight, position, client)  # User will be either left or right paddle
    else:
        watchGame(screenWidth, screenHeight, client)           # User will watch the game
    app.quit()         # Kills the window


# This displays the opening screen, you don't need to edit this (but may if you like)
def startScreen() -> None:
    app = tk.Tk()
    app.title("Server Info")

    image = tk.PhotoImage(file="./assets/images/logo.png")

    titleLabel = tk.Label(image=image)
    titleLabel.grid(column=0, row=0, columnspan=2)

    ipLabel = tk.Label(text="Server IP:")
    ipLabel.grid(column=0, row=1, sticky="W", padx=8)

    ipEntry = tk.Entry(app)
    ipEntry.grid(column=1, row=1)

    portLabel = tk.Label(text="Server Port:")
    portLabel.grid(column=0, row=2, sticky="W", padx=8)

    portEntry = tk.Entry(app)
    portEntry.grid(column=1, row=2)

    errorLabel = tk.Label(text="")
    errorLabel.grid(column=0, row=4, columnspan=2)

    joinButton = tk.Button(text="Join", command=lambda: joinServer(ipEntry.get(), portEntry.get(), errorLabel, app))
    joinButton.grid(column=0, row=3, columnspan=2)

    app.mainloop()

if __name__ == "__main__":
    startScreen()
    

