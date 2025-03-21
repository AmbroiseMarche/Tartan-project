"""
Rendering functions for the game board and pieces
"""
import pygame
import math
from src.core.piece import Unit, Double, Triple, Quadruple, Hat

def render_board(screen, board, size, highlighted=None, blocked=None):
    """
    Render the game board with pieces and highlights.
    
    Args:
        screen: Pygame screen to render on
        board: Game board object
        size: Size of hexagons
        highlighted: Set of cells to highlight (yellow)
        blocked: Set of cells to display as blocked (dark gray)
    """
    # Clear the screen
    screen.fill((255, 255, 255))
    
    # Use empty set if no blocked cells are specified
    if blocked is None:
        blocked = set()

    # Draw each cell in the board
    for hex_cell in board.complete_hex_board:
        q, r, s = hex_cell.q, hex_cell.r, hex_cell.s
        x = size * (3 / 2 * q) + 400  # Offset to center
        y = size * (math.sqrt(3) * (r + q / 2)) + 300

        # Determine cell background color
        if hex_cell in board.forbidden_cells:
            color = (50, 50, 50)  # Dark gray for forbidden cells
        elif hex_cell in blocked:
            color = (100, 100, 100)  # Medium gray for blocked cells (during split)
        elif highlighted and hex_cell in highlighted:
            color = (255, 255, 0)  # Yellow for highlighted cells
        else:
            color = (200, 200, 200)  # Light gray by default

        # Draw the hexagon
        points = [
            (x + size * math.cos(math.radians(angle)), y + size * math.sin(math.radians(angle)))
            for angle in range(0, 360, 60)
        ]
        pygame.draw.polygon(screen, color, points, 0)
        pygame.draw.polygon(screen, (0, 0, 0), points, 1)  # Black border

        # Check if there are pieces at this position
        if hex_cell in board.pieces:
            piece = board.pieces[hex_cell]
            
            # Handle tuple case (piece, hat)
            if isinstance(piece, tuple):
                immobilized_piece, hat = piece
                
                # Draw the immobilized piece
                piece_color = (255, 0, 0) if immobilized_piece.color == "red" else (0, 0, 255)
                pygame.draw.circle(screen, piece_color, (int(x), int(y)), size // 3)
                
                # Add numeric indicator for stacked pieces
                if isinstance(immobilized_piece, Double):
                    draw_number(screen, x, y, size, "2")
                elif isinstance(immobilized_piece, Triple):
                    draw_number(screen, x, y, size, "3")
                elif isinstance(immobilized_piece, Quadruple):
                    draw_number(screen, x, y, size, "4")
                    
                # Draw the hat on top with a slight offset
                draw_hat(screen, x, y - size // 6, size, hat.color)
            
            # Draw regular piece
            elif not isinstance(piece, Hat):
                piece_color = (255, 0, 0) if piece.color == "red" else (0, 0, 255)
                pygame.draw.circle(screen, piece_color, (int(x), int(y)), size // 3)
                
                # Add numeric indicator for stacked pieces
                if isinstance(piece, Double):
                    draw_number(screen, x, y, size, "2")
                elif isinstance(piece, Triple):
                    draw_number(screen, x, y, size, "3")
                elif isinstance(piece, Quadruple):
                    draw_number(screen, x, y, size, "4")
            # Draw regular hat
            elif isinstance(piece, Hat):
                draw_hat(screen, x, y, size, piece.color)
        
        # Special case for central position (0,0,0) with hats
        if hex_cell.q == 0 and hex_cell.r == 0 and hex_cell.s == 0:
            # Draw red hat if present
            if hasattr(board, 'red_hat') and board.red_hat:
                draw_hat(screen, x - size // 4, y, size, "red")
                
            # Draw blue hat if present
            if hasattr(board, 'blue_hat') and board.blue_hat:
                draw_hat(screen, x + size // 4, y, size, "blue")

    # Update the display
    pygame.display.flip()

def draw_number(screen, x, y, size, number):
    """Draw a number in the center of a piece."""
    font = pygame.font.Font(None, size)
    text = font.render(number, True, (0, 0, 0))
    text_rect = text.get_rect(center=(int(x), int(y)))
    screen.blit(text, text_rect)

def draw_hat(screen, x, y, size, color):
    """Draw a triangular hat."""
    triangle_offset = size // 3
    
    if color == "red":
        triangle_points = [
            (x, y - triangle_offset),
            (x - triangle_offset, y + triangle_offset/2),
            (x + triangle_offset, y + triangle_offset/2),
        ]
        pygame.draw.polygon(screen, (255, 0, 0), triangle_points, 0)
        
    elif color == "blue":
        triangle_points = [
            (x, y - triangle_offset),
            (x - triangle_offset, y + triangle_offset/2),
            (x + triangle_offset, y + triangle_offset/2),
        ]
        pygame.draw.polygon(screen, (0, 0, 255), triangle_points, 0)
        
    # Add a black border
    pygame.draw.polygon(screen, (0, 0, 0), triangle_points, 1)