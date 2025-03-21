"""
Placement Phase - Initial game phase where players place their units
"""
import pygame
import math
from src.core.board import Board
from src.core.player import Player
from src.core.piece import Unit, Hat
from src.core.hexagon import Hexagon
from src.ui.rendering import render_board

def placement_phase(screen, board, players):
    """Run the placement phase of the game."""
    player_index = 0  # Current player index
    size = 40  # Hexagon size
    
    while True:
        # Get available cells for placement
        available_cells = [
            hex_cell for hex_cell in board.complete_hex_board
            if hex_cell not in board.pieces
            and hex_cell not in board.forbidden_cells
            and not board.is_adjacent(hex_cell)
        ]
        
        # Check if placement phase is complete
        if not available_cells:
            # Place the hats in the center after placement phase
            center = Hexagon(0, 0, 0)
            red_hat = Hat("red", center)
            blue_hat = Hat("blue", center)
            
            # Store both hats directly in board attributes
            board.red_hat = red_hat
            board.blue_hat = blue_hat
            
            print("Placement phase complete, added hats at center")
            return True  # Placement phase complete
            
        # Display board with available cells highlighted
        render_board(screen, board, size, highlighted=available_cells)
        
        # Display current player info
        font = pygame.font.Font(None, 30)
        player = players[player_index]
        text = font.render(f"{player.name}'s turn ({player.color})", True, (0, 0, 0))
        screen.blit(text, (10, 10))
        pygame.display.flip()
        
        # Wait for a player action
        action_taken = False
        while not action_taken:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False  # Quit game
                    
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
                    x, y = event.pos
                    q, r, s = board.pixel_to_hex(x - 400, y - 300, size)
                    clicked_hex = Hexagon(q, r, s)
                    
                    if clicked_hex in available_cells:
                        player = players[player_index]
                        if player.place_piece(Unit, clicked_hex, board):
                            player_index = 1 - player_index  # Alternate between players
                            action_taken = True
            
            pygame.time.Clock().tick(30)  # Cap at 30 FPS
    
    return True  # Placement phase complete