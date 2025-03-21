from hexagone import hexagone
from pieces import *
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pygame
import math

class Plateau_hexagonal:
    def __init__(self):
        cases_interieures = set({hexagone(q, r, -q-r) for q in range(-3, 4) for r in range(-3, 4) if -q-r in range(-3, 4)})
        cases_exterieures = {hexagone(-4,1,3), hexagone(-4,2,2), hexagone(-3,4,-1), hexagone(-2,4,-2),
                             hexagone(1,3,-4), hexagone(2,2,-4), hexagone(4,-1,-3), hexagone(4,-2,-2),
                             hexagone(3,-4,1), hexagone(2,-4,2), hexagone(-1,-3,4), hexagone(-2,-2,4)}
        self.plateau_hexagonal_complet = cases_interieures.union(cases_exterieures)
        self.casesinterdites = {hexagone(0,0,0), hexagone(3,-1,-2), hexagone(1,2,-3),hexagone(-2,3,-1),hexagone(-3,1,2),hexagone(-1,-2,3),hexagone(2,-3,1)}
        # Dans Plateau_hexagonal.__init__ (après avoir défini self.casesinterdites, etc.)
        self.fleurs_dict = {}
        for case_int in self.casesinterdites:
            # la "fleur" est {case_int} + voisins
            fleur_set = {case_int} | case_int.neighbors(self)
            self.fleurs_dict[case_int] = fleur_set

        self.pieces = {}

    def liste_fleurs_possible(self, hex_case):
        """Retourne la liste des centres interdits dont la fleur contient hex_case."""
        results = []
        for center_int, set_fleur in self.fleurs_dict.items():
            # Si on ne veut pas compter la fleur du centre, on peut ignorer center_int == (0,0,0) ici
            if hex_case in set_fleur:
                results.append(center_int)
        return results

    def placer_piece(self, piece, position):
        if (position in self.plateau_hexagonal_complet and position not in self.pieces and position not in self.casesinterdites) or (position in self.plateau_hexagonal_complet and isinstance(piece,Chapeau)):
            piece.position = position
            self.pieces[position] = piece
            return True
        return False

    def deplacer_piece(self, depart, arrivee):
        if (depart in self.pieces and arrivee in self.plateau_hexagonal_complet and arrivee not in self.casesinterdites):
            piece = self.pieces.pop(depart)
            piece.position = arrivee
            self.pieces[arrivee] = piece
            return True
        return False

    def cases_libres(self):
        return self.plateau_hexagonal_complet - set(self.pieces.keys())

    def est_adjacent(self, position):
        return any(adj in self.pieces for adj in position.neighbors(self))

    def afficher(self, size=40):
        """
        Affiche le plateau hexagonal en utilisant pygame, avec une fenêtre ajustée à la taille du plateau.
        """
        def hex_to_pixel(q, r, size):
            """Convertir les coordonnées cubiques (q, r) en coordonnées pixel 2D."""
            x = size * (3 / 2 * q)
            y = size * (math.sqrt(3) * (r + q / 2))
            return x, y

        # Calculer les limites du plateau en pixels
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')

        for hex_case in self.plateau_hexagonal_complet:
            q, r, s = hex_case.q, hex_case.r, hex_case.s
            x, y = hex_to_pixel(q, r, size)
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, y), max(max_y, y)

        # Ajouter une marge autour du plateau
        margin = size
        width = int(max_x - min_x + 2 * margin)
        height = int(max_y - min_y + 2 * margin)

        # Initialiser Pygame avec les dimensions calculées
        pygame.init()
        screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Plateau Hexagonal")
        clock = pygame.time.Clock()

        running = True
        while running:
            screen.fill((255, 255, 255))

            for hex_case in self.plateau_hexagonal_complet:
                q, r, s = hex_case.q, hex_case.r, hex_case.s
                x, y = hex_to_pixel(q, r, size)

                # Décaler les coordonnées pour centrer le plateau dans la fenêtre
                x += margin - min_x
                y += margin - min_y

                # Définir la couleur en fonction de l'état de la case
                color = (200, 200, 200)  # Case libre
                if hex_case in self.casesinterdites:
                    color = (50, 50, 50)  # Case interdite
                elif hex_case in self.pieces:
                    piece = self.pieces[hex_case]
                    color = (255, 0, 0) if piece.couleur == "rouge" else (0, 0, 255)

                # Dessiner l'hexagone
                points = [
                    (x + size * math.cos(math.radians(angle)), y + size * math.sin(math.radians(angle)))
                    for angle in range(0, 360, 60)
                ]
                pygame.draw.polygon(screen, color, points, 0)
                pygame.draw.polygon(screen, (0, 0, 0), points, 1)

            pygame.display.flip()
            clock.tick(30)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

        pygame.quit()

