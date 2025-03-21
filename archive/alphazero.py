#!/usr/bin/env python3
"""
============================================================
 Jeu de Stratégie Hexagonal – Environnement et AlphaZero
============================================================

Ce script regroupe :
  - Les définitions de classes pour les hexagones, les pièces (Unite, Double, Triple, Quadruple, Chapeau)
  - La classe Plateau_hexagonal qui gère le plateau, les cases interdites, les fleurs, etc.
  - Les classes de Player (HumanPlayer et AIPlayer minimal)
  - Quelques fonctions utilitaires (conversion pixel<->hex, affichage via pygame, etc.)
  - La fonction initialiser_configuration() pour placer les unités et les chapeaux initiaux
  - La classe Gym HexGameEnv qui définit l’environnement pour le reinforcement learning
  - L’implémentation d’un agent AlphaZero :
      • Un réseau de neurones (AlphaZeroNet) en PyTorch
      • Une recherche Monte Carlo Tree Search (MCTS) guidée par ce réseau
      • Une boucle de self-play pour collecter des exemples (état, politique MCTS, résultat)
      • Une boucle d’entraînement du réseau avec sauvegarde de checkpoints
"""

#############################
# Imports et définitions de base
#############################
import math, pygame, random, numpy as np, gymnasium as gym, copy, os
from gymnasium import spaces

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

#############################
# CLASSE HEXAGONE et fonctions de conversion
#############################
class hexagone:
    def __init__(self, q, r, s, contenu=' '):
        self.q = q
        self.r = r
        self.s = s
        self.contenu = contenu

    def __repr__(self):
        return f"Hex({self.q}, {self.r}, {self.s})"

    def __eq__(self, other):
        return (self.q, self.r, self.s) == (other.q, other.r, other.s)

    def __hash__(self):
        return hash((self.q, self.r, self.s))

    def distance(self, other):
        return (abs(self.q - other.q) + abs(self.r - other.r) + abs(self.s - other.s)) // 2

    def is_neighbor(self, other):
        return self.distance(other) == 1

    def neighbors(self, plateau):
        potential = [
            hexagone(self.q + 1, self.r - 1, - (self.q + 1) - (self.r - 1)),
            hexagone(self.q + 1, self.r, - (self.q + 1) - self.r),
            hexagone(self.q, self.r + 1, - self.q - (self.r + 1)),
            hexagone(self.q - 1, self.r + 1, - (self.q - 1) - (self.r + 1)),
            hexagone(self.q - 1, self.r, - (self.q - 1) - self.r),
            hexagone(self.q, self.r - 1, - self.q - (self.r - 1))
        ]
        # Retourne uniquement les cases présentes dans le plateau complet.
        return set(potential).intersection(plateau.plateau_hexagonal_complet)

def cube_round(q, r):
    s = -q - r
    q_round = round(q)
    r_round = round(r)
    s_round = round(s)
    q_diff = abs(q_round - q)
    r_diff = abs(r_round - r)
    s_diff = abs(s_round - s)
    if q_diff > r_diff and q_diff > s_diff:
        q_round = -r_round - s_round
    elif r_diff > s_diff:
        r_round = -q_round - s_round
    else:
        s_round = -q_round - r_round
    return q_round, r_round, s_round

def pixel_to_hex(x, y, size):
    q = (2/3 * x) / size
    r = (-1/3 * x + math.sqrt(3)/3 * y) / size
    return cube_round(q, r)

#############################
# DÉFINITION DES PIÈCES
#############################
class Piece:
    def __init__(self, couleur, position):
        self.couleur = couleur
        self.position = position
        self.immobilisee = False
        self.just_fused = False  # Indique si la pièce issue d'une fusion (rebond) ne peut être splittée immédiatement.
    def __repr__(self):
        return f"{self.__class__.__name__}({self.couleur}, {self.position})"
    def mouvements_possibles(self, plateau):
        raise NotImplementedError("Surchargez cette méthode dans les sous-classes.")
    def peut_bouger(self):
        return not self.immobilisee

class Unite(Piece):
    def mouvements_possibles(self, plateau):
        voisins = self.position.neighbors(plateau)
        mouvements = set()
        for voisin in voisins:
            if voisin in plateau.casesinterdites:
                continue
            if voisin in plateau.cases_libres():
                mouvements.add(voisin)
            elif voisin in plateau.pieces:
                content = plateau.pieces[voisin]
                if isinstance(content, tuple) or isinstance(content, Chapeau):
                    continue
                if content.couleur == self.couleur and (isinstance(content, Unite) or isinstance(content, Double)):
                    mouvements.add(voisin)
        return mouvements

class Double(Piece):
    def mouvements_possibles(self, plateau):
        start = self.position
        destinations = set()
        level1 = { n for n in start.neighbors(plateau)
                   if n not in plateau.casesinterdites and (n in plateau.cases_libres() or n == start) }
        for cell in level1:
            for n in cell.neighbors(plateau):
                if n in plateau.casesinterdites:
                    continue
                if n in plateau.cases_libres() or n == start:
                    destinations.add(n)
                elif n in plateau.pieces:
                    content = plateau.pieces[n]
                    if isinstance(content, tuple) or isinstance(content, Chapeau):
                        continue
                    if content.couleur == self.couleur and (isinstance(content, Unite) or isinstance(content, Double)):
                        destinations.add(n)
                    elif isinstance(content, Unite):
                        destinations.add(n)
        return destinations

