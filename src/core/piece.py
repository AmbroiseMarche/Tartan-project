"""
Piece classes - Different game pieces with their movement rules
"""
from src.core.hexagon import Hexagon

class Piece:
    def __init__(self, color, position):
        self.color = color
        self.position = position
        self.immobilized = False
        self.just_formed = False

    def __repr__(self):
        return f"{self.__class__.__name__}({self.color}, {self.position})"

    def possible_moves(self, board):
        raise NotImplementedError("This method must be overridden by subclasses.")
    
    def can_move(self):
        return not self.immobilized
    
class Unit(Piece):
    def possible_moves(self, board):
        neighbors = self.position.neighbors(board)
        moves = set()

        for neighbor in neighbors:
            if neighbor in board.free_cells():
                moves.add(neighbor)  # Free cell
            elif (neighbor in board.pieces and 
                  board.pieces[neighbor].color == self.color and 
                  (isinstance(board.pieces[neighbor], Unit) or isinstance(board.pieces[neighbor], Double))):
                moves.add(neighbor)  # Cell occupied by an allied unit (fusion possible)

        return moves

class Double(Piece):
    def possible_moves(self, board):
        """Returns possible moves for a stack of 2 units."""
        # Step 1: Get adjacent cells (filtered)
        neighbors = {
            neighbor for neighbor in self.position.neighbors(board)
            if neighbor not in board.forbidden_cells and neighbor not in board.pieces
        }

        # Step 2: Temporarily remove the piece from the board
        board.pieces.pop(self.position, None)

        # Step 3: Get all neighbors of the neighbors
        moves = set()
        for neighbor in neighbors:
            neighbors_of_neighbors = neighbor.neighbors(board)
            for cell in neighbors_of_neighbors:
                # Skip dark cells, own position, and cells already in moves
                if cell in board.forbidden_cells or cell == self.position or cell in moves:
                    continue
                    
                # Free cell
                if cell not in board.pieces:
                    moves.add(cell)
                # Cell with a piece
                else:
                    other_piece = board.pieces[cell]
                    
                    # Allied piece (possible fusion)
                    if other_piece.color == self.color:
                        if isinstance(other_piece, Unit) or isinstance(other_piece, Double):
                            moves.add(cell)
                    # Enemy piece (possible capture)
                    else:
                        if isinstance(other_piece, Unit):
                            moves.add(cell)

        # Step 4: Put the piece back on the board
        board.pieces[self.position] = self

        return moves

class Triple(Piece):
    def possible_moves(self, board):
        """Returns possible moves for a stack of 3 units."""
        # Step 1: Get adjacent cells (filtered)
        neighbors = {
            neighbor for neighbor in self.position.neighbors(board)
            if neighbor not in board.forbidden_cells and neighbor not in board.pieces
        }

        # Step 2: Temporarily remove the piece from the board
        board.pieces.pop(self.position, None)

        # Step 3: Get neighbors of neighbors (filtered)
        second_neighbors = set()
        for neighbor in neighbors:
            second_neighbors.update(
                neighbor.neighbors(board) 
                if neighbor not in board.forbidden_cells and neighbor not in board.pieces 
                else set()
            )

        # Step 4: Get accessible adjacent cells of second-degree neighbors
        moves = set()
        for second_neighbor in second_neighbors:
            neighbors_of_second = second_neighbor.neighbors(board)
            for cell in neighbors_of_second:
                # Skip dark cells, own position, and cells already in moves
                if cell in board.forbidden_cells or cell == self.position or cell in moves:
                    continue
                    
                # Free cell
                if cell not in board.pieces:
                    moves.add(cell)
                # Cell with a piece
                else:
                    other_piece = board.pieces[cell]
                    
                    # Allied piece (future possible fusion)
                    if other_piece.color == self.color:
                        pass  # No fusion implemented yet for Triple
                    # Enemy piece (possible capture)
                    else:
                        if isinstance(other_piece, Double):
                            moves.add(cell)  # Triple can capture enemy Double

        # Step 5: Put the piece back on the board
        board.pieces[self.position] = self
        
        return moves

class Quadruple(Piece):
    def possible_moves(self, board):
        return set()

class Hat(Piece):
    def possible_moves(self, board):
        """
        The hat moves 1 cell.
        It cannot go on a dark cell (except initial placement).
        It cannot go on a cell already containing a hat.
        Otherwise, it can go on a free cell or an occupied cell (allied or enemy).
        When a hat moves onto a piece, it immobilise and protect that piece.
        """
        if not self.can_move():
            return set()

        moves = set()
        for neighbor in self.position.neighbors(board):
            # Forbid dark cells
            if neighbor in board.forbidden_cells:
                continue
            # If there's already a hat, refuse
            if neighbor in board.pieces and (isinstance(board.pieces[neighbor], Hat) or isinstance(board.pieces[neighbor], tuple)):
                continue
            # Otherwise, it's OK (free cell or occupied by a piece without a hat)
            moves.add(neighbor)
        return moves
    

class InitialHats:
    """Represents the 2 hats (red and blue) in the center at the beginning of the game."""
    
    def __init__(self, position):
        self.position = position
        self.hats = ["red", "blue"]

    def __repr__(self):
        return f"InitialHats({self.hats}, pos={self.position})"