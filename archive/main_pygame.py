import pygame
import math
from plateau_hexagonal import Plateau_hexagonal
from player import Player
from pieces import Unite
from hexagone import hexagone

# Fonction utilitaire pour convertir un clic en coordonnées hexagonales
def pixel_to_hex(x, y, size):
    """Convertit les coordonnées pixels (x, y) en coordonnées hexagonales cubiques."""
    q = (2 / 3 * x) / size
    r = (-1 / 3 * x + math.sqrt(3) / 3 * y) / size
    return cube_round(q, r)

def cube_round(q, r):
    """Arrondit des coordonnées fractionnelles cubiques en coordonnées cubiques."""
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

def afficher_plateau(screen, plateau, size, highlighted=None):
    """Affiche le plateau avec les cases disponibles illuminées."""
    screen.fill((255, 255, 255))

    for hex_case in plateau.plateau_hexagonal_complet:
        q, r, s = hex_case.q, hex_case.r, hex_case.s
        x = size * (3 / 2 * q) + 400  # Décalage pour centrer
        y = size * (math.sqrt(3) * (r + q / 2)) + 300

        # Déterminer la couleur de fond de l'hexagone
        if hex_case in plateau.casesinterdites:
            color = (0, 0, 0)  # Noir pour les cases interdites
        elif highlighted and hex_case in highlighted:
            color = (255, 255, 0)  # Jaune vif pour les cases disponibles
        else:
            color = (200, 200, 200)  # Gris clair par défaut

        # Dessiner l'hexagone
        points = [
            (x + size * math.cos(math.radians(angle)), y + size * math.sin(math.radians(angle)))
            for angle in range(0, 360, 60)
        ]
        pygame.draw.polygon(screen, color, points, 0)
        pygame.draw.polygon(screen, (0, 0, 0), points, 1)  # Bordure noire

        # Dessiner une pièce si la case est occupée
        if hex_case in plateau.pieces:
            piece = plateau.pieces[hex_case]
            piece_color = (255, 0, 0) if piece.couleur == "rouge" else (0, 0, 255)
            pygame.draw.circle(screen, piece_color, (int(x), int(y)), size // 3)  # Rond pour la pièce

    pygame.display.flip()

def main():
    # Initialisation
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Phase de Placement")
    clock = pygame.time.Clock()

    # Initialisation du plateau et des joueurs
    plateau = Plateau_hexagonal()
    joueur1 = Player(couleur="rouge", nom="Joueur 1")
    joueur2 = Player(couleur="bleu", nom="Joueur 2")
    joueurs = [joueur1, joueur2]
    joueur_actuel = 0  # Indice du joueur actuel
    size = 40  # Taille des hexagones
    phase_placement_terminee = False  # Indique si la phase de placement est terminée

    running = True
    while running:
        # Identifier les cases disponibles si la phase de placement est en cours
        if not phase_placement_terminee:
            cases_disponibles = [
                hex_case for hex_case in plateau.plateau_hexagonal_complet
                if hex_case not in plateau.pieces
                and hex_case not in plateau.casesinterdites
                and not plateau.est_adjacent(hex_case)  # Nouvelle règle : pas adjacent à une autre pièce
            ]

            # Vérifier si la phase de placement est terminée
            if not cases_disponibles:
                print("Fin de la phase de placement.")
                phase_placement_terminee = True

        # Afficher le plateau
        afficher_plateau(screen, plateau, size, highlighted=cases_disponibles if not phase_placement_terminee else None)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if not phase_placement_terminee and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Clic gauche
                x, y = event.pos
                q, r, s = pixel_to_hex(x - 400, y - 300, size)  # Convertir en coordonnées hex
                clicked_hex = hexagone(q, r, s)

                # Vérifier si la case est valide pour placer un pion
                if clicked_hex in cases_disponibles:
                    joueur = joueurs[joueur_actuel]
                    if joueur.placer_piece(Unite, clicked_hex, plateau):
                        joueur_actuel = 1 - joueur_actuel  # Alterner entre 0 et 1

        clock.tick(30)

    pygame.quit()

if __name__ == "__main__":
    main()
