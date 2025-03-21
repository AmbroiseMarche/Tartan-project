"""
Game Phase - Main gameplay phase after initial placement
"""
import pygame
import math
from src.core.board import Board
from src.core.player import Player
from src.core.piece import Unit, Double, Triple, Quadruple, Hat
from src.core.hexagon import Hexagon
from src.ui.rendering import render_board

# Button definitions for move/split
MOVE_BUTTON_RECT = pygame.Rect(20, 50, 100, 40)
SPLIT_BUTTON_RECT = pygame.Rect(130, 50, 100, 40)

def draw_buttons_for_double(screen, double_piece):
    """
    Draw two buttons: "Move" and "Split".
    All doubles can be split now.
    """
    # Draw Move button
    pygame.draw.rect(screen, (180, 180, 180), MOVE_BUTTON_RECT)
    font = pygame.font.Font(None, 24)
    text_move = font.render("Move", True, (0, 0, 0))
    screen.blit(text_move, (MOVE_BUTTON_RECT.x + 15, MOVE_BUTTON_RECT.y + 10))

    # Normal Split button - always allowed now
    pygame.draw.rect(screen, (180, 180, 180), SPLIT_BUTTON_RECT)
    text_split = font.render("Split", True, (0, 0, 0))
    screen.blit(text_split, (SPLIT_BUTTON_RECT.x + 15, SPLIT_BUTTON_RECT.y + 10))

def is_valid_split_cell(board, hex_cell):
    """
    Check if a cell is valid for placing a split unit:
    - Not a dark cell
    - Not occupied
    """
    if hex_cell in board.forbidden_cells:
        return False
    if hex_cell in board.pieces:
        return False
    return True

def perform_split(board, double_piece, screen, size):
    """
    Split: Double -> 3 Units
    - Each unit must be in a different flower
    - Block the entire flower once used
    - Exclude the central flower (0,0,0)
    """
    old_pos = double_piece.position
    color = double_piece.color

    # Remove the Double
    del board.pieces[old_pos]

    # Track used flowers
    used_flowers = set()
    # Set of blocked cells already assigned to flowers
    blocked_cells = set()

    units_to_place = 3

    while units_to_place > 0:
        # Display board with blocked cells
        render_board(screen, board, size, blocked=blocked_cells)
        
        # Message
        font = pygame.font.Font(None, 30)
        text = font.render(
            f"Place unit #{4 - units_to_place} (color {color})",
            True, (0, 0, 0)
        )
        screen.blit(text, (10, 10))
        pygame.display.flip()

        valid_cell = None
        while valid_cell is None:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return False
                    
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    q, r, s = board.pixel_to_hex(mx - 400, my - 300, size)
                    clicked_hex = Hexagon(q, r, s)

                    # Check if cell is blocked
                    if clicked_hex in blocked_cells:
                        print("This cell is already blocked (flower already used).")
                        continue

                    # Check if cell is valid
                    if is_valid_split_cell(board, clicked_hex):
                        # Get the possible flowers => list of possible flowers
                        possible_flowers = board.possible_flowers(clicked_hex)

                        # Remove the central flower if present
                        center = Hexagon(0, 0, 0)
                        if center in possible_flowers:
                            possible_flowers.remove(center)

                        # Find an unused flower
                        chosen_flower = None
                        for flower_center in possible_flowers:
                            if flower_center not in used_flowers:
                                chosen_flower = flower_center
                                break

                        if chosen_flower is not None:
                            # Valid click
                            valid_cell = clicked_hex
                            # Mark this flower as "used"
                            used_flowers.add(chosen_flower)

                            # BLOCK all cells of this flower
                            # => flower = {center} U neighbors(center)
                            flower_cells = {chosen_flower} | chosen_flower.neighbors(board)
                            blocked_cells |= flower_cells
                        else:
                            print("Impossible: this cell is either outside a flower or in a flower already used.")
                    else:
                        print("Invalid cell (dark/occupied).")
            
            pygame.time.Clock().tick(30)  # Cap at 30 FPS

        # Place the unit
        new_unit = Unit(color, valid_cell)
        board.pieces[valid_cell] = new_unit
        units_to_place -= 1

    # After placing all 3 units
    print("==> Split complete: Double replaced by 3 Units (distinct flowers).")
    return True

