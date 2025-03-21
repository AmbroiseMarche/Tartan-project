"""
============================================================
 Jeu de Stratégie Hexagonal – Code complet avec environnement RL
============================================================

Ce code regroupe :
  - Les définitions de classes pour les hexagones, les pièces (Unité, Double, Triple, Quadruple, Chapeau, ChapeauxInit)
  - La classe Plateau_hexagonal qui gère le plateau, les cases interdites, les fleurs, etc.
  - Les classes de Player (HumanPlayer et un AIPlayer minimal)
  - Quelques fonctions utilitaires (conversion pixel<->hex, affichage via pygame, etc.)
  - Une fonction initialiser_configuration() pour placer les unités et le chapeaux init
  - La classe Gym HexGameEnv qui définit l’environnement pour le reinforcement learning

Pour lancer une partie en mode self-play (ici aléatoire pour la démonstration), exécutez ce script.
"""

#############################
# Imports et définitions de base
#############################
import math, pygame, random, numpy as np, gymnasium as gym
from gymnasium import spaces
import copy
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

# ---------------------------
# Fonctions utilitaires pour conversion
# ---------------------------
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
        self.just_formed = False
        self.value = None
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
            if voisin in plateau.cases_libres():
                mouvements.add(voisin)
            elif voisin in plateau.pieces:
                content = plateau.pieces[voisin]
                # Si la case contient un tuple (de chapeaux), on ignore
                if isinstance(content, tuple):
                    continue
                if isinstance(content, Chapeau):
                    continue
                if content.couleur == self.couleur and (isinstance(content, Unite) or isinstance(content, Double)):
                    mouvements.add(voisin)
        return mouvements


class Double(Piece):
    def mouvements_possibles(self, plateau):
        """
        Le Double se déplace exactement de 2 cases en passant par un niveau intermédiaire.
        Pour chaque niveau, la case considérée doit ne pas être interdite et être libre ou être la position de départ (permettant de revenir sur soi-même).
        Au niveau final, la destination est autorisée si elle est libre, ou, si occupée,
          - par une pièce alliée (fusion possible),
          - ou par une Unite ennemie (pour être mangée).
        """
        start = self.position
        destinations = set()

        # Niveau 1 : voisins immédiats de la position, autorisés si non interdits et libres OU égaux à start.
        level1 = { n for n in start.neighbors(plateau)
                   if n not in plateau.casesinterdites and (n in plateau.cases_libres() or n == start) }

        # Niveau 2 (destination) : pour chaque cellule du niveau 1, regarder ses voisins
        for cell in level1:
            for n in cell.neighbors(plateau):
                if n in plateau.casesinterdites:
                    continue
                if n in plateau.cases_libres() or n == start:
                    destinations.add(n)
                elif n in plateau.pieces:
                    content = plateau.pieces[n]
                    # Si la case contient un tuple (par exemple, deux chapeaux déjà présents), on l'ignore.
                    if isinstance(content, tuple):
                        continue
                    if isinstance(content, Chapeau):
                        continue
                    # Autoriser la destination si la pièce présente est alliée (fusion)...
                    if (content.couleur == self.couleur) and (isinstance(content, Unite) or isinstance(content, Double)):
                        destinations.add(n)
                    # ... ou si c'est une Unite ennemie (pour "manger")
                    elif isinstance(content, Unite):
                        destinations.add(n)
        return destinations



class Triple(Piece):
    def mouvements_possibles(self, plateau):
        """
        Le Triple se déplace exactement de 3 cases en passant par 2 niveaux intermédiaires.
        Pour chaque niveau, la case considérée doit ne pas être interdite et être libre ou égale à la position de départ (permettant de revenir sur soi).
        Au niveau final, la destination doit être libre ou contenir un Double ennemi.
        """
        start = self.position
        destinations = set()

        # Niveau 1 : voisins immédiats qui ne sont pas interdits et qui sont libres ou égaux à start.
        level1 = {n for n in start.neighbors(plateau)
                  if n not in plateau.casesinterdites and (n in plateau.cases_libres() or n == start)}

        # Niveau 2 : pour chaque cellule de niveau 1, prendre les voisins respectant les mêmes conditions.
        level2 = set()
        for cell in level1:
            for n in cell.neighbors(plateau):
                if n not in plateau.casesinterdites and (n in plateau.cases_libres() or n == start):
                    level2.add(n)

        # Niveau 3 (destination) : pour chaque cellule de niveau 2, le voisin final est autorisé
        # s'il n'est pas interdit, et s'il est libre ou égal à start,
        # ou s'il contient un Double ennemi.
        for cell in level2:
            for n in cell.neighbors(plateau):
                if n in plateau.casesinterdites:
                    continue
                if n in plateau.cases_libres() or n == start:
                    destinations.add(n)
                elif n in plateau.pieces:
                    content = plateau.pieces[n]
                    if isinstance(content, tuple):
                        continue
                    if isinstance(content, Chapeau):
                        continue
                    if isinstance(content, Double) and content.couleur != self.couleur:
                        destinations.add(n)
        return destinations


