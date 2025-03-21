"""
AI player implementations for the hexagonal game
"""
import random
import pygame
from stable_baselines3 import PPO

from src.core.player import Player
from src.core.hexagon import Hexagon

class RandomPlayer(Player):
    """
    Simple AI player that selects random valid moves.
    """
    def __init__(self, color):
        super().__init__(color=color, name=f"RandomAI ({color})")
    
    def choose_action(self, board, game_state):
        """
        Choose a random valid action.
        
        Args:
            board: Game board
            game_state: Current game state with possible actions
            
        Returns:
            A randomly chosen valid action
        """
        # Get all pieces of this player's color
        player_pieces = [
            pos for pos, piece in board.pieces.items() 
            if piece.color == self.color and not isinstance(piece, Quadruple)
        ]
        
        if not player_pieces:
            return None  # No pieces to move
            
        # Try random pieces until we find one with valid moves
        while player_pieces:
            # Choose a random piece
            piece_pos = random.choice(player_pieces)
            piece = board.pieces[piece_pos]
            
            # Get possible moves for this piece
            moves = piece.possible_moves(board)
            
            if moves:
                # Return a random valid move
                return random.choice(list(moves))
            
            # Remove this piece from consideration if it has no moves
            player_pieces.remove(piece_pos)
            
        return None  # No valid moves found

class RLPlayer(Player):
    """
    Reinforcement learning AI player using a trained model.
    """
    def __init__(self, color, model_path):
        super().__init__(color=color, name=f"RLAI ({color})")
        # Load the trained model
        self.model = PPO.load(model_path)
        
    def choose_action(self, board, game_state):
        """
        Choose an action using the trained model.
        
        Args:
            board: Game board
            game_state: Current game state
            
        Returns:
            The selected action based on the model's prediction
        """
        # Convert the current board state to the observation format expected by the model
        observation = self._board_to_observation(board)
        
        # Get action from model
        action, _states = self.model.predict(observation, deterministic=True)
        
        # Decode and validate the action
        source_idx, target_idx = self._decode_action(action, board)
        source_hex = self._index_to_hex(source_idx, board)
        target_hex = self._index_to_hex(target_idx, board)
        
        # Verify the action is valid
        if (source_hex in board.pieces and 
            board.pieces[source_hex].color == self.color):
            
            piece = board.pieces[source_hex]
            possible_moves = piece.possible_moves(board)
            
            if target_hex in possible_moves:
                return target_hex
        
        # If model gives invalid action, fall back to random valid move
        return RandomPlayer(self.color).choose_action(board, game_state)
    
    def _board_to_observation(self, board):
        """Convert board state to observation format for the model."""
        # This needs to match the format in environment.py
        # Implementation details would depend on how we process observations
        pass
        
    def _decode_action(self, action, board):
        """Convert model action to source and target indices."""
        n_cells = len(board.complete_hex_board)
        source_idx = action // n_cells
        target_idx = action % n_cells
        return source_idx, target_idx
    
    def _index_to_hex(self, idx, board):
        """Convert index to hexagon object."""
        return list(board.complete_hex_board)[idx]