"""
Human Player class - Handles user inputs for game actions
"""
import pygame
from src.core.player import Player
from src.core.hexagon import Hexagon

class HumanPlayer(Player):
    def __init__(self, color, name=None):
        super().__init__(color, name or f"Human ({color})")
    
    def choose_action(self, board, game_state, screen):
        """
        Wait for the player to select an action using mouse clicks.
        
        Args:
            board: The game board
            game_state: Current state of the game
            screen: Pygame screen for event handling
            
        Returns:
            The selected action or None if no valid action was chosen
        """
        waiting_for_action = True
        action = None
        size = 40  # Hexagon size
        
        while waiting_for_action:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None  # Signal to exit game
                
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
                    # Convert mouse position to hex coordinates
                    x, y = event.pos
                    q, r, s = board.pixel_to_hex(x - 400, y - 300, size)
                    clicked_hex = Hexagon(q, r, s)
                    
                    # Check if the click is on a valid action
                    if clicked_hex in game_state.possible_actions:
                        action = clicked_hex
                        waiting_for_action = False
            
            pygame.time.Clock().tick(30)  # Cap at 30 FPS
        
        return action