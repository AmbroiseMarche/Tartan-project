import math
import copy
import numpy as np
import torch
import torch.nn.functional as F  # uniquement si vous souhaitez utiliser des fonctions PyTorch pour la softmax, etc.

# --- Ajout d'une méthode copy() à HexGameEnv ---
# Vous pouvez l'ajouter directement dans la classe HexGameEnv ; ici, nous définissons une fonction utilitaire.
def env_copy(env):
    return copy.deepcopy(env)


# --- Fonction d'évaluation heuristique ---
def evaluate_state(env, player_color):
    """
    Évalue l'état actuel selon le barème de valeurs indiqué :
        - 1 point pour une Unite (+9 si voisine d'une Unite alliée => total 10)
        - 10 points pour un Double
        - 5 points pour un Triple
        - 0 point pour un Quadruple (sauf si adjacent à un chapeau allié => 100)
        - 0 point pour un Chapeau
        - Si occupant est chapeauté par l'adversaire => 0
        - Score final : somme pièces alliées - somme pièces adverses
    """
    winner = env.check_win()
    if winner == player_color:
        return 9999
    elif winner is not None:
        return -9999
    
    # Contrôle de la couleur adverse (si vous avez seulement 2 joueurs)
    def other_color(c):
        return "bleu" if c == "rouge" else "rouge"
    
    base_value = {
        "Unite": 1,
        "Double": 10,
        "Triple": 5,
        "Quadruple": 0,
        "Chapeau": 0
    }
    score_player = 0
    score_opponent = 0
    
    for cell, content in env.plateau.pieces.items():
        # Gérer le tuple occupant-chapeau
        if isinstance(content, tuple):
            occupant, hat = content
            # S'il s'agit de deux chapeaux, on considère 0 pour tout
            if isinstance(occupant, Chapeau) and isinstance(hat, Chapeau):
                continue
            # Si occupant est chapeauté par l'adversaire => occupant vaut 0
            if occupant.couleur != hat.couleur:
                continue
            # Sinon (occupant.couleur == hat.couleur), on évalue occupant
            piece_obj = occupant
        else:
            piece_obj = content
        
        # Récupérer la valeur de base
        piece_name = piece_obj.__class__.__name__
        val = base_value.get(piece_name, 0)
        
        # Bonus pour Unite voisine d'une Unite alliée
        if piece_name == "Unite" and val > 0:
            neighbors = piece_obj.position.neighbors(env.plateau)
            has_ally_unite_neighbor = False
            for ncell in neighbors:
                if ncell in env.plateau.pieces:
                    neighbor_content = env.plateau.pieces[ncell]
                    # Gérer le cas d'un occupant chapeauté ou d'un occupant seul
                    if isinstance(neighbor_content, tuple):
                        neigh_occ, neigh_hat = neighbor_content
                        if isinstance(neigh_occ, Unite) and neigh_occ.couleur == piece_obj.couleur:
                            has_ally_unite_neighbor = True
                            break
                    else:
                        if isinstance(neighbor_content, Unite) and neighbor_content.couleur == piece_obj.couleur:
                            has_ally_unite_neighbor = True
                            break
            if has_ally_unite_neighbor:
                val += 9  # total 10
            
        # Quadruple adjacent à un chapeau allié => 100
        if piece_name == "Quadruple":
            neighbors = piece_obj.position.neighbors(env.plateau)
            ally_chapeau_adjacent = False
            for ncell in neighbors:
                if ncell in env.plateau.pieces:
                    neighbor_content = env.plateau.pieces[ncell]
                    if isinstance(neighbor_content, tuple):
                        # vérifier chaque élément du tuple
                        for sp in neighbor_content:
                            if isinstance(sp, Chapeau) and sp.couleur == piece_obj.couleur:
                                ally_chapeau_adjacent = True
                                break
                    elif isinstance(neighbor_content, Chapeau) and neighbor_content.couleur == piece_obj.couleur:
                        ally_chapeau_adjacent = True
                if ally_chapeau_adjacent:
                    break
            if ally_chapeau_adjacent:
                val = 100
        
        # Additionner ou soustraire
        if piece_obj.couleur == player_color:
            score_player += val
        else:
            score_opponent += val
    
    return score_player - score_opponent


# --- Recherche alphabeta ---
def alphabeta(env, depth, alpha, beta, maximizing_player, player_color):
    """
    Applique la recherche minimax avec élagage alpha-beta sur l'environnement.
    - env : instance de HexGameEnv (qui doit être copiable)
    - depth : profondeur restante de recherche
    - alpha, beta : bornes de l'élagage
    - maximizing_player : True si c'est au tour du joueur dont la couleur est player_color
    """
    # Condition d'arrêt : profondeur nulle ou partie terminée
    if depth == 0 or env.check_win() is not None:
        return evaluate_state(env, player_color)
    
    legal_moves = env.get_legal_moves()
    if not legal_moves:
        return evaluate_state(env, player_color)
    
    if maximizing_player:
        value = -math.inf
        for move in legal_moves:
            env_copy_instance = env_copy(env)
            valid, _ = env_copy_instance.apply_move(move)
            if not valid:
                continue
            value = max(value, alphabeta(env_copy_instance, depth - 1, alpha, beta, False, player_color))
            alpha = max(alpha, value)
            if alpha >= beta:
                break  # Coupure beta
        return value
    else:
        value = math.inf
        for move in legal_moves:
            env_copy_instance = env_copy(env)
            valid, _ = env_copy_instance.apply_move(move)
            if not valid:
                continue
            value = min(value, alphabeta(env_copy_instance, depth - 1, alpha, beta, True, player_color))
            beta = min(beta, value)
            if alpha >= beta:
                break  # Coupure alpha
        return value

def best_move(env, depth, player_color):
    """
    Recherche le meilleur coup à partir de l'environnement env en utilisant alphabeta jusqu'à la profondeur 'depth'.
    Retourne un tuple (move, value).
    """
    legal_moves = env.get_legal_moves()
    best_val = -math.inf
    best_mv = None
    alpha = -math.inf
    beta = math.inf
    for move in legal_moves:
        env_copy_instance = env_copy(env)
        valid, _ = env_copy_instance.apply_move(move)
        if not valid:
            continue
        move_val = alphabeta(env_copy_instance, depth - 1, alpha, beta, False, player_color)
        if move_val > best_val:
            best_val = move_val
            best_mv = move
        alpha = max(alpha, best_val)
    return best_mv, best_val