def initialize_preset_configuration(board, player1, player2):
    """Initialize a predefined setup after the placement phase (for testing)."""
    # Place red units (Player 1)
    red_positions = [
        (-1, -1, 2), (4, -1, -3), (3, -3, 0), (2, -4, 2),
        (2, -1, -1), (2, 2, -4), (1, -2, 1), (1, 1, -2)
    ]
    for pos in red_positions:
        board.place_piece(Unit("red", Hexagon(*pos)), Hexagon(*pos))

    # Place blue units (Player 2)
    blue_positions = [
        (0, -3, 3), (0, 3, -3), (-1, 2, -1), (-2, -2, 4),
        (-2, 1, 1), (-3, 0, 3), (-3, 4, -1), (-4, 2, 2)
    ]
    for pos in blue_positions:
        board.place_piece(Unit("blue", Hexagon(*pos)), Hexagon(*pos))

    # Place hats at center
    center = Hexagon(0, 0, 0)
    red_hat = Hat("red", center)
    blue_hat = Hat("blue", center)
    
    # Store both hats directly in board attributes
    board.red_hat = red_hat
    board.blue_hat = blue_hat
    
    print("Initialized preset configuration with both hats at center")

def game_phase(screen, board, players):
    """Run the main game phase after placement."""
    player_index = 0  # Current player index
    size = 40  # Hexagon size
    game_over = False
    
    while not game_over:
        player = players[player_index]
        render_board(screen, board, size)
        
        # Handle input events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False  # Quit game
                
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
                x, y = event.pos
                q, r, s = board.pixel_to_hex(x - 400, y - 300, size)
                clicked_hex = Hexagon(q, r, s)
                
                # Special case for clicking the center with hats
                if clicked_hex.q == 0 and clicked_hex.r == 0 and clicked_hex.s == 0:
                    # Check if the current player has a hat at center
                    if (player.color == "red" and board.red_hat) or (player.color == "blue" and board.blue_hat):
                        hat = board.red_hat if player.color == "red" else board.blue_hat
                        
                        # Show possible moves for the hat
                        possible_actions = hat.possible_moves(board)
                        render_board(screen, board, size, highlighted=possible_actions)
                        
                        # Wait for player to select a move
                        action_completed = False
                        while not action_completed:
                            for hat_event in pygame.event.get():
                                if hat_event.type == pygame.QUIT:
                                    return False  # Quit game
                                    
                                if hat_event.type == pygame.MOUSEBUTTONDOWN and hat_event.button == 1:
                                    x2, y2 = hat_event.pos
                                    q2, r2, s2 = board.pixel_to_hex(x2 - 400, y2 - 300, size)
                                    target_hex = Hexagon(q2, r2, s2)
                                    
                                    if target_hex in possible_actions:
                                        # Move the hat from center
                                        if player.color == "red":
                                            hat = board.red_hat
                                            board.red_hat = None
                                        else:
                                            hat = board.blue_hat
                                            board.blue_hat = None
                                        
                                        # Set the hat's position
                                        hat.position = target_hex
                                        
                                        # Handle destination cell
                                        # Case A: Destination has a regular piece (create a tuple)
                                        if target_hex in board.pieces and not isinstance(board.pieces[target_hex], Hat) and not isinstance(board.pieces[target_hex], tuple):
                                            existing_piece = board.pieces[target_hex]
                                            # Immobilize the piece
                                            existing_piece.immobilized = True
                                            # Create a tuple with piece and hat
                                            board.pieces[target_hex] = (existing_piece, hat)
                                        # Case B: Destination is empty (just place the hat)
                                        elif target_hex not in board.pieces:
                                            board.pieces[target_hex] = hat
                                        # Case C: Destination has a hat or a tuple (this shouldn't happen with valid moves)
                                        else:
                                            # This is a fallback but shouldn't happen if possible_moves is correct
                                            print("Warning: Attempted to move hat to an invalid destination with another hat or tuple")
                                            board.pieces[target_hex] = hat
                                        
                                        action_completed = True
                            
                            pygame.time.Clock().tick(30)
                            
                        if action_completed:
                            player_index = 1 - player_index  # Switch players
                        continue  # Skip the rest of the processing
                
                # Regular piece selection/movement
                if clicked_hex in board.pieces and not isinstance(board.pieces[clicked_hex], Quadruple):
                    # Handle the case when a piece is champotée (tuple with piece and hat)
                    if isinstance(board.pieces[clicked_hex], tuple):
                        immobilized_piece, hat = board.pieces[clicked_hex]
                        # Only the hat can be selected when a piece is champotée
                        if hat.color == player.color:
                            # CRITICAL: We need to handle the hat movement differently
                            # We don't want to completely remove the tuple when selecting the hat
                            hat.position = clicked_hex  # Ensure position is correct
                            piece = hat
                            print(f"Selected {player.color} hat on top of {immobilized_piece.color} piece")
                        else:
                            # Can't select an immobilized piece
                            print(f"This {immobilized_piece.color} piece is immobilized by a {hat.color} hat")
                            continue
                    else:
                        piece = board.pieces[clicked_hex]
                    
                    # Only allow the player to move their own pieces
                    if piece.color == player.color:
                        # Special handling for Double pieces (Move or Split)
                        if isinstance(piece, Double):
                            render_board(screen, board, size)
                            draw_buttons_for_double(screen, piece)
                            pygame.display.flip()
                            
                            choice_made = False
                            action_completed = False
                            
                            while not choice_made:
                                for sub_event in pygame.event.get():
                                    if sub_event.type == pygame.QUIT:
                                        return False  # Quit game
                                        
                                    elif sub_event.type == pygame.MOUSEBUTTONDOWN and sub_event.button == 1:
                                        mx, my = sub_event.pos
                                        
                                        if MOVE_BUTTON_RECT.collidepoint(mx, my):
                                            # Move action selected
                                            choice_made = True
                                            
                                            # Show possible moves
                                            possible_actions = piece.possible_moves(board)
                                            render_board(screen, board, size, highlighted=possible_actions)
                                            
                                            # Wait for move selection
                                            move_selected = False
                                            while not move_selected:
                                                for move_event in pygame.event.get():
                                                    if move_event.type == pygame.QUIT:
                                                        return False
                                                        
                                                    if move_event.type == pygame.MOUSEBUTTONDOWN and move_event.button == 1:
                                                        x2, y2 = move_event.pos
                                                        q2, r2, s2 = board.pixel_to_hex(x2 - 400, y2 - 300, size)
                                                        target_hex = Hexagon(q2, r2, s2)
                                                        
                                                        if target_hex in possible_actions:
                                                            # Don't allow self-fusion (fix for bug #4)
                                                            if target_hex == piece.position:
                                                                print("Cannot move to the same position.")
                                                                continue
                                                                
                                                            # Handle fusion if target cell contains a piece
                                                            if target_hex in board.pieces:
                                                                other_piece = board.pieces[target_hex]
                                                                
                                                                # Handle different fusion cases
                                                                # Check if it's an enemy piece (capture)
                                                                # Skip if it's a tuple (piece with a hat on top) - can't capture
                                                                if not isinstance(other_piece, tuple) and other_piece.color != piece.color:
                                                                    # Double can capture Unit
                                                                    if isinstance(other_piece, Unit):
                                                                        print(f"Double {piece.color} captures enemy Unit {other_piece.color}")
                                                                        # First remove the enemy unit
                                                                        del board.pieces[target_hex]
                                                                        # Then directly handle the move (avoid using player.move_piece)
                                                                        old_pos = piece.position
                                                                        piece.position = target_hex
                                                                        # Remove piece from old position
                                                                        del board.pieces[old_pos]
                                                                        # Place piece at new position
                                                                        board.pieces[target_hex] = piece
                                                                        
                                                                        piece.just_formed = False
                                                                        move_selected = True
                                                                        action_completed = True
                                                                        continue
                                                                
                                                                # Same color piece - fusion (skip if tuple)
                                                                if not isinstance(other_piece, tuple) and isinstance(other_piece, Unit) and other_piece.color == piece.color:
                                                                    # Double + Unit -> Triple
                                                                    del board.pieces[piece.position]
                                                                    board.pieces[target_hex] = Triple(piece.color, target_hex)
                                                                    new_piece = board.pieces[target_hex]
                                                                    new_piece.just_formed = True
                                                                    
                                                                    # Show possibilities for new Triple
                                                                    possible_actions = new_piece.possible_moves(board)
                                                                    render_board(screen, board, size, highlighted=possible_actions)
                                                                    pygame.display.flip()
                                                                    
                                                                    # Let player continue moving with the Triple
                                                                    triple_moved = False
                                                                    while not triple_moved:
                                                                        for triple_event in pygame.event.get():
                                                                            if triple_event.type == pygame.QUIT:
                                                                                return False
                                                                                
                                                                            if triple_event.type == pygame.MOUSEBUTTONDOWN and triple_event.button == 1:
                                                                                x3, y3 = triple_event.pos
                                                                                q3, r3, s3 = board.pixel_to_hex(x3 - 400, y3 - 300, size)
                                                                                triple_target = Hexagon(q3, r3, s3)
                                                                                
                                                                                if triple_target in possible_actions and triple_target != new_piece.position:
                                                                                    # Move the Triple
                                                                                    old_pos = new_piece.position
                                                                                    new_piece.position = triple_target
                                                                                    del board.pieces[old_pos]
                                                                                    board.pieces[triple_target] = new_piece
                                                                                    triple_moved = True
                                                                                    
                                                                        pygame.time.Clock().tick(30)
                                                                    
                                                                    move_selected = True
                                                                    action_completed = True
                                                                    
                                                                elif isinstance(other_piece, Double) and other_piece.color == piece.color:
                                                                    # Double + Double -> Quadruple
                                                                    del board.pieces[piece.position]
                                                                    board.pieces[target_hex] = Quadruple(piece.color, target_hex)
                                                                    move_selected = True
                                                                    action_completed = True
                                                                    
                                                            # Simple move
                                                            else:
                                                                player.move_piece(piece.position, target_hex, board)
                                                                piece.just_formed = False
                                                                move_selected = True
                                                                action_completed = True
                                                                
                                                pygame.time.Clock().tick(30)
                                                
                                        elif SPLIT_BUTTON_RECT.collidepoint(mx, my):
                                            # Split action selected - always allowed now
                                            # Perform the split operation
                                            perform_split(board, piece, screen, size)
                                            choice_made = True
                                            action_completed = True
                                            
                            if action_completed:
                                player_index = 1 - player_index  # Switch players
                                
                        # Regular piece movement (Unit, Triple, Hat)
                        else:
                            # Show possible moves
                            possible_actions = piece.possible_moves(board)
                            render_board(screen, board, size, highlighted=possible_actions)
                            
                            # Wait for player to select a move
                            action_completed = False
                            while not action_completed:
                                for move_event in pygame.event.get():
                                    if move_event.type == pygame.QUIT:
                                        return False  # Quit game
                                        
                                    if move_event.type == pygame.MOUSEBUTTONDOWN and move_event.button == 1:
                                        x2, y2 = move_event.pos
                                        q2, r2, s2 = board.pixel_to_hex(x2 - 400, y2 - 300, size)
                                        target_hex = Hexagon(q2, r2, s2)
                                        
                                        if target_hex in possible_actions:
                                            # Handle fusion if target cell contains a piece
                                            if target_hex in board.pieces:
                                                other_piece = board.pieces[target_hex]
                                                
                                                # Check for enemy piece capture - skip tuples
                                                if not isinstance(other_piece, tuple) and other_piece.color != piece.color:
                                                    # Double captures Unit
                                                    if isinstance(piece, Double) and isinstance(other_piece, Unit):
                                                        print(f"Double {piece.color} captures enemy Unit {other_piece.color}")
                                                        # First remove the enemy unit
                                                        del board.pieces[target_hex]
                                                        # Then directly handle the move (avoid using player.move_piece)
                                                        old_pos = piece.position
                                                        piece.position = target_hex
                                                        # Remove piece from old position
                                                        del board.pieces[old_pos]
                                                        # Place piece at new position
                                                        board.pieces[target_hex] = piece
                                                        action_completed = True
                                                        continue
                                                    
                                                    # Triple captures Double
                                                    elif isinstance(piece, Triple) and isinstance(other_piece, Double):
                                                        print(f"Triple {piece.color} captures enemy Double {other_piece.color}")
                                                        # First remove the enemy double
                                                        del board.pieces[target_hex]
                                                        # Then directly handle the move (avoid using player.move_piece)
                                                        old_pos = piece.position
                                                        piece.position = target_hex
                                                        # Remove piece from old position
                                                        del board.pieces[old_pos]
                                                        # Place piece at new position
                                                        board.pieces[target_hex] = piece
                                                        action_completed = True
                                                        continue
                                                
                                                # Handle different fusion cases (for Unit)
                                                # Skip fusion with tuples
                                                if isinstance(piece, Unit) and not isinstance(other_piece, tuple):
                                                    if isinstance(other_piece, Unit) and piece.color == other_piece.color:
                                                        # Unit + Unit -> Double
                                                        del board.pieces[piece.position]
                                                        board.pieces[target_hex] = Double(piece.color, target_hex)
                                                        new_piece = board.pieces[target_hex]
                                                        new_piece.just_formed = True
                                                        
                                                        # Show possible moves for the new Double
                                                        possible_actions = new_piece.possible_moves(board)
                                                        render_board(screen, board, size, highlighted=possible_actions)
                                                        pygame.display.flip()
                                                        
                                                        # Let player continue moving with the new Double immediately
                                                        double_action_completed = False
                                                        while not double_action_completed:
                                                            for double_event in pygame.event.get():
                                                                if double_event.type == pygame.QUIT:
                                                                    return False
                                                                    
                                                                if double_event.type == pygame.MOUSEBUTTONDOWN and double_event.button == 1:
                                                                    x3, y3 = double_event.pos
                                                                    q3, r3, s3 = board.pixel_to_hex(x3 - 400, y3 - 300, size)
                                                                    double_target = Hexagon(q3, r3, s3)
                                                                    
                                                                    if double_target in possible_actions and double_target != new_piece.position:
                                                                        # Check for fusion with another piece
                                                                        if double_target in board.pieces:
                                                                            other_piece2 = board.pieces[double_target]
                                                                            
                                                                            if isinstance(other_piece2, Unit) and other_piece2.color == new_piece.color:
                                                                                # Double + Unit -> Triple
                                                                                del board.pieces[new_piece.position]
                                                                                board.pieces[double_target] = Triple(new_piece.color, double_target)
                                                                                triple_piece = board.pieces[double_target]
                                                                                triple_piece.just_formed = True
                                                                                
                                                                                # Show possible moves for new Triple
                                                                                possible_triple_actions = triple_piece.possible_moves(board)
                                                                                render_board(screen, board, size, highlighted=possible_triple_actions)
                                                                                pygame.display.flip()
                                                                                
                                                                                # Let player continue moving with the Triple
                                                                                triple_moved = False
                                                                                while not triple_moved:
                                                                                    for triple_event in pygame.event.get():
                                                                                        if triple_event.type == pygame.QUIT:
                                                                                            return False
                                                                                            
                                                                                        if triple_event.type == pygame.MOUSEBUTTONDOWN and triple_event.button == 1:
                                                                                            x4, y4 = triple_event.pos
                                                                                            q4, r4, s4 = board.pixel_to_hex(x4 - 400, y4 - 300, size)
                                                                                            triple_target = Hexagon(q4, r4, s4)
                                                                                            
                                                                                            if triple_target in possible_triple_actions and triple_target != triple_piece.position:
                                                                                                # Move the Triple
                                                                                                old_pos = triple_piece.position
                                                                                                triple_piece.position = triple_target
                                                                                                del board.pieces[old_pos]
                                                                                                board.pieces[triple_target] = triple_piece
                                                                                                triple_moved = True
                                                                                    
                                                                                    pygame.time.Clock().tick(30)
                                                                                
                                                                                double_action_completed = True
                                                                                
                                                                            elif isinstance(other_piece2, Double) and other_piece2.color == new_piece.color:
                                                                                # Double + Double -> Quadruple
                                                                                del board.pieces[new_piece.position]
                                                                                board.pieces[double_target] = Quadruple(new_piece.color, double_target)
                                                                                double_action_completed = True
                                                                        else:
                                                                            # Simple move
                                                                            old_pos = new_piece.position
                                                                            new_piece.position = double_target
                                                                            del board.pieces[old_pos]
                                                                            board.pieces[double_target] = new_piece
                                                                            double_action_completed = True
                                                            
                                                            pygame.time.Clock().tick(30)
                                                        
                                                        action_completed = True
                                                        continue
                                                        
                                                    elif isinstance(other_piece, Double) and piece.color == other_piece.color:
                                                        # Unit + Double -> Triple
                                                        del board.pieces[piece.position]
                                                        board.pieces[target_hex] = Triple(piece.color, target_hex)
                                                        new_piece = board.pieces[target_hex]
                                                        new_piece.just_formed = True
                                                        
                                                        # Show possibilities for new Triple
                                                        possible_actions = new_piece.possible_moves(board)
                                                        render_board(screen, board, size, highlighted=possible_actions)
                                                        pygame.display.flip()
                                                        
                                                        # Let player continue moving with the Triple
                                                        triple_moved = False
                                                        while not triple_moved:
                                                            for triple_event in pygame.event.get():
                                                                if triple_event.type == pygame.QUIT:
                                                                    return False
                                                                    
                                                                if triple_event.type == pygame.MOUSEBUTTONDOWN and triple_event.button == 1:
                                                                    x3, y3 = triple_event.pos
                                                                    q3, r3, s3 = board.pixel_to_hex(x3 - 400, y3 - 300, size)
                                                                    triple_target = Hexagon(q3, r3, s3)
                                                                    
                                                                    if triple_target in possible_actions and triple_target != new_piece.position:
                                                                        # Move the Triple
                                                                        old_pos = new_piece.position
                                                                        new_piece.position = triple_target
                                                                        del board.pieces[old_pos]
                                                                        board.pieces[triple_target] = new_piece
                                                                        triple_moved = True
                                                                        
                                                            pygame.time.Clock().tick(30)
                                                        
                                                        action_completed = True
                                                        
                                                # For Hat movement, handle immobilization separately
                                                elif isinstance(piece, Hat):
                                                    # Special case for Hat - it can immobilize a piece
                                                    if not isinstance(other_piece, Hat):
                                                        other_piece.immobilized = True
                                                        
                                                    # Move the hat
                                                    player.move_piece(piece.position, target_hex, board)
                                                    action_completed = True
                                            
                                            # Regular move to empty cell
                                            else:
                                                # Move the piece - doing it directly instead of using player.move_piece
                                                # to avoid issues with tuple handling
                                                old_pos = piece.position
                                                piece.position = target_hex
                                                
                                                # If it's a hat, handle the special case
                                                if isinstance(piece, Hat):
                                                    # STEP 1: Handle the origin cell (where the hat is coming from)
                                                    if old_pos in board.pieces:
                                                        # Case A: Hat was part of a tuple (hat + immobilized piece)
                                                        if isinstance(board.pieces[old_pos], tuple):
                                                            immobilized_piece, _ = board.pieces[old_pos]
                                                            # Release the immobilized piece and leave it there
                                                            immobilized_piece.immobilized = False
                                                            board.pieces[old_pos] = immobilized_piece
                                                        # Case B: Hat was alone
                                                        else:
                                                            # Remove the hat from old position
                                                            del board.pieces[old_pos]
                                                    
                                                    # STEP 2: Handle the destination cell (where the hat is going)
                                                    # Case A: Destination has a regular piece (create a tuple)
                                                    if target_hex in board.pieces and not isinstance(board.pieces[target_hex], Hat) and not isinstance(board.pieces[target_hex], tuple):
                                                        existing_piece = board.pieces[target_hex]
                                                        # Immobilize the piece
                                                        existing_piece.immobilized = True
                                                        # Create a tuple with piece and hat
                                                        board.pieces[target_hex] = (existing_piece, piece)
                                                    # Case B: Destination is empty (just place the hat)
                                                    elif target_hex not in board.pieces:
                                                        board.pieces[target_hex] = piece
                                                    # Case C: Destination has a hat or a tuple (this shouldn't happen with valid moves)
                                                    else:
                                                        # This is a fallback but shouldn't happen if possible_moves is correct
                                                        print("Warning: Attempted to move hat to an invalid destination with another hat or tuple")
                                                        board.pieces[target_hex] = piece
                                                else:
                                                    # Regular piece movement
                                                    del board.pieces[old_pos]
                                                    board.pieces[target_hex] = piece
                                                
                                                if hasattr(piece, 'just_formed'):
                                                    piece.just_formed = False
                                                action_completed = True
                                
                                pygame.time.Clock().tick(30)
                            
                            if action_completed:
                                player_index = 1 - player_index  # Switch players
        
        pygame.time.Clock().tick(30)  # Cap at 30 FPS