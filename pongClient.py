# =================================================================================================
# Contributing Authors:	    Kiara Johnson
# Email Addresses:          kdjo267@uky.edu
# Date:                     11/20/2025
# Purpose:                  Implement game logic, receive updates from server, write to server
# Misc:                     <Not Required.  Anything else you might want to include>
# =================================================================================================


import pygame
import tkinter as tk
import sys
import socket
import threading
import json

from assets.code.helperCode import *

clientBuffer = ""       # buffer to hold received updates
# colors
WHITE = (255,255,255)
BG_COLOR = (24, 61, 26)
RED = (255,0,0)
BLUE = (0,0,255)

isPlaying = False       # Boolean used to determine whether to run game loop


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
        return [], clientBuffer  

# This is the main game loop.  For the most part, you will not need to modify this.  The sections
# where you should add to the code are marked.  Feel free to change any part of this project
# to suit your needs.
def playGame(screenWidth:int, screenHeight:int, playerPaddle:str, client:socket.socket) -> None:
    
    global isPlaying    # use previously declared variable instead of creating a new local variable
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
    isPlaying = True

    # game loop
    while isPlaying: 
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
            winText = "Player 1 Wins! " if lScore > 4 else "Player 2 Wins! "
            winColor = RED if lScore > 4 else BLUE
            textSurface = winFont.render(winText, False, winColor, BG_COLOR)
            textRect = textSurface.get_rect()
            textRect.center = ((screenWidth/2), screenHeight/2)
            winMessage = screen.blit(textSurface, textRect)
            isPlaying = False
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

    clock.tick(60)
    winText = "Press the space bar to play again"
    textSurface = winFont.render(winText, False, WHITE, BG_COLOR)
    textRect = textSurface.get_rect()
    textRect.center = ((screenWidth/2), screenHeight/2)
    winMessage = screen.blit(textSurface, textRect)
    while isPlaying == False:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # send signal to server to play again
                    print("Play again")
        # =========================================================================================

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
    
    # Uncomment the line below if you want to play the game without a server to see how it should work
    # the startScreen() function should call playGame with the arguments given to it by the server this is
    # here for demo purposes only
    #playGame(640, 480,"left",socket.socket(socket.AF_INET, socket.SOCK_STREAM))

