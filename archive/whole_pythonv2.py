"""
============================================================
 Jeu de Stratégie Hexagonal – Code complet avec environnement RL
============================================================

Ce code regroupe :
  - Les définitions de classes pour les hexagones, les pièces (Unite, Double, Triple, Quadruple, Chapeau)
  - La classe Plateau_hexagonal qui gère le plateau, les cases interdites, les fleurs, etc.
  - Les classes de Player (HumanPlayer et un AIPlayer minimal)
  - Quelques fonctions utilitaires (conversion pixel<->hex, affichage via pygame, etc.)
  - Une fonction initialiser_configuration() pour placer les unités et les chapeaux initiaux
  - La classe Gym HexGameEnv qui définit l’environnement pour le reinforcement learning
"""

#############################
# Imports et définitions de base
#############################
import math, pygame, random, numpy as np, gymnasium as gym, copy
from gymnasium import spaces

# ---------------------------
# Classe hexagone (coordonnées cubiques)
# ---------------------------
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
        # On ne retourne que les cases présentes dans le plateau complet.
        return set(potential).intersection(plateau.plateau_hexagonal_complet)

#############################
# Fonctions utilitaires pour conversion
#############################
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
# Définition des pièces
#############################
class Piece:
    def __init__(self, couleur, position):
        self.couleur = couleur
        self.position = position
        self.immobilisee = False
        # Attribut servant à indiquer si la pièce issue d'une fusion (effet rebond) ne peut pas être splittée immédiatement.
        self.just_fused = False  
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
            # Les unités ne peuvent pas être placées sur une case interdite (cases sombre)
            if voisin in plateau.casesinterdites:
                continue
            if voisin in plateau.cases_libres():
                mouvements.add(voisin)
            elif voisin in plateau.pieces:
                content = plateau.pieces[voisin]
                # Si la case contient déjà un tuple (champoté) ou un chapeau, on n'y va pas.
                if isinstance(content, tuple) or isinstance(content, Chapeau):
                    continue
                # Permettre la fusion avec une Unite ou un Double allié
                if content.couleur == self.couleur and (isinstance(content, Unite) or isinstance(content, Double)):
                    mouvements.add(voisin)
        return mouvements

class Double(Piece):
    def mouvements_possibles(self, plateau):
        """
        Le Double (pile de 2) se déplace exactement de 2 cases.
        Pour chaque niveau, la case considérée doit ne pas être interdite et être libre ou être la position de départ (pour revenir sur soi).
        Au niveau final, la destination est autorisée si elle est libre, ou si elle contient :
          - une pièce alliée (fusion possible)
          - ou une Unite ennemie (pour "manger")
        """
        start = self.position
        destinations = set()

        # Niveau 1
        level1 = { n for n in start.neighbors(plateau)
                   if n not in plateau.casesinterdites and (n in plateau.cases_libres() or n == start) }
        # Niveau 2
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
                    elif isinstance(content, Unite):  # Permet "manger"
                        destinations.add(n)
        return destinations

class Triple(Piece):
    def mouvements_possibles(self, plateau):
        """
        Le Triple se déplace exactement de 3 cases en passant par 2 niveaux intermédiaires.
        Au niveau final, la destination est autorisée si elle est libre ou contient un Double ennemi.
        """
        start = self.position
        destinations = set()

        # Niveau 1
        level1 = {n for n in start.neighbors(plateau)
                  if n not in plateau.casesinterdites and (n in plateau.cases_libres() or n == start)}
        # Niveau 2
        level2 = set()
        for cell in level1:
            for n in cell.neighbors(plateau):
                if n not in plateau.casesinterdites and (n in plateau.cases_libres() or n == start):
                    level2.add(n)
        # Niveau 3
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
        # Une pile de 4 est immobile.
        return set()

