"""
Board class - Represents the hexagonal game board
"""
from src.core.hexagon import Hexagon
from src.core.piece import Hat

import math

class Board:
    def __init__(self):
        # Initialize inner cells
        inner_cells = set({Hexagon(q, r, -q-r) for q in range(-3, 4) for r in range(-3, 4) if -q-r in range(-3, 4)})
        
        # Initialize outer cells
        outer_cells = {
            Hexagon(-4, 1, 3), Hexagon(-4, 2, 2), Hexagon(-3, 4, -1), Hexagon(-2, 4, -2),
            Hexagon(1, 3, -4), Hexagon(2, 2, -4), Hexagon(4, -1, -3), Hexagon(4, -2, -2),
            Hexagon(3, -4, 1), Hexagon(2, -4, 2), Hexagon(-1, -3, 4), Hexagon(-2, -2, 4)
        }
        
        self.complete_hex_board = inner_cells.union(outer_cells)
        
        # Initialize forbidden cells (dark cells)
        self.forbidden_cells = {
            Hexagon(0, 0, 0), Hexagon(3, -1, -2), Hexagon(1, 2, -3),
            Hexagon(-2, 3, -1), Hexagon(-3, 1, 2), Hexagon(-1, -2, 3), 
            Hexagon(2, -3, 1)
        }
        
        # Initialize flowers (forbidden cells + their neighbors)
        self.flowers_dict = {}
        for forbidden_cell in self.forbidden_cells:
            flower_set = {forbidden_cell} | forbidden_cell.neighbors(self)
            self.flowers_dict[forbidden_cell] = flower_set

        # Initialize pieces dictionary
        self.pieces = {}
        
        # Initialize hats at center
        self.red_hat = None
        self.blue_hat = None

    def possible_flowers(self, hex_cell):
        """Returns the list of forbidden centers whose flower contains hex_cell."""
        results = []
        for center, flower_set in self.flowers_dict.items():
            if hex_cell in flower_set:
                results.append(center)
        return results

    def place_piece(self, piece, position):
        """Place a piece on the board."""
        # Regular case
        valid_position = (
            position in self.complete_hex_board and 
            position not in self.pieces and 
            position not in self.forbidden_cells
        )
        
        if valid_position:
            piece.position = position
            self.pieces[position] = piece
            return True
        
        return False

    def move_piece(self, start, end):
        """Move a piece from start to end position."""
        # Special case for moving hats from center
        center = Hexagon(0, 0, 0)
        if start == center:
            # Handle moving the red hat from center
            if self.red_hat and self.red_hat.color == self.pieces.get(start, Hat("")).color:
                hat = self.red_hat
                self.red_hat = None
                hat.position = end
                
                # If moving to a position with another piece, immobilize it and store both
                if end in self.pieces and not isinstance(self.pieces[end], Hat):
                    existing_piece = self.pieces[end]
                    # Create a tuple (piece, hat) to store both pieces
                    self.pieces[end] = (existing_piece, hat)
                else:
                    # Just store the hat
                    self.pieces[end] = hat
                return True
                
            # Handle moving the blue hat from center
            elif self.blue_hat and self.blue_hat.color == self.pieces.get(start, Hat("")).color:
                hat = self.blue_hat
                self.blue_hat = None
                hat.position = end
                
                # If moving to a position with another piece, immobilize it and store both
                if end in self.pieces and not isinstance(self.pieces[end], Hat):
                    existing_piece = self.pieces[end]
                    existing_piece.immobilized = True
                    # Create a tuple (piece, hat) to store both pieces
                    self.pieces[end] = (existing_piece, hat)
                else:
                    # Just store the hat
                    self.pieces[end] = hat
                return True
        
        # Regular piece movement
        if (start in self.pieces and 
            end in self.complete_hex_board and 
            end not in self.forbidden_cells):
            
            # Get the piece at start position
            piece_at_start = self.pieces.pop(start)
            
            # If it's a tuple (piece, hat), extract the hat
            if isinstance(piece_at_start, tuple) and isinstance(piece_at_start[1], Hat):
                # We're moving a hat from a position with another piece
                piece_under_hat, hat = piece_at_start
                hat.position = end
                
                # Put the piece back at start position and remove immobilization
                piece_under_hat.immobilized = False
                self.pieces[start] = piece_under_hat
                
                # Check destination
                if end in self.pieces and not isinstance(self.pieces[end], Hat):
                    # Create a new tuple at destination
                    existing_piece = self.pieces[end]
                    existing_piece.immobilized = True
                    self.pieces[end] = (existing_piece, hat)
                else:
                    # Just place the hat
                    self.pieces[end] = hat
                
                return True
            
            # Regular piece (not a hat, not a tuple)
            else:
                piece = piece_at_start
                piece.position = end
                
                # Check if this is a hat being moved
                if isinstance(piece, Hat):
                    # If there's already a piece at the destination, immobilize it
                    if end in self.pieces and not isinstance(self.pieces[end], Hat) and not isinstance(self.pieces[end], tuple):
                        existing_piece = self.pieces[end]
                        existing_piece.immobilized = True
                        # Create a tuple (piece, hat)
                        self.pieces[end] = (existing_piece, piece)
                    else:
                        # Just store the hat
                        self.pieces[end] = piece
                else:
                    # Regular piece moving to empty space
                    self.pieces[end] = piece
                
                return True
            
        return False

    def free_cells(self):
        """Returns the set of free cells on the board."""
        return self.complete_hex_board - set(self.pieces.keys())

    def is_adjacent(self, position):
        """Checks if any adjacent cell is occupied."""
        return any(adj in self.pieces for adj in position.neighbors(self))
        
    def hex_to_pixel(self, q, r, size):
        """Convert cubic coordinates (q, r) to 2D pixel coordinates."""
        x = size * (3 / 2 * q)
        y = size * (math.sqrt(3) * (r + q / 2))
        return x, y
        
    def pixel_to_hex(self, x, y, size):
        """Convert 2D pixel coordinates to cubic coordinates (q, r, s)."""
        q = (2/3 * x) / size
        r = (-1/3 * x + math.sqrt(3)/3 * y) / size
        s = -q - r  # Third coordinate derived from the constraint q + r + s = 0
        return self.cube_round(q, r, s)
    
    def cube_round(self, x, y, z):
        """Round floating point cubic coordinates to the nearest hex."""
        rx = round(x)
        ry = round(y)
        rz = round(z)
        
        x_diff = abs(rx - x)
        y_diff = abs(ry - y)
        z_diff = abs(rz - z)
        
        if x_diff > y_diff and x_diff > z_diff:
            rx = -ry - rz
        elif y_diff > z_diff:
            ry = -rx - rz
        else:
            rz = -rx - ry
            
        return rx, ry, rz