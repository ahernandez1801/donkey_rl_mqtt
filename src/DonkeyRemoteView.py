from __future__ import print_function, with_statement, division
import os

import zmq
import pygame
from pygame.locals import *



TELEOP_RATE = 1 / 60 

class pygameScreen():
    def __init__(self, window, control_speed, control_angle):
    	self.control_speed = control_speed
    	self.control_angle = control_angle
    	self.updateScreen = self.updateScreen()
    	
    def pygameMain():
        # Pygame require a window
        pygame.init()
        window = pygame.display.set_mode((800, 500), RESIZABLE)
        pygame.font.init()
        font = pygame.font.SysFont('Open Sans', 25)
        small_font = pygame.font.SysFont('Open Sans', 20)
        end = False

    def writeText(self, screen, text, x, y, font, color=(62, 107, 153)):
        text = str(text)
        text = font.render(text, True, color)
        screen.blit(text, (x, y))

    def clear(self):
        self.window.fill((0, 0, 0))

    def updateScreen(self, window, speed, turn):
        clear()
        writeText(window, 'Linear: {:.2f}, Angular: {:.2f}'.format(speed, turn), 20, 0, font, (255, 255, 255))
        help_str = 'Use arrow keys to move, q or ESCAPE to exit.'
        writeText(window, help_str, 20, 50, small_font)
        help_2 = 'space key, k : force stop ---  anything else : stop smoothly'
        writeText(window, help_2, 20, 100, small_font)

        control_speed, control_turn = 0, 0
        updateScreen(window, control_speed, control_turn)

    def updateWindow(control_speed, control_angle):
        x, theta = 0, 0

        updateScreen(window, control_speed, control_angle)

        for event in pygame.event.get():
            if event.type == QUIT or event.type == KEYDOWN and event.key in [K_ESCAPE, K_q]:
                end = True
            pygame.display.flip()
            # Limit FPS
            pygame.time.Clock().tick(1 / TELEOP_RATE)