class Chapeau(Piece):
    def mouvements_possibles(self, plateau):
        """
        Un chapeau se déplace d'une case adjacente.
        Il ne peut pas aller sur une case interdite et ne peut être placé sur une case contenant déjà un chapeau (ou un tuple, c'est-à-dire déjà champoté).
        Si le chapeau atterrit sur une case occupée, il applique l'effet "champoter" qui immobilise la pièce présente.
        """
        if not self.peut_bouger():
            return set()
        moves = set()
        for voisin in self.position.neighbors(plateau):
            if voisin in plateau.casesinterdites:
                continue
            # Le chapeau peut se déplacer sur une case occupée à condition qu'elle ne contienne pas déjà un chapeau ou un tuple
            if voisin in plateau.pieces:
                content = plateau.pieces[voisin]
                if isinstance(content, tuple) or isinstance(content, Chapeau):
                    continue
            moves.add(voisin)
        return moves

#############################
# Plateau_hexagonal et gestion du plateau
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
        # Création des fleurs : chaque fleur est constituée de la case interdite centrale + ses 6 voisins.
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
        # Autorise le placement sur toute case du plateau non interdite, OU pour un chapeau qui peut être placé sur la case interdite centrale au début.
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
# Configuration initiale
#############################
def initialiser_configuration(plateau, joueur1, joueur2):
    # Placement des unités (phase de placement préconfigurée)
    rouge_positions = [(-1, -1, 2), (4, -1, -3), (3, -3, 0)]
    for pos in rouge_positions:
        cell = hexagone(*pos)
        plateau.placer_piece(Double("rouge", cell), cell)
    bleu_positions = [(0, -3, 3), (0, 3, -3), (-1, 2, -1), (-2, -2, 4),
                      (-2, 1, 1), (-3, 0, 3), (-3, 4, -1), (-4, 2, 2)]
    for pos in bleu_positions:
        cell = hexagone(*pos)
        plateau.placer_piece(Unite("bleu", cell), cell)
    # Placer les chapeaux initiaux sur la case centrale (même si cette case est interdite, c'est l'unique exception)
    plateau.pieces[hexagone(0, 0, 0)] = (Chapeau("rouge", hexagone(0, 0, 0)), Chapeau("bleu", hexagone(0, 0, 0)))

def initialiser_configuration_test(plateau, joueur1, joueur2):
    # Vider le plateau (optionnel si vous souhaitez partir d'un plateau vierge)
    plateau.pieces = {}
    
    # Placer un Double allié (pile de 2) pour le joueur 1 ("rouge")
    allied_cell = hexagone(-1, 0, 1)
    plateau.placer_piece(Double("rouge", allied_cell), allied_cell)
    
    # Placer une Unite ennemie pour le joueur 2 ("bleu")
    enemy_cell = hexagone(-1, 2, -1)
    plateau.placer_piece(Unite("bleu", enemy_cell), enemy_cell)
    
    # On n'ajoute pas les chapeaux initiaux pour ce test minimal