class Triple(Piece):
    def mouvements_possibles(self, plateau):
        start = self.position
        destinations = set()
        level1 = {n for n in start.neighbors(plateau)
                  if n not in plateau.casesinterdites and (n in plateau.cases_libres() or n == start)}
        level2 = set()
        for cell in level1:
            for n in cell.neighbors(plateau):
                if n not in plateau.casesinterdites and (n in plateau.cases_libres() or n == start):
                    level2.add(n)
        for cell in level2:
            for n in cell.neighbors(plateau):
                if n in plateau.casesinterdites:
                    continue
                if n in plateau.cases_libres() or n == start:
                    destinations.add(n)
                elif n in plateau.pieces:
                    content = plateau.pieces[n]
                    if isinstance(content, tuple) or isinstance(content, Chapeau):
                        continue
                    if isinstance(content, Double) and content.couleur != self.couleur:
                        destinations.add(n)
        return destinations

class Quadruple(Piece):
    def mouvements_possibles(self, plateau):
        return set()  # Une pile de 4 est immobile.

class Chapeau(Piece):
    def mouvements_possibles(self, plateau):
        if not self.peut_bouger():
            return set()
        moves = set()
        for voisin in self.position.neighbors(plateau):
            if voisin in plateau.casesinterdites:
                continue
            if voisin in plateau.pieces:
                content = plateau.pieces[voisin]
                if isinstance(content, tuple) or isinstance(content, Chapeau):
                    continue
            moves.add(voisin)
        return moves

#############################
# PLATEAU_HEXAGONAL et GESTION DU PLATEAU
#############################
class Plateau_hexagonal:
    def __init__(self):
        cases_interieures = {hexagone(q, r, -q-r) for q in range(-3, 4) for r in range(-3, 4) if -q-r in range(-3, 4)}
        cases_exterieures = {hexagone(-4,1,3), hexagone(-4,2,2), hexagone(-3,4,-1), hexagone(-2,4,-2),
                             hexagone(1,3,-4), hexagone(2,2,-4), hexagone(4,-1,-3), hexagone(4,-2,-2),
                             hexagone(3,-4,1), hexagone(2,-4,2), hexagone(-1,-3,4), hexagone(-2,-2,4)}
        self.plateau_hexagonal_complet = cases_interieures.union(cases_exterieures)
        self.casesinterdites = {hexagone(0,0,0), hexagone(3,-1,-2), hexagone(1,2,-3),
                                hexagone(-2,3,-1), hexagone(-3,1,2), hexagone(-1,-2,3), hexagone(2,-3,1)}
        self.fleurs_dict = {}
        for case_int in self.casesinterdites:
            fleur_set = {case_int} | case_int.neighbors(self)
            self.fleurs_dict[case_int] = fleur_set
        self.pieces = {}

    def liste_fleurs_possible(self, hex_case):
        results = []
        for center, fleur in self.fleurs_dict.items():
            if hex_case in fleur:
                results.append(center)
        return results

    def placer_piece(self, piece, position):
        if (position in self.plateau_hexagonal_complet and position not in self.pieces and position not in self.casesinterdites) \
           or (position in self.plateau_hexagonal_complet and isinstance(piece, Chapeau)):
            piece.position = position
            self.pieces[position] = piece
            return True
        return False

    def deplacer_piece(self, depart, arrivee):
        if depart in self.pieces and arrivee in self.plateau_hexagonal_complet and arrivee not in self.casesinterdites:
            piece = self.pieces.pop(depart)
            piece.position = arrivee
            self.pieces[arrivee] = piece
            return True
        return False

    def cases_libres(self):
        return self.plateau_hexagonal_complet - set(self.pieces.keys())

    def est_adjacent(self, position):
        return any(adj in self.pieces for adj in position.neighbors(self))

#############################
# CONFIGURATION INITIALE
#############################
def initialiser_configuration(plateau, joueur1, joueur2):
    rouge_positions = [(-1, -1, 2), (4, -1, -3), (3, -3, 0), (2, -4, 2),
                       (2, -1, -1), (2, 2, -4), (1, -2, 1), (1, 1, -2)]
    for pos in rouge_positions:
        cell = hexagone(*pos)
        plateau.placer_piece(Unite("rouge", cell), cell)
    bleu_positions = [(0, -3, 3), (0, 3, -3), (-1, 2, -1), (-2, -2, 4),
                      (-2, 1, 1), (-3, 0, 3), (-3, 4, -1), (-4, 2, 2)]
    for pos in bleu_positions:
        cell = hexagone(*pos)
        plateau.placer_piece(Unite("bleu", cell), cell)
    plateau.pieces[hexagone(0, 0, 0)] = (Chapeau("rouge", hexagone(0, 0, 0)), Chapeau("bleu", hexagone(0, 0, 0)))

def initialiser_configuration_test(plateau, joueur1, joueur2):
    plateau.pieces = {}
    allied_cell = hexagone(-1, 0, 1)
    plateau.placer_piece(Double("rouge", allied_cell), allied_cell)
    enemy_cell = hexagone(-1, 2, -1)
    plateau.placer_piece(Unite("bleu", enemy_cell), enemy_cell)

