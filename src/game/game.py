"""
Main game class - Coordinates the game flow and states
"""
import pygame
from src.core.board import Board
from src.core.player import Player
from src.game.placement_phase import placement_phase
from src.game.game_phase import game_phase, initialize_preset_configuration

class Game:
    def __init__(self, screen_size=(800, 600)):
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode(screen_size)
        pygame.display.set_caption("Hexagonal Game")
        self.clock = pygame.time.Clock()
        
        # Game components
        self.board = Board()
        self.players = [
            Player(color="red", name="Player 1"),
            Player(color="blue", name="Player 2")
        ]
        
    def run(self, skip_placement=False):
        """
        Run the complete game flow.
        
        Args:
            skip_placement: If True, skip the placement phase and use a preset configuration
        """
        if skip_placement:
            # Skip placement and use a preset configuration
            initialize_preset_configuration(self.board, self.players[0], self.players[1])
            placement_complete = True
        else:
            # Run the placement phase
            placement_complete = placement_phase(self.screen, self.board, self.players)
        
        if placement_complete:
            # Run the main game phase
            game_complete = game_phase(self.screen, self.board, self.players)
            
        # Clean up
        pygame.quit()
        
    def quit(self):
        """Clean up and exit the game."""
        pygame.quit()