#############################
# Définition des joueurs
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
# Environnement RL (Gym)
#############################
class HexGameEnv(gym.Env):
    metadata = {"render.modes": ["human"]}
    MAX_MOVES_PER_PLAYER = 40  # Maximum de coups par joueur
    MAX_ACTIONS = 1000
    def __init__(self):
        super(HexGameEnv, self).__init__()
        self.plateau = Plateau_hexagonal()
        # Création des joueurs : le joueur 0 (agent) et le joueur 1 (adversaire random)
        self.players = [Player("rouge", "Agent"), Player("bleu", "Random")]
        initialiser_configuration(self.plateau, self.players[0], self.players[1])
        self.current_player = 0  # L'agent commence (joueur 0)
        self.history = []
        self.done = False
        self.build_cell_index()  # Pour l'observation
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
        # Si c'est le tour de l'adversaire random, ignorer l'action fournie
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

        # Pour le joueur agent, l'action est un indice dans legal_moves
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
                    obs[idx] = 99  # Code pour champoté
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
        """
        Retourne une liste de combinaisons possibles pour splitter un Double.
        Chaque combinaison est une liste de 3 cellules (issues de 3 fleurs distinctes, hors la fleur centrale)
        qui respectent :
            - La cellule doit être libre (non occupée et non interdite).
            - Chaque cellule provient d'une fleur différente (la fleur centrale est exclue).
        """
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
        # Regrouper les cellules par fleur (clé = centre de la fleur)
        flower_groups = {}
        for cell in valid_cells:
            for center in self.plateau.liste_fleurs_possible(cell):
                if center == hexagone(0, 0, 0):
                    continue
                flower_groups.setdefault(center, []).append(cell)
        # Il faut au moins 3 fleurs distinctes
        if len(flower_groups) < 3:
            return []
        from itertools import combinations, product
        split_moves = []
        # Choisir 3 fleurs parmi celles disponibles
        for flower_centers in combinations(flower_groups.keys(), 3):
            # Pour chaque trio de fleurs, générer toutes les combinaisons en prenant une cellule par fleur
            cells_choices = [flower_groups[fc] for fc in flower_centers]
            for combo in product(*cells_choices):
                split_moves.append(list(combo))
        return split_moves


    def get_legal_moves(self):
        legal_moves = []
        # Traitement pour les pièces dans un tuple (état champoté) : seuls les chapeaux peuvent bouger.
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
                            # Coup normal : déplacement simple
                            legal_moves.append((0, cell, dest))
                        else:
                            occupant = self.plateau.pieces[dest]
                            if occupant.couleur == piece.couleur:
                                # Fusion alliée : on génère les coups avec rebond uniquement pour Double et Triple
                                if isinstance(piece, (Unite, Double)) and isinstance(occupant, (Unite, Double)):
                                    fused = self.fuse(piece, occupant, dest)
                                    if isinstance(fused, (Double, Triple)):
                                        r_moves = fused.mouvements_possibles(self.plateau)
                                        r_moves = {r for r in r_moves if r != dest}
                                        for r_dest in r_moves:
                                            legal_moves.append((0, cell, dest, {"rebond": (0, dest, r_dest)}))
                            else:
                                # Capture ennemie : Par exemple, Double mange Unite ou Triple mange Double.
                                if (isinstance(piece, Double) and isinstance(occupant, Unite)) or \
                                   (isinstance(piece, Triple) and isinstance(occupant, Double)):
                                    legal_moves.append((0, cell, dest, {"capture": True}))
        # Coup de split pour un Double splittable (et non issu d'une fusion immédiate)
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
        # 1. Fusion avec rebond (notation sur 4 éléments avec clé "rebond")
        if len(move) == 4 and "rebond" in move[3]:
            # Format : (0, origin, fusion_dest, {"rebond": (0, fusion_dest, r_dest)})
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
            rebond_move = extra["rebond"]  # Doit être de la forme (0, fusion_dest, r_dest)
            if len(rebond_move) != 3 or rebond_move[0] != 0 or rebond_move[1] != fusion_dest:
                return False, fusion_move
            r_dest = rebond_move[2]
            if r_dest not in fused_piece.mouvements_possibles(self.plateau):
                return False, fusion_move
            self.plateau.deplacer_piece(fusion_dest, r_dest)
            fused_piece.position = r_dest
            return True, False

        # 2. Déplacement d'un chapeau contenu dans un tuple (champoté) via clé "tuple_index"
        elif len(move) == 4 and "tuple_index" in move[3]:
            # Format : (0, origin, dest, {"tuple_index": i})
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

        # 3. Déplacement normal (sans fusion ni capture) pour une pièce qui n'est pas dans un tuple
        elif move[0] == 0 and len(move) == 3:
            # On ne doit utiliser cette branche que pour un déplacement simple
            move_type, origin, dest = move
            piece = self.plateau.pieces.get(origin, None)
            if piece is None or isinstance(piece, tuple):
                return False, fusion_move
            if dest not in self.plateau.pieces:
                self.plateau.deplacer_piece(origin, dest)
                return True, False
            else:
                # Si la destination est occupée, on ne doit pas avoir un coup sans capture ni rebond dans la nouvelle convention.
                return False, fusion_move

        # 4. Capture ennemie : coup noté sur 4 éléments avec clé "capture"
        elif move[0] == 0 and len(move) == 4 and "capture" in move[3]:
            # Format : (0, origin, dest, {"capture": True})
            move_type, origin, dest, extra = move
            piece = self.plateau.pieces.get(origin, None)
            if piece is None:
                return False, fusion_move
            cell_content = self.plateau.pieces.get(dest, None)
            if cell_content is None or cell_content.couleur == piece.couleur:
                return False, fusion_move
            # Exemple : Double mange Unite
            if isinstance(piece, Double) and isinstance(cell_content, Unite):
                del self.plateau.pieces[dest]  # On enlève l'unité ennemie capturée
                del self.plateau.pieces[origin]
                piece.position = dest
                self.plateau.pieces[dest] = piece  # Le même objet Double est replacé à la destination
                return True, False
            # Exemple : Triple mange Double
            elif isinstance(piece, Triple) and isinstance(cell_content, Double):
                del self.plateau.pieces[dest]
                del self.plateau.pieces[origin]
                piece.position = dest
                self.plateau.pieces[dest] = piece
                return True, False
            else:
                return False, fusion_move

        # 5. Coup de split pour un Double (inchangé, sauf la notation)
        elif move[0] == 1:
            # Format : (1, origin, [cell1, cell2, cell3])
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
        # Condition de victoire : un chapeau placé sur une pile de 4 alliée (ou sur un tuple dont l'occupant est Quadruple)
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
# Fonctions d'affichage (via pygame)
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
# Exemple d'exécution en mode self-play (RL)
#############################
from stable_baselines3 import PPO
# Pour l'exemple, nous réimportons HexGameEnv depuis ce module même.
# Assurez-vous que le chemin d'importation est correct si vous déplacez ce fichier.
import pygame