class Quadruple(Piece):
    def mouvements_possibles(self, plateau):
        return set()  # Une pile de 4 est immobile.

class Chapeau(Piece):
    def mouvements_possibles(self, plateau):
        """
        Un chapeau peut se déplacer d'une case adjacente, qu'elle soit libre ou occupée
        par une pièce (alliée ou ennemie) à condition que la case ne contienne pas déjà
        un chapeau ou un tuple (déjà champoté).
        """
        if not self.peut_bouger():
            return set()
        moves = set()
        for voisin in self.position.neighbors(plateau):
            if voisin == self.position:
                continue
            if voisin in plateau.casesinterdites:
                continue
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
# Configuration initiale
#############################
def initialiser_configuration(plateau, joueur1, joueur2):
    # Placement des unités (phase de placement préconfigurée)
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
    # Placer les chapeaux initiaux sur la case centrale
    plateau.pieces[hexagone(0, 0, 0)] = (Chapeau("rouge", hexagone(0, 0, 0)), Chapeau("bleu", hexagone(0, 0, 0)))


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
        # Exemple : récupération d'un clic via pygame (à adapter selon votre interface)
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
        # Ici, on utilisera par exemple une politique RL pour choisir parmi etat_du_jeu['legal_moves']
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
        # Créer les joueurs : pour ce premier entraînement, le joueur 0 (agent) et le joueur 1 (adversaire random)
        self.players = [Player("rouge", "Agent"), Player("bleu", "Random")]
        # Initialiser la configuration (par exemple, le placement initial)
        initialiser_configuration(self.plateau, self.players[0], self.players[1])
        self.current_player = 0  # L'agent commence (joueur 0)
        self.history = []
        self.done = False
        self.build_cell_index()  # pour l'observation, comme précédemment
        self.observation_space = spaces.Box(low=-1, high=100, shape=(self.n_cells,), dtype=np.int32)
        self.action_space = spaces.Discrete(HexGameEnv.MAX_ACTIONS)
        # Nouveaux compteurs pour le nombre de coups effectués par chaque joueur
        self.agent_moves = 0
        self.random_moves = 0
        self.total_moves = 0

    def reset(self, seed=None, options=None):
        if seed is not None:
            # Vous pouvez initialiser le seed ici si nécessaire.
            self.seed_val = seed
        self.plateau = Plateau_hexagonal()
        initialiser_configuration(self.plateau, self.players[0], self.players[1])
        self.current_player = 0
        self.history = []
        self.done = False
        self.build_cell_index()
        # Réinitialiser les compteurs de coups
        self.agent_moves = 0
        self.random_moves = 0
        self.total_moves = 0
        # Retourner l'observation et un dictionnaire d'info vide
        return self.get_observation(), {}



    def step(self, action):
        # Si c'est le tour de l'adversaire random, ignorer l'action fournie
        if self.current_player == 1:
            legal_moves = self.get_legal_moves()
            if legal_moves:
                action = random.choice(legal_moves)
            else:
                # Aucun coup légal pour l'adversaire : passer la main
                self.current_player = 0

        legal_moves = self.get_legal_moves()
        if not legal_moves:
            # Aucun coup légal pour le joueur courant, fin de partie par défaut
            self.done = True
            terminated = True
            truncated = False
            return self.get_observation(), 0, terminated, truncated, {}

        # Si c'est le tour de l'agent, l'action est un indice dans legal_moves
        if self.current_player == 0:
            if action < 0 or action >= len(legal_moves):
                reward = -0.5
                return self.get_observation(), reward, False, False, {"illegal": True}
            move = legal_moves[action]
        else:
            # Pour l'adversaire, on choisit un coup aléatoire
            move = random.choice(legal_moves)

        # Appliquer le coup et récupérer validité et fusion_move
        valid, fusion_move = self.apply_move(move)
        if valid:
            self.history.append(move)
            self.total_moves += 1
            if self.current_player == 0:
                self.agent_moves += 1
            else:
                self.random_moves += 1

        # Vérifier si un des joueurs a dépassé le nombre maximum de coups
        if self.agent_moves >= HexGameEnv.MAX_MOVES_PER_PLAYER or self.random_moves >= HexGameEnv.MAX_MOVES_PER_PLAYER:
            self.done = True
            # On considère cela comme une fin d'épisode par "time-out" (truncated)
            terminated = False
            truncated = True
            reward = -1
            return self.get_observation(), reward, terminated, truncated, {}

        # Vérifier si la partie est terminée (victoire/défaite)
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

        # Si le coup est valide et qu'il ne permet pas de rejouer (fusion), on alterne les tours
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

    def get_legal_moves(self):
        legal_moves = []
        # Vérifier d'abord les coups pour les pièces fusionnées (comme avant)
        fused_piece = None
        for cell, piece in list(self.plateau.pieces.items()):
            if isinstance(piece, tuple):
                continue
            if piece.couleur == self.players[self.current_player].couleur and getattr(piece, "just_fused", False):
                fused_piece = (cell, piece)
                break
        if fused_piece is not None:
            cell, piece = fused_piece
            moves = piece.mouvements_possibles(self.plateau)
            moves = {dest for dest in moves if dest != cell}
            for dest in moves:
                legal_moves.append((0, cell, dest))
            return legal_moves

        # Cas général : pour chaque pièce appartenant au joueur courant
        for cell, piece in list(self.plateau.pieces.items()):
            if isinstance(piece, tuple):
                # Si la case contient un tuple, on examine chacun des éléments.
                for i, subpiece in enumerate(piece):
                    if isinstance(subpiece, Chapeau) and subpiece.couleur == self.players[self.current_player].couleur and subpiece.peut_bouger():
                        moves = subpiece.mouvements_possibles(self.plateau)
                        # On ne garde que les coups qui font changer la position (pas de self-loop)
                        moves = {dest for dest in moves if dest != cell}
                        for dest in moves:
                            # On ajoute un champ supplémentaire (l'indice dans le tuple)
                            legal_moves.append((0, cell, dest, i))
            else:
                if piece.couleur == self.players[self.current_player].couleur and piece.peut_bouger():
                    moves = piece.mouvements_possibles(self.plateau)
                    for dest in moves:
                        if dest != cell:
                            legal_moves.append((0, cell, dest))
                    if isinstance(piece, Double) and not getattr(piece, "just_fused", False) and self.can_split(piece):
                        legal_moves.append((1, cell, None))
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
        #print("Application du coup :", move)
        # Traitement des coups de déplacement pour un chapeau extrait d'un tuple (longueur de move == 4)
        if len(move) == 4:
            move_type, origin, dest, hat_index = move
            # Récupérer le contenu de la case d'origine
            cell_content = self.plateau.pieces.get(origin, None)
            if not cell_content or not isinstance(cell_content, tuple):
                return False, False
            #print("Avant extraction, contenu dans", origin, ":", cell_content)
            try:
                moving_hat = cell_content[hat_index]
            except IndexError:
                return False, False
            if not isinstance(moving_hat, Chapeau):
                return False, False
            # Retirer le chapeau du tuple dans l'origine
            new_list = list(cell_content)
            del new_list[hat_index]
            #print("Après extraction, reste dans", origin, ":", new_list)
            if len(new_list) == 0:
                self.plateau.pieces.pop(origin, None)
            elif len(new_list) == 1:
                self.plateau.pieces[origin] = new_list[0]
            else:
                self.plateau.pieces[origin] = tuple(new_list)
            # Mettre à jour la position interne du chapeau AVANT de l'insérer dans la destination
            moving_hat.position = dest
            # Placer le chapeau à la destination
            if dest not in self.plateau.pieces:
                self.plateau.pieces[dest] = moving_hat
            else:
                dest_content = self.plateau.pieces[dest]
                # Si la destination est déjà occupée par un tuple ou un chapeau, le coup est illégal
                if isinstance(dest_content, tuple) or isinstance(dest_content, Chapeau):
                    return False, False
                self.plateau.pieces[dest] = (dest_content, moving_hat)
            #print("Après déplacement, contenu à", origin, ":", self.plateau.pieces.get(origin, None))
            return True, False

        # Traitement des coups normaux (move_type == 0 pour déplacement, move_type == 1 pour split)
        fusion_move = False
        if move[0] == 0:
            move_type, origin, dest = move[0:3]
            piece = self.plateau.pieces.get(origin, None)
            if piece is None:
                return False, fusion_move
            # Si la destination est libre, effectuer un déplacement simple.
            if dest not in self.plateau.pieces:
                self.plateau.deplacer_piece(origin, dest)
                if hasattr(piece, "just_fused") and piece.just_fused:
                    piece.just_fused = False
            else:
                cell_content = self.plateau.pieces[dest]
                # Si c'est un chapeau qui se déplace (et qu'il est seul, pas dans un tuple)
                if isinstance(piece, Chapeau):
                    # On vérifie que la destination ne contient ni un chapeau ni un tuple (champoté)
                    if isinstance(cell_content, Chapeau) or (isinstance(cell_content, tuple) and any(isinstance(item, Chapeau) for item in cell_content)):
                        return False, fusion_move
                    # IMPORTANT : retirer la pièce de l'origine avant d'effectuer le champotage
                    del self.plateau.pieces[origin]
                    # Créer un tuple dans la destination avec l'ancien contenu et le chapeau déplacé
                    self.plateau.pieces[dest] = (cell_content, piece)
                    piece.position = dest
                else:
                    # Fusion de pièces alliées
                    if cell_content.couleur == piece.couleur:
                        new_piece = self.fuse(piece, cell_content, dest)
                        new_piece.just_fused = True
                        del self.plateau.pieces[origin]
                        self.plateau.pieces[dest] = new_piece
                        fusion_move = True
                    else:
                        # Traitement des attaques (ex. Double mange Unite, etc.)
                        if isinstance(piece, Double) and isinstance(cell_content, Unite):
                            del self.plateau.pieces[dest]
                            new_piece = Triple(piece.couleur, dest)
                            del self.plateau.pieces[origin]
                            self.plateau.pieces[dest] = new_piece
                        elif isinstance(piece, Triple) and isinstance(cell_content, Double):
                            del self.plateau.pieces[dest]
                            new_piece = Triple(piece.couleur, dest)
                            del self.plateau.pieces[origin]
                            self.plateau.pieces[dest] = new_piece
                        else:
                            return False, fusion_move
        elif move[0] == 1:
            # Coup de split pour un Double
            piece = self.plateau.pieces.get(move[1], None)
            if not piece or not isinstance(piece, Double):
                return False, fusion_move
            free_cells = list(self.plateau.cases_libres())
            valid_moves = []
            flower_used = set()
            for cell in free_cells:
                if cell in self.plateau.casesinterdites:
                    continue
                fleurs = self.plateau.liste_fleurs_possible(cell)
                fleurs = [f for f in fleurs if f != hexagone(0, 0, 0)]
                for f in fleurs:
                    if f not in flower_used:
                        valid_moves.append(cell)
                        flower_used.add(f)
                        break
                if len(valid_moves) == 3:
                    break
            if len(valid_moves) < 3:
                return False, fusion_move
            del self.plateau.pieces[move[1]]
            for cell in valid_moves:
                new_piece = Unite(piece.couleur, cell)
                self.plateau.pieces[cell] = new_piece
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
# Fonctions alphabeta
#############################

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
        print('piece_name', piece_name)
        val = base_value.get(piece_name, 0)
        print('val', val)   
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
    legal_moves = env.get_legal_moves()
    print(f"[best_move] Nombre de coups légaux : {len(legal_moves)}")
    best_val = -math.inf
    best_moves = []  # Liste de tous les coups ayant la meilleure valeur
    alpha = -math.inf
    beta = math.inf

    for move in legal_moves:
        env_copy_instance = env_copy(env)
        valid, _ = env_copy_instance.apply_move(move)
        if not valid:
            continue

        move_val = alphabeta(env_copy_instance, depth - 1, alpha, beta, False, player_color)
        print(f"   Coup {move}, valeur={move_val}")

        if move_val > best_val:
            best_val = move_val
            best_moves = [move]          # Réinitialiser la liste avec ce nouveau "meilleur" coup
        elif move_val == best_val:
            best_moves.append(move)      # Ajouter ce coup aux "ex æquo"

        alpha = max(alpha, best_val)

    # Choisir un coup aléatoirement parmi ceux qui ont la valeur best_val
    if best_moves:
        chosen_move = random.choice(best_moves)
    else:
        chosen_move = None  # Au cas où il n'y ait aucun coup valide

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
                    # Si tous les éléments du tuple sont des instances de Chapeau,
                # on considère que c'est le cas de la case centrale avec les deux chapeaux.
                if all(isinstance(item, Chapeau) for item in content):
                    # Si on a exactement 2 chapeaux, on les affiche avec un offset à droite et à gauche.
                    if len(content) == 2:
                        dessiner_triangle(screen, x + (size // 4), y, size, content[0].couleur)
                        dessiner_triangle(screen, x - (size // 4), y, size, content[1].couleur)
                    else:
                        print("c'est pas normal")
                else:
                    # Sinon, on suppose que le tuple est de la forme (occupant, chapeau)
                    occupant, hat = content
                    piece_color = (255, 0, 0) if occupant.couleur == "rouge" else (0, 0, 255)
                    pygame.draw.circle(screen, piece_color, (int(x), int(y)), size // 3)
                    font = pygame.font.Font(None, size)
                    text = font.render("P", True, (0, 0, 0))
                    screen.blit(text, (x - size // 6, y - size // 6))
                    dessiner_triangle(screen, x + (size // 4), y, size, hat.couleur)

            elif isinstance(content, Chapeau):
                dessiner_triangle(screen, x + (size//4), y, size, content.couleur)
            else:
                piece_color = (255, 0, 0) if content.couleur=="rouge" else (0, 0, 255)
                pygame.draw.circle(screen, piece_color, (int(x), int(y)), size//3)
                # Pour afficher le nombre sur une pile (Double, Triple, Quadruple)
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
from whole_python import HexGameEnv  # Assurez-vous que le chemin d'importation est correct
import random
import pygame
# Choisissez le type d'IA à utiliser : "rl" ou "alphabeta"
AI_TYPE = "alphabeta"   # ou "rl"

if __name__ == "__main__":
    # Créer l'environnement
    env = HexGameEnv()

    if AI_TYPE == "rl":
        # Charger le modèle entraîné pour l'agent RL (joueur 0)
        from stable_baselines3 import PPO
        model = PPO.load("ppo_hex_game", env=env)
        model.set_env(env)

        # Réinitialiser l'environnement (reset renvoie (obs, info))
        obs, info = env.reset()
        done = False
        total_reward = 0

        # Boucle de jeu
        while not done:
            if env.current_player == 0:
                action, _ = model.predict(obs)
            else:
                # Adversaire random : choisir aléatoirement parmi les coups légaux
                legal_moves = env.get_legal_moves()
                if legal_moves:
                    action = random.randint(0, len(legal_moves) - 1)
                else:
                    action = 0

            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            total_reward += reward

            env.render()
            pygame.time.wait(500)  # Pause pour visualiser
        print("Partie terminée. Reward total :", total_reward)

    elif AI_TYPE == "alphabeta":
        # Assurez-vous d'avoir intégré les fonctions alphabeta et best_move dans votre code,
        # ainsi qu'une fonction utilitaire (ici env_copy) permettant de copier l'environnement.
        # Exemple : voir les fonctions alphabeta, best_move et env_copy fournies précédemment.

        # Paramètres de la recherche alphabeta
        search_depth = 4   # Ajustez la profondeur en fonction de la complexité du jeu
        player_color = "rouge"  # On suppose que l'agent (maximisant) est "rouge"

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


            # Appliquer le coup choisi
            valid, fusion_move = env.apply_move(move)
            if valid:
                env.history.append(move)
            else:
                total_reward -= 0.5

            if valid and not fusion_move:
                env.current_player = 1 - env.current_player

            # Vérifier la condition de victoire
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