#############################
# Fonctions alphabeta et utilitaires
#############################
def env_copy(env):
    return copy.deepcopy(env)

def evaluate_state(env, player_color):
    """
    Évalue l'état selon un barème :
      - Unite : 1 point (bonus +9 si voisine d'une Unite alliée, soit 10 au total)
      - Double : 10 points
      - Triple : 5 points
      - Quadruple : 0 point (sauf si adjacent à un chapeau allié, alors 100)
      - Chapeau : 0 point
      - Si une pièce est champotée (occupée dans un tuple), sa valeur est nulle.
    """
    winner = env.check_win()
    if winner == player_color:
        return 9999
    elif winner is not None:
        return -9999

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
        if isinstance(content, tuple):
            occupant, hat = content
            if occupant.couleur != hat.couleur:
                continue
            piece_obj = occupant
        else:
            piece_obj = content
        piece_name = piece_obj.__class__.__name__
        val = base_value.get(piece_name, 0)
        if piece_name == "Unite" and val > 0:
            neighbors = piece_obj.position.neighbors(env.plateau)
            has_ally = False
            for ncell in neighbors:
                if ncell in env.plateau.pieces:
                    neighbor_content = env.plateau.pieces[ncell]
                    if isinstance(neighbor_content, tuple):
                        neigh_occ, _ = neighbor_content
                        if isinstance(neigh_occ, Unite) and neigh_occ.couleur == piece_obj.couleur:
                            has_ally = True
                            break
                    elif isinstance(neighbor_content, Unite) and neighbor_content.couleur == piece_obj.couleur:
                        has_ally = True
                        break
            if has_ally:
                val += 0.5
        if piece_name == "Quadruple":
            neighbors = piece_obj.position.neighbors(env.plateau)
            ally_hat = False
            for ncell in neighbors:
                if ncell in env.plateau.pieces:
                    neighbor_content = env.plateau.pieces[ncell]
                    if isinstance(neighbor_content, tuple):
                        for sp in neighbor_content:
                            if isinstance(sp, Chapeau) and sp.couleur == piece_obj.couleur:
                                ally_hat = True
                                break
                    elif isinstance(neighbor_content, Chapeau) and neighbor_content.couleur == piece_obj.couleur:
                        ally_hat = True
                if ally_hat:
                    break
            if ally_hat:
                val = 100
        if piece_obj.couleur == player_color:
            score_player += val
        else:
            score_opponent += val

    return score_player - score_opponent

def alphabeta(env, depth, alpha, beta, maximizing_player, player_color):
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
                break
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
                break
        return value

def best_move(env, depth, player_color):
    legal_moves = env.get_legal_moves()
    print(f"[best_move] Nombre de coups légaux : {len(legal_moves)}")
    best_val = -math.inf
    best_moves = []
    alpha = -math.inf
    beta = math.inf

    for move in legal_moves:
        env_copy_instance = env_copy(env)
        valid, _ = env_copy_instance.apply_move(move)
        if not valid:
            continue
        move_val = alphabeta(env_copy_instance, depth - 1, alpha, beta, False, player_color)
        if move[0] == 0:
            print(f"   Coup {move}, valeur={move_val}")
        if move_val > best_val:
            best_val = move_val
            best_moves = [move]
        elif move_val == best_val:
            best_moves.append(move)
        alpha = max(alpha, best_val)

    chosen_move = random.choice(best_moves) if best_moves else None
    print(f"[best_move] => Coups ex æquo : {best_moves}, valeur={best_val}")
    print(f"[best_move] => Coup finalement choisi : {chosen_move}, valeur={best_val}")
    return chosen_move, best_val

#############################
# DÉFINITION DES JOUEURS
#############################
class Player:
    def __init__(self, couleur, nom=None):
        self.couleur = couleur
        self.nom = nom
        self.pieces = []
    def placer_piece(self, piece_type, position, plateau):
        piece = piece_type(self.couleur, position)
        if plateau.placer_piece(piece, position):
            self.pieces.append(piece)
            return True
        return False
    def deplacer_piece(self, depart, arrivee, plateau):
        if plateau.deplacer_piece(depart, arrivee):
            for piece in self.pieces:
                if piece.position == depart:
                    piece.position = arrivee
                    return True
        return False
    def choisir_action(self, plateau, etat_du_jeu):
        raise NotImplementedError("À implémenter dans les sous-classes.")

class HumanPlayer(Player):
    def choisir_action(self, plateau, etat_du_jeu):
        action = None
        while action is None:
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    x, y = event.pos
                    q, r, s = pixel_to_hex(x - 400, y - 300, 40)
                    clicked_hex = hexagone(q, r, s)
                    if clicked_hex in etat_du_jeu['legal_moves']:
                        action = clicked_hex
                        break
        return action

class AIPlayer(Player):
    def choisir_action(self, plateau, etat_du_jeu):
        legal_moves = etat_du_jeu['legal_moves']
        return random.choice(legal_moves)