AI_TYPE = "alphabeta"   # ou "rl"

if __name__ == "__main__":
    env = HexGameEnv()

    if AI_TYPE == "rl":
        model = PPO.load("ppo_hex_game", env=env)
        model.set_env(env)
        obs, info = env.reset()
        done = False
        total_reward = 0
        while not done:
            if env.current_player == 0:
                action, _ = model.predict(obs)
            else:
                legal_moves = env.get_legal_moves()
                if legal_moves:
                    action = random.randint(0, len(legal_moves) - 1)
                else:
                    action = 0
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            total_reward += reward
            env.render()
            pygame.time.wait(500)
        print("Partie terminée. Reward total :", total_reward)

    elif AI_TYPE == "alphabeta":
        search_depth = 2
        player_color = "rouge"
        obs, info = env.reset()
        done = False
        total_reward = 0
        while not done:
            if env.current_player == 0:
                print("Tour du joueur 0 (alphabeta)")
                best_mv, value = best_move(env, search_depth, player_color)
                print(f"   => Meilleur coup = {best_mv}, valeur estimée = {value}")
                move = best_mv
            else:
                print("Tour du joueur 1 (random)")
                legal_moves = env.get_legal_moves()
                if legal_moves:
                    move = random.choice(legal_moves)
                else:
                    break
                print(f"   => Coup random = {move}")
            valid, fusion_move = env.apply_move(move)
            if valid:
                env.history.append(move)
            else:
                total_reward -= 0.5
            if valid and not fusion_move:
                env.current_player = 1 - env.current_player
            winner = env.check_win()
            if winner is not None:
                done = True
                if winner == env.players[0].couleur:
                    total_reward += 1
                else:
                    total_reward -= 1
            env.render()
            pygame.time.wait(500)
        print("Partie terminée. Reward total :", total_reward)
