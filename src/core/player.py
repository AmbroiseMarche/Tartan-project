"""
Player classes - Base player class and human player implementation
"""

class Player:
    def __init__(self, color, name=None):
        self.color = color
        self.name = name or f"Player {color}"
        self.pieces = []

    def place_piece(self, piece_type, position, board):
        piece = piece_type(self.color, position)
        if board.place_piece(piece, position):
            self.pieces.append(piece)
            return True
        return False

    def move_piece(self, start, end, board):
        if board.move_piece(start, end):
            for piece in self.pieces:
                if piece.position == start:
                    piece.position = end
                    return True
        return False

    def choose_action(self, board, game_state):
        """
        Method to be overridden.
        For a human player, it will wait for clicks.
        For an AI player, it will execute a decision policy.
        """
        raise NotImplementedError("This method must be implemented in subclasses.")