#############################
# ENVIRONNEMENT RL (Gym)
#############################
class HexGameEnv(gym.Env):
    metadata = {"render.modes": ["human"]}
    MAX_MOVES_PER_PLAYER = 80
    MAX_ACTIONS = 5000
    def __init__(self):
        super(HexGameEnv, self).__init__()
        self.plateau = Plateau_hexagonal()
        self.players = [Player("rouge", "Agent"), Player("bleu", "Random")]
        initialiser_configuration(self.plateau, self.players[0], self.players[1])
        self.current_player = 0
        self.history = []
        self.done = False
        self.build_cell_index()
        self.observation_space = spaces.Box(low=-1, high=100, shape=(self.n_cells,), dtype=np.int32)
        self.action_space = spaces.Discrete(HexGameEnv.MAX_ACTIONS)
        self.agent_moves = 0
        self.random_moves = 0
        self.total_moves = 0
    def reset(self, seed=None, options=None):
        if seed is not None:
            self.seed_val = seed
        self.plateau = Plateau_hexagonal()
        initialiser_configuration(self.plateau, self.players[0], self.players[1])
        self.current_player = 0
        self.history = []
        self.done = False
        self.build_cell_index()
        self.agent_moves = 0
        self.random_moves = 0
        self.total_moves = 0
        return self.get_observation(), {}
    def step(self, action):
        if self.current_player == 1:
            legal_moves = self.get_legal_moves()
            if legal_moves:
                action = random.choice(legal_moves)
            else:
                self.current_player = 0
        legal_moves = self.get_legal_moves()
        if not legal_moves:
            self.done = True
            terminated = True
            truncated = False
            return self.get_observation(), 0, terminated, truncated, {}
        if self.current_player == 0:
            if action < 0 or action >= len(legal_moves):
                reward = -0.5
                return self.get_observation(), reward, False, False, {"illegal": True}
            move = legal_moves[action]
        else:
            move = random.choice(legal_moves)
        valid, fusion_move = self.apply_move(move)
        if valid:
            self.history.append(move)
            self.total_moves += 1
            if self.current_player == 0:
                self.agent_moves += 1
            else:
                self.random_moves += 1
        if self.agent_moves >= HexGameEnv.MAX_MOVES_PER_PLAYER or self.random_moves >= HexGameEnv.MAX_MOVES_PER_PLAYER:
            self.done = True
            terminated = False
            truncated = True
            reward = -1
            return self.get_observation(), reward, terminated, truncated, {}
        winner = self.check_win()
        if winner is not None:
            self.done = True
            if winner == self.players[0].couleur:
                bonus = (HexGameEnv.MAX_MOVES_PER_PLAYER - self.agent_moves) / HexGameEnv.MAX_MOVES_PER_PLAYER
                reward = 1 + bonus
            else:
                reward = -1
            terminated = True
            truncated = False
            return self.get_observation(), reward, terminated, truncated, {}
        if valid and not fusion_move:
            self.current_player = 1 - self.current_player
        reward = 0 if valid else -0.5
        terminated = False
        truncated = False
        return self.get_observation(), reward, terminated, truncated, {}
    def build_cell_index(self):
        sorted_cells = sorted(self.plateau.plateau_hexagonal_complet, key=lambda h: (h.q, h.r, h.s))
        self.cell_index = {cell: i for i, cell in enumerate(sorted_cells)}
        self.n_cells = len(sorted_cells)
    def get_observation(self):
        obs = np.zeros(self.n_cells, dtype=np.int32)
        for cell, idx in self.cell_index.items():
            if cell in self.plateau.casesinterdites:
                obs[idx] = -1
            elif cell not in self.plateau.pieces:
                obs[idx] = 0
            else:
                content = self.plateau.pieces[cell]
                if isinstance(content, tuple):
                    obs[idx] = 99
                else:
                    if isinstance(content, Unite):
                        obs[idx] = 1 if content.couleur=="rouge" else 2
                    elif isinstance(content, Double):
                        obs[idx] = 3 if content.couleur=="rouge" else 4
                    elif isinstance(content, Triple):
                        obs[idx] = 5 if content.couleur=="rouge" else 6
                    elif isinstance(content, Quadruple):
                        obs[idx] = 7 if content.couleur=="rouge" else 8
                    elif isinstance(content, Chapeau):
                        obs[idx] = 9 if content.couleur=="rouge" else 10
        return obs
    def generate_split_moves(self, origin):
        free_cells = list(self.plateau.cases_libres())
        valid_cells = []
        for cell in free_cells:
            if cell in self.plateau.casesinterdites:
                continue
            fleurs = self.plateau.liste_fleurs_possible(cell)
            if hexagone(0, 0, 0) in fleurs:
                fleurs.remove(hexagone(0, 0, 0))
            if fleurs:
                valid_cells.append(cell)
        flower_groups = {}
        for cell in valid_cells:
            for center in self.plateau.liste_fleurs_possible(cell):
                if center == hexagone(0, 0, 0):
                    continue
                flower_groups.setdefault(center, []).append(cell)
        if len(flower_groups) < 3:
            return []
        from itertools import combinations, product
        split_moves = []
        for flower_centers in combinations(flower_groups.keys(), 3):
            cells_choices = [flower_groups[fc] for fc in flower_centers]
            for combo in product(*cells_choices):
                split_moves.append(list(combo))
        return split_moves
    def get_legal_moves(self):
        legal_moves = []
        for cell, piece in list(self.plateau.pieces.items()):
            if isinstance(piece, tuple):
                for i, subpiece in enumerate(piece):
                    if isinstance(subpiece, Chapeau) and subpiece.couleur == self.players[self.current_player].couleur and subpiece.peut_bouger():
                        moves = subpiece.mouvements_possibles(self.plateau)
                        moves = {dest for dest in moves if dest != cell}
                        for dest in moves:
                            legal_moves.append((0, cell, dest, {"tuple_index": i}))
            else:
                if piece.couleur == self.players[self.current_player].couleur and piece.peut_bouger():
                    moves = piece.mouvements_possibles(self.plateau)
                    for dest in moves:
                        if dest not in self.plateau.pieces:
                            legal_moves.append((0, cell, dest))
                        else:
                            occupant = self.plateau.pieces[dest]
                            if occupant.couleur == piece.couleur:
                                if isinstance(piece, (Unite, Double)) and isinstance(occupant, (Unite, Double)):
                                    fused = self.fuse(piece, occupant, dest)
                                    if isinstance(fused, (Double, Triple)):
                                        r_moves = fused.mouvements_possibles(self.plateau)
                                        r_moves = {r for r in r_moves if r != dest}
                                        for r_dest in r_moves:
                                            legal_moves.append((0, cell, dest, {"rebond": (0, dest, r_dest)}))
                            else:
                                if (isinstance(piece, Double) and isinstance(occupant, Unite)) or \
                                   (isinstance(piece, Triple) and isinstance(occupant, Double)):
                                    legal_moves.append((0, cell, dest, {"capture": True}))
        for cell, piece in list(self.plateau.pieces.items()):
            if not isinstance(piece, tuple) and piece.couleur == self.players[self.current_player].couleur and piece.peut_bouger():
                if isinstance(piece, Double) and not getattr(piece, "just_fused", False):
                    split_moves = self.generate_split_moves(cell)
                    for split_move in split_moves:
                        legal_moves.append((1, cell, split_move))
        return legal_moves
    def can_split(self, piece):
        free_cells = self.plateau.cases_libres()
        valid_cells = []
        for cell in free_cells:
            if cell in self.plateau.casesinterdites:
                continue
            fleurs = self.plateau.liste_fleurs_possible(cell)
            if hexagone(0,0,0) in fleurs:
                fleurs.remove(hexagone(0,0,0))
            if fleurs:
                valid_cells.append(cell)
        flower_groups = {}
        for cell in valid_cells:
            for center in self.plateau.liste_fleurs_possible(cell):
                if center == hexagone(0,0,0):
                    continue
                flower_groups.setdefault(center, []).append(cell)
        return len(flower_groups) >= 3
    def fuse(self, piece1, piece2, position):
        if isinstance(piece1, Unite) and isinstance(piece2, Unite):
            return Double(piece1.couleur, position)
        elif (isinstance(piece1, Unite) and isinstance(piece2, Double)) or (isinstance(piece1, Double) and isinstance(piece2, Unite)):
            return Triple(piece1.couleur, position)
        elif isinstance(piece1, Double) and isinstance(piece2, Double):
            return Quadruple(piece1.couleur, position)
        else:
            return piece1
    def apply_move(self, move):
        fusion_move = False
        if len(move) == 4 and "rebond" in move[3]:
            move_type, origin, fusion_dest, extra = move
            piece = self.plateau.pieces.get(origin, None)
            if piece is None:
                return False, fusion_move
            occupant = self.plateau.pieces.get(fusion_dest, None)
            if occupant is None or occupant.couleur != piece.couleur:
                return False, fusion_move
            fused_piece = self.fuse(piece, occupant, fusion_dest)
            del self.plateau.pieces[origin]
            self.plateau.pieces[fusion_dest] = fused_piece
            rebond_move = extra["rebond"]
            if len(rebond_move) != 3 or rebond_move[0] != 0 or rebond_move[1] != fusion_dest:
                return False, fusion_move
            r_dest = rebond_move[2]
            if r_dest not in fused_piece.mouvements_possibles(self.plateau):
                return False, fusion_move
            self.plateau.deplacer_piece(fusion_dest, r_dest)
            fused_piece.position = r_dest
            return True, False
        elif len(move) == 4 and "tuple_index" in move[3]:
            move_type, origin, dest, extra = move
            tuple_index = extra["tuple_index"]
            cell_content = self.plateau.pieces.get(origin, None)
            if not cell_content or not isinstance(cell_content, tuple):
                return False, fusion_move
            try:
                moving_hat = cell_content[tuple_index]
            except IndexError:
                return False, fusion_move
            if not isinstance(moving_hat, Chapeau):
                return False, fusion_move
            new_list = list(cell_content)
            del new_list[tuple_index]
            if len(new_list) == 0:
                del self.plateau.pieces[origin]
            elif len(new_list) == 1:
                self.plateau.pieces[origin] = new_list[0]
            else:
                self.plateau.pieces[origin] = tuple(new_list)
            if dest in self.plateau.pieces:
                dest_content = self.plateau.pieces[dest]
                if isinstance(dest_content, tuple) or isinstance(dest_content, Chapeau):
                    return False, fusion_move
                dest_content.immobilisee = True
                self.plateau.pieces[dest] = (dest_content, moving_hat)
            else:
                self.plateau.pieces[dest] = moving_hat
            moving_hat.position = dest
            return True, False
        elif move[0] == 0 and len(move) == 3:
            move_type, origin, dest = move
            piece = self.plateau.pieces.get(origin, None)
            if piece is None or isinstance(piece, tuple):
                return False, fusion_move
            if dest not in self.plateau.pieces:
                self.plateau.deplacer_piece(origin, dest)
                return True, False
            else:
                return False, fusion_move
        elif move[0] == 0 and len(move) == 4 and "capture" in move[3]:
            move_type, origin, dest, extra = move
            piece = self.plateau.pieces.get(origin, None)
            if piece is None:
                return False, fusion_move
            cell_content = self.plateau.pieces.get(dest, None)
            if cell_content is None or cell_content.couleur == piece.couleur:
                return False, fusion_move
            if isinstance(piece, Double) and isinstance(cell_content, Unite):
                del self.plateau.pieces[dest]
                del self.plateau.pieces[origin]
                piece.position = dest
                self.plateau.pieces[dest] = piece
                return True, False
            elif isinstance(piece, Triple) and isinstance(cell_content, Double):
                del self.plateau.pieces[dest]
                del self.plateau.pieces[origin]
                piece.position = dest
                self.plateau.pieces[dest] = piece
                return True, False
            else:
                return False, fusion_move
        elif move[0] == 1:
            piece = self.plateau.pieces.get(move[1], None)
            if not piece or not isinstance(piece, Double):
                return False, fusion_move
            if getattr(piece, "just_fused", False):
                return False, fusion_move
            split_positions = move[2]
            del self.plateau.pieces[move[1]]
            for cell in split_positions:
                new_piece = Unite(piece.couleur, cell)
                self.plateau.pieces[cell] = new_piece
            return True, fusion_move
        return True, fusion_move
    def check_win(self):
        for cell, content in self.plateau.pieces.items():
            if isinstance(content, tuple):
                occupant, chapeau = content
                if isinstance(occupant, Quadruple) and occupant.couleur == chapeau.couleur:
                    return occupant.couleur
        return None
    def render(self, mode='human'):
        pygame.init()
        screen = pygame.display.set_mode((800, 600))
        afficher_plateau(screen, self.plateau, 40)
        pygame.display.flip()

#############################
# FONCTIONS D'AFFICHAGE (pygame)
#############################
def afficher_plateau(screen, plateau, size, highlighted=None, blocked=None):
    if blocked is None:
        blocked = set()
    screen.fill((255, 255, 255))
    for hex_case in plateau.plateau_hexagonal_complet:
        q, r, s = hex_case.q, hex_case.r, hex_case.s
        x = size * (3/2 * q) + 400
        y = size * (math.sqrt(3) * (r + q/2)) + 300
        color = (200, 200, 200)
        if hex_case in plateau.casesinterdites:
            color = (0, 0, 0)
        elif highlighted and hex_case in highlighted:
            color = (255, 255, 0)
        elif hex_case in blocked:
            color = (150, 150, 150)
        points = [(x + size * math.cos(math.radians(angle)),
                   y + size * math.sin(math.radians(angle))) for angle in range(0, 360, 60)]
        pygame.draw.polygon(screen, color, points, 0)
        pygame.draw.polygon(screen, (0, 0, 0), points, 1)
        if hex_case in plateau.pieces:
            content = plateau.pieces[hex_case]
            if isinstance(content, tuple):
                if all(isinstance(item, Chapeau) for item in content):
                    if len(content) == 2:
                        dessiner_triangle(screen, x + (size // 4), y, size, content[0].couleur)
                        dessiner_triangle(screen, x - (size // 4), y, size, content[1].couleur)
                    else:
                        print("Cas inattendu pour tuple de chapeaux")
                else:
                    occupant, hat = content
                    piece_color = (255, 0, 0) if occupant.couleur == "rouge" else (0, 0, 255)
                    pygame.draw.circle(screen, piece_color, (int(x), int(y)), size // 3)
                    font = pygame.font.Font(None, size)
                    text = font.render("P", True, (0, 0, 0))
                    screen.blit(text, (x - size // 6, y - size // 6))
                    dessiner_triangle(screen, x + (size // 4), y, size, hat.couleur)
            elif isinstance(content, Chapeau):
                dessiner_triangle(screen, x + (size // 4), y, size, content.couleur)
            else:
                piece_color = (255, 0, 0) if content.couleur=="rouge" else (0, 0, 255)
                pygame.draw.circle(screen, piece_color, (int(x), int(y)), size // 3)
                if isinstance(content, Double):
                    afficher_nombre(screen, x, y, size, "2")
                elif isinstance(content, Triple):
                    afficher_nombre(screen, x, y, size, "3")
                elif isinstance(content, Quadruple):
                    afficher_nombre(screen, x, y, size, "4")
    pygame.display.flip()

def dessiner_triangle(screen, x, y, size, couleur):
    triangle_offset = size // 3
    if couleur == "rouge":
        triangle_points = [(x + triangle_offset, y),
                           (x + 2 * triangle_offset, y - triangle_offset),
                           (x + 2 * triangle_offset, y + triangle_offset)]
        pygame.draw.polygon(screen, (255, 0, 0), triangle_points, 0)
    elif couleur == "bleu":
        triangle_points = [(x - triangle_offset, y),
                           (x - 2 * triangle_offset, y - triangle_offset),
                           (x - 2 * triangle_offset, y + triangle_offset)]
        pygame.draw.polygon(screen, (0, 0, 255), triangle_points, 0)

def afficher_nombre(screen, x, y, size, nombre):
    font = pygame.font.Font(None, size)
    text = font.render(nombre, True, (0, 0, 0))
    text_rect = text.get_rect(center=(int(x), int(y)))
    screen.blit(text, text_rect)

#############################
# ALPHA ZERO : RÉSEAU DE NEURONES et MCTS
#############################
# RÉSEAU : prend l'observation (vector de dimension n_cells) et produit une politique sur MAX_ACTIONS et une valeur
class AlphaZeroNet(nn.Module):
    def __init__(self, input_dim, hidden_dim=256, output_policy_dim=1000):
        super(AlphaZeroNet, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        # Tête politique
        self.policy_head = nn.Linear(hidden_dim, output_policy_dim)
        # Tête valeur
        self.value_head = nn.Linear(hidden_dim, 1)
    def forward(self, x):
        # x shape : (batch, input_dim)
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        policy_logits = self.policy_head(x)
        value = torch.tanh(self.value_head(x))
        return policy_logits, value

# MCTS Node
class MCTSNode:
    def __init__(self, env, parent=None, action_taken=None, prior=0.0):
        self.env = env  # une copie de l'environnement
        self.parent = parent
        self.action_taken = action_taken  # action menant à cet état (notation du move)
        self.children = {}  # mapping: action_index -> MCTSNode
        self.N = 0  # nombre de visites
        self.W = 0.0  # somme des valeurs
        self.Q = 0.0  # valeur moyenne
        self.P = prior  # probabilité a priori
    def is_leaf(self):
        return len(self.children) == 0
    def expand(self, legal_moves, priors):
        # legal_moves : liste d'actions (indices correspondants à l'ordre dans get_legal_moves)
        for i, move in enumerate(legal_moves):
            # Pour chaque coup légal, créer un enfant avec la probabilité issue du réseau.
            env_copy_instance = env_copy(self.env)
            valid, _ = env_copy_instance.apply_move(move)
            if not valid:
                continue
            child = MCTSNode(env_copy_instance, parent=self, action_taken=move, prior=priors[i])
            self.children[i] = child

def mcts_search(root, network, n_simulations, c_puct=1.0):
    for sim in range(n_simulations):
        node = root
        search_path = [node]
        # SELECTION
        while not node.is_leaf() and not node.env.done:
            max_ucb = -float('inf')
            best_action = None
            best_child = None
            for action, child in node.children.items():
                ucb = child.Q + c_puct * child.P * math.sqrt(node.N) / (1 + child.N)
                if ucb > max_ucb:
                    max_ucb = ucb
                    best_action = action
                    best_child = child
            node = best_child
            search_path.append(node)
        # ÉVALUATION
        if node.env.done:
            win = node.env.check_win()
            value = 1 if win == "rouge" else -1 if win is not None else 0
        else:
            obs = node.env.get_observation()
            obs_tensor = torch.FloatTensor(obs).unsqueeze(0)  # shape (1, n_cells)
            policy_logits, value = network(obs_tensor)
            value = value.item()
            legal_moves = node.env.get_legal_moves()
            L = len(legal_moves)
            # Prendre les L premières dimensions du vecteur de politique
            policy = F.softmax(policy_logits[0][:L], dim=0).detach().cpu().numpy()
            node.expand(legal_moves, policy)
        # BACKPROPAGATION
        for n in reversed(search_path):
            n.N += 1
            n.W += value
            n.Q = n.W / n.N
            value = -value
    # Construction de la distribution de visites pour la racine
    num_children = len(root.children)
    visits = np.array([root.children[i].N if i in root.children else 0 for i in range(num_children)])
    if visits.sum() > 0:
        pi = visits / visits.sum()
    else:
        # Si aucune visite n'est enregistrée, renvoyer une distribution uniforme
        pi = np.ones(num_children) / num_children if num_children > 0 else np.array([])
    return pi


# Fonction de self-play avec MCTS
def self_play_episode(network, n_mcts_simulations, temperature):
    import time
    env = HexGameEnv()
    states, mcts_pis, current_players = [], [], []
    move_count = 0
    start_time = time.time()
    
    while not env.done:
        move_count += 1
        print(f"\n--- Move {move_count} ---")
        print(f"Current player: {env.players[env.current_player].couleur}")
        
        legal_moves = env.get_legal_moves()
        print(f"Legal moves count: {len(legal_moves)}")
        if len(legal_moves) == 0:
            print("Aucun coup légal. Fin de la partie.")
            break

        # Création d'une racine pour MCTS à partir d'une copie de l'environnement
        root = MCTSNode(env_copy(env))
        pi = mcts_search(root, network, n_mcts_simulations)
        print(f"Distribution π obtenue (len={len(pi)}): {pi}")
        if len(pi) == 0:
            print("Distribution π vide. Fin de la partie.")
            break

        # On padde la distribution π pour qu'elle ait la dimension fixe définie par MAX_ACTIONS
        fixed_pi = np.zeros(HexGameEnv.MAX_ACTIONS)
        L = len(pi)
        fixed_pi[:L] = pi

        # Sélection de l'action selon la température
        if temperature > 0:
            action_index = np.random.choice(len(pi), p=pi)
        else:
            action_index = np.argmax(pi)
        print(f"Action index choisi: {action_index}")

        # Appel de env.step() avec l'action choisie (en supposant que pour le joueur "rouge" l'action est un index)
        observation, reward, terminated, truncated, info = env.step(action_index)
        print(f"Reward: {reward}, terminated: {terminated}, truncated: {truncated}")
        
        # Enregistrer l'état, la distribution et le joueur courant
        states.append(env.get_observation())
        mcts_pis.append(fixed_pi)
        current_players.append(env.players[env.current_player].couleur)
        
        if move_count % 10 == 0:
            elapsed = time.time() - start_time
            print(f"Après {move_count} coups, temps écoulé: {elapsed:.2f} secondes")
    
    total_time = time.time() - start_time
    print(f"\nÉpisode self-play terminé après {move_count} coups en {total_time:.2f} secondes.")
    
    # Définir le résultat z de la partie
    win = env.check_win()
    if win is None:
        z = 0
    elif win == "rouge":
        z = 1
    else:
        z = -1

    training_examples = []
    for state, pi, player in zip(states, mcts_pis, current_players):
        # Si le joueur courant est "rouge", la valeur cible est z, sinon -z
        value = z if player == "rouge" else -z
        training_examples.append((state, pi, value))
    
    return training_examples

# Fonction de mise à jour du réseau
def train_network(network, optimizer, training_examples, epochs):
    network.train()
    for epoch in range(epochs):
        total_loss = 0.0
        for state, pi_target, z_target in training_examples:
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            target_pi = torch.FloatTensor(pi_target).unsqueeze(0)
            target_value = torch.FloatTensor([z_target]).unsqueeze(0)
            pred_logits, pred_value = network(state_tensor)
            loss_policy = -torch.sum(target_pi * F.log_softmax(pred_logits, dim=1))
            loss_value = F.mse_loss(pred_value, target_value)
            loss = loss_policy + loss_value
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"Epoch {epoch+1}/{epochs} Loss: {total_loss/len(training_examples):.4f}")

#############################
# MAIN TRAINING LOOP pour AlphaZero
#############################
if __name__ == "__main__":
    from torch.utils.tensorboard import SummaryWriter
    writer = SummaryWriter(log_dir="./runs/alpha_zero")
    
    temp_env = HexGameEnv()
    input_dim = temp_env.n_cells           # Dimension de l'observation (vecteur)
    output_policy_dim = HexGameEnv.MAX_ACTIONS  # Dimension fixe de la tête de politique
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    network = AlphaZeroNet(input_dim, hidden_dim=256, output_policy_dim=output_policy_dim).to(device)
    optimizer = optim.Adam(network.parameters(), lr=0.001)
    
    checkpoint_path = "alpha_zero_checkpoint.pth"
    if os.path.exists(checkpoint_path):
        network.load_state_dict(torch.load(checkpoint_path, map_location=device))
        print("Checkpoint chargé.")
    else:
        print("Pas de checkpoint trouvé, début d'un nouvel entraînement.")
    
    num_iterations = 10         # Itérations globales d'entraînement
    num_selfplay_games = 50      # Parties de self-play par itération
    n_mcts_simulations = 50      # Simulations MCTS par coup
    training_epochs = 5          # Epochs de mise à jour par itération
    temperature = 1.0            # Température pour la sélection d'action
    replay_buffer = []           # Stockage des exemples d'entraînement
    
    for iteration in range(num_iterations):
        print(f"\n=== Itération {iteration+1}/{num_iterations} ===")
        iteration_examples = []
        total_reward = 0  # Réinitialisation du total de récompenses pour cette itération
        
        for game in range(num_selfplay_games):
            print(f"Self-play game {game+1}/{num_selfplay_games}")
            examples = self_play_episode(network, n_mcts_simulations, temperature)
            print('ici?')
            iteration_examples.extend(examples)
            print('la?')
            # On peut par exemple extraire la récompense finale de l'épisode self-play
            # et l'additionner à total_reward
            if examples:
                # Supposons que le résultat z est contenu dans les exemples (vous devez adapter selon votre implémentation)
                total_reward += examples[-1][2]
        
        replay_buffer.extend(iteration_examples)
        
        # Entraînement du réseau et calcul de la perte moyenne
        avg_loss = train_network(network, optimizer, iteration_examples, training_epochs)
        
        # Enregistrer les scalaires dans TensorBoard
        writer.add_scalar("Loss/epoch", avg_loss, iteration)
        writer.add_scalar("Reward/epoch", total_reward, iteration)
        
        # Sauvegarder le modèle
        torch.save(network.state_dict(), checkpoint_path)
        print(f"Checkpoint sauvegardé dans {checkpoint_path}")
        
        # Réduire la température si nécessaire
        temperature = max(0.1, temperature * 0.95)
    
    writer.close()
    print("Entraînement terminé.")
