"""
Gym environment for reinforcement learning
"""
import gymnasium as gym
import numpy as np
from gymnasium import spaces

from src.core.board import Board
from src.core.player import Player
from src.core.piece import Unit, Double, Triple, Quadruple, Hat

class HexGameEnv(gym.Env):
    """
    Custom Environment that follows gym interface for the hexagonal game.
    This environment allows AI training with reinforcement learning.
    """
    metadata = {'render.modes': ['human']}

    def __init__(self):
        super(HexGameEnv, self).__init__()
        
        # Initialize the board and players
        self.board = Board()
        self.player1 = Player(color="red")  # AI player
        self.player2 = Player(color="blue")  # Opponent
        self.current_player_idx = 0
        self.players = [self.player1, self.player2]
        
        # Define action and observation spaces
        # Action space: move piece from source to destination
        # Each location on board can be represented by its q,r,s coordinates
        # We simplify by using flattened indices of valid board positions
        n_cells = len(self.board.complete_hex_board)
        self.action_space = spaces.Discrete(n_cells * n_cells)  # source_cell * target_cell
        
        # Observation space: state of the board
        # For each cell: [is_empty, is_red_unit, is_red_double, ..., is_blue_hat]
        # 10 possible states per cell (empty, 4 red piece types, 4 blue piece types, forbidden)
        self.observation_space = spaces.Box(low=0, high=1, 
                                           shape=(n_cells, 10), 
                                           dtype=np.float32)
        
        # Initialize the board with a default setup
        self.reset()
        
    def reset(self, seed=None, options=None):
        """Reset the environment to an initial state."""
        super().reset(seed=seed)
        
        # Clear the board
        self.board = Board()
        
        # Set up initial piece positions (simplified placement phase)
        # This could be randomized or follow specific strategies
        self._setup_initial_pieces()
        
        # Reset players and turn
        self.current_player_idx = 0
        
        # Get initial observation
        observation = self._get_observation()
        info = {}
        
        return observation, info
        
    def step(self, action):
        """
        Execute one time step within the environment.
        
        Args:
            action: Index representing (source_cell, target_cell)
            
        Returns:
            observation, reward, terminated, truncated, info
        """
        # Decode action
        source_idx, target_idx = self._decode_action(action)
        
        # Convert indices to board hexagons
        source_hex = self._index_to_hex(source_idx)
        target_hex = self._index_to_hex(target_idx)
        
        # Get current player
        current_player = self.players[self.current_player_idx]
        
        # Check if move is valid
        valid_move = False
        reward = -0.1  # Small penalty for invalid moves
        
        if (source_hex in self.board.pieces and 
            self.board.pieces[source_hex].color == current_player.color):
            
            piece = self.board.pieces[source_hex]
            possible_moves = piece.possible_moves(self.board)
            
            if target_hex in possible_moves:
                # Execute the move
                current_player.move_piece(source_hex, target_hex, self.board)
                valid_move = True
                reward = 0.1  # Small reward for valid moves
                
                # Additional rewards for strategic moves
                # For example, capturing opponent pieces, forming stronger pieces, etc.
                # This part would need game-specific logic
        
        # Switch players if valid move
        if valid_move:
            self.current_player_idx = 1 - self.current_player_idx
        
        # Get updated observation
        observation = self._get_observation()
        
        # Check if game is over
        terminated = self._check_game_over()
        truncated = False  # We don't truncate episodes in this environment
        
        # Prepare info dict
        info = {
            "valid_move": valid_move,
            "current_player": self.current_player_idx
        }
        
        return observation, reward, terminated, truncated, info
    
    def render(self, mode='human'):
        """
        Render the current state of the environment.
        For this game, we would typically display the board with pygame.
        """
        # In a full implementation, this would display the game board
        # using the UI rendering functions
        pass
    
    def _setup_initial_pieces(self):
        """Set up initial piece positions for the game."""
        # This is a simplified example - actual setup could vary
        # Place red units (Player 1)
        red_positions = [
            (-1, -1, 2), (3, -3, 0), (2, -1, -1), (1, 1, -2)
        ]
        for pos in red_positions:
            self.board.place_piece(Unit("red", pos), pos)

        # Place blue units (Player 2)
        blue_positions = [
            (0, -3, 3), (-1, 2, -1), (-2, 1, 1), (-3, 0, 3)
        ]
        for pos in blue_positions:
            self.board.place_piece(Unit("blue", pos), pos)
    
    def _get_observation(self):
        """Convert the current board state to an observation."""
        n_cells = len(self.board.complete_hex_board)
        observation = np.zeros((n_cells, 10), dtype=np.float32)
        
        # Map each cell to its index
        cell_to_idx = {hex_cell: idx for idx, hex_cell in enumerate(self.board.complete_hex_board)}
        
        # Fill the observation matrix
        for hex_cell, idx in cell_to_idx.items():
            if hex_cell in self.board.forbidden_cells:
                observation[idx, 9] = 1  # Mark as forbidden
            elif hex_cell in self.board.pieces:
                piece = self.board.pieces[hex_cell]
                piece_idx = 0
                
                # Determine piece type index
                if isinstance(piece, Unit):
                    piece_idx = 1
                elif isinstance(piece, Double):
                    piece_idx = 2
                elif isinstance(piece, Triple):
                    piece_idx = 3
                elif isinstance(piece, Quadruple):
                    piece_idx = 4
                elif isinstance(piece, Hat):
                    piece_idx = 5
                
                # Adjust index for color
                if piece.color == "red":
                    observation[idx, piece_idx] = 1
                else:  # blue
                    observation[idx, piece_idx + 4] = 1
            else:
                observation[idx, 0] = 1  # Empty cell
                
        return observation
    
    def _decode_action(self, action):
        """Convert flat action index to source and target indices."""
        n_cells = len(self.board.complete_hex_board)
        source_idx = action // n_cells
        target_idx = action % n_cells
        return source_idx, target_idx
    
    def _index_to_hex(self, idx):
        """Convert index to hexagon object."""
        # Convert the flat index back to a hexagon
        return list(self.board.complete_hex_board)[idx]
    
    def _check_game_over(self):
        """Check if the game is over."""
        # For simplicity, we'll just check if either player has no more pieces
        # In a real implementation, check victory conditions based on game rules
        red_pieces = sum(1 for piece in self.board.pieces.values() if piece.color == "red")
        blue_pieces = sum(1 for piece in self.board.pieces.values() if piece.color == "blue")
        
        return red_pieces == 0 or blue_pieces == 0