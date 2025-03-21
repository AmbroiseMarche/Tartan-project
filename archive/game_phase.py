import pygame
import math
from plateau_hexagonal import Plateau_hexagonal
from player import Player
from pieces import Unite, Chapeau, Double, Triple, Quadruple
from hexagone import hexagone

move_button_rect = pygame.Rect(50, 50, 100, 40)
split_button_rect = pygame.Rect(200, 50, 100, 40)

# Fonction utilitaire pour convertir un clic en coordonnées hexagonales
def pixel_to_hex(x, y, size):
    q = (2 / 3 * x) / size
    r = (-1 / 3 * x + math.sqrt(3) / 3 * y) / size
    return cube_round(q, r)

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

def afficher_plateau(screen, plateau, size, highlighted=None):
    """Affiche le plateau avec les cases disponibles illuminées."""
    screen.fill((255, 255, 255))

    positions_chapeaux = {
        "rouge": hexagone(0, 0, 0),
        "bleu": hexagone(0, 0, 0),
    }

    for hex_case in plateau.plateau_hexagonal_complet:
        q, r, s = hex_case.q, hex_case.r, hex_case.s
        x = size * (3 / 2 * q) + 400  # Décalage pour centrer
        y = size * (math.sqrt(3) * (r + q / 2)) + 300

        # Déterminer la couleur de fond de l'hexagone
        if hex_case in plateau.casesinterdites:
            color = (0, 0, 0)
        elif highlighted and hex_case in highlighted:
            color = (255, 255, 0)
        else:
            color = (200, 200, 200)

        # Dessiner l'hexagone
        points = [
            (x + size * math.cos(math.radians(angle)), y + size * math.sin(math.radians(angle)))
            for angle in range(0, 360, 60)
        ]
        pygame.draw.polygon(screen, color, points, 0)
        pygame.draw.polygon(screen, (0, 0, 0), points, 1)

        # Dessiner une pièce si la case est occupée
        if hex_case in plateau.pieces:
            piece = plateau.pieces[hex_case]
            piece_color = (255, 0, 0) if piece.couleur == "rouge" else (0, 0, 255)
            pygame.draw.circle(screen, piece_color, (int(x), int(y)), size // 3)

            # Afficher un nombre pour les piles
            if isinstance(piece, Double):
                afficher_nombre(screen, x, y, size, "2")
            elif isinstance(piece, Triple):
                afficher_nombre(screen, x, y, size, "3")
            elif isinstance(piece, Quadruple):
                afficher_nombre(screen, x, y, size, "4")

        # Dessiner les chapeaux
        if hex_case == positions_chapeaux["rouge"]:
            dessiner_triangle(screen, x, y, size, "rouge")
        if hex_case == positions_chapeaux["bleu"]:
            dessiner_triangle(screen, x, y, size, "bleu")

    pygame.display.flip()

def afficher_nombre(screen, x, y, size, nombre):
    """Affiche un nombre au centre d'une pièce."""
    font = pygame.font.Font(None, size)
    text = font.render(nombre, True, (0, 0, 0))
    text_rect = text.get_rect(center=(int(x), int(y)))
    screen.blit(text, text_rect)

def dessiner_triangle(screen, x, y, size, couleur):
    """Dessine un triangle pour représenter un chapeau."""
    triangle_offset = size // 3
    if couleur == "rouge":
        triangle_points = [
            (x + triangle_offset, y),
            (x + triangle_offset * 2, y - triangle_offset),
            (x + triangle_offset * 2, y + triangle_offset),
        ]
        pygame.draw.polygon(screen, (255, 0, 0), triangle_points, 0)  # triangle rouge

    elif couleur == "bleu":
        triangle_points = [
            (x - triangle_offset, y),
            (x - triangle_offset * 2, y - triangle_offset),
            (x - triangle_offset * 2, y + triangle_offset),
        ]
        pygame.draw.polygon(screen, (0, 0, 255), triangle_points, 0)  # triangle bleu
        

def initialiser_configuration(plateau, joueur1, joueur2):
    """Initialise une configuration prédéfinie après la phase de placement."""
    # Placement des unités rouges (Joueur 1)
    rouge_positions = [
        (-1, -1, 2), (4, -1, -3), (3, -3, 0), (2, -4, 2),
        (2, -1, -1), (2, 2, -4), (1, -2, 1), (1, 1, -2)
    ]
    for pos in rouge_positions:
        plateau.placer_piece(Unite("rouge", hexagone(*pos)), hexagone(*pos))

    # Placement des unités bleues (Joueur 2)
    bleu_positions = [
        (0, -3, 3), (0, 3, -3), (-1, 2, -1), (-2, -2, 4),
        (-2, 1, 1), (-3, 0, 3), (-3, 4, -1), (-4, 2, 2)
    ]
    for pos in bleu_positions:
        plateau.placer_piece(Unite("bleu", hexagone(*pos)), hexagone(*pos))

    # Placement des chapeaux
    plateau.placer_piece(Chapeau("rouge", hexagone(0, 0, 0)), hexagone(0, 0, 0))
    plateau.placer_piece(Chapeau("bleu", hexagone(0, 0, 0)), hexagone(0, 0, 0))

def main_game():
    # Initialisation
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Phase de Jeu")
    clock = pygame.time.Clock()

    plateau = Plateau_hexagonal()
    joueur1 = Player(couleur="rouge", nom="Joueur 1")
    joueur2 = Player(couleur="bleu", nom="Joueur 2")
    joueurs = [joueur1, joueur2]
    joueur_actuel = 0
    size = 40
    partie_terminee = False

    # Configuration initiale
    initialiser_configuration(plateau, joueur1, joueur2)

    while not partie_terminee:
        afficher_plateau(screen, plateau, size)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                partie_terminee = True

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                x, y = event.pos
                q, r, s = pixel_to_hex(x - 400, y - 300, size)
                clicked_hex = hexagone(q, r, s)

                joueur = joueurs[joueur_actuel]

                if clicked_hex in plateau.pieces and not isinstance(plateau.pieces[clicked_hex], Quadruple):
                    piece = plateau.pieces[clicked_hex]
                    if piece.couleur == joueur.couleur:
                        actions_possibles = piece.mouvements_possibles(plateau)
                        afficher_plateau(screen, plateau, size, highlighted=actions_possibles)

                        action_realisee = False
                        while not action_realisee:
                            for event in pygame.event.get():
                                if event.type == pygame.QUIT:
                                    partie_terminee = True
                                    action_realisee = True

                                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                                    x2, y2 = event.pos
                                    q2, r2, s2 = pixel_to_hex(x2 - 400, y2 - 300, size)
                                    target_hex = hexagone(q2, r2, s2)

                                    if target_hex in actions_possibles:
                                        if target_hex in plateau.pieces:
                                            autre_piece = plateau.pieces[target_hex]
                                            
                                            # Gestion des fusions
                                            if isinstance(piece, Unite) and isinstance(autre_piece, Double) and piece.couleur == autre_piece.couleur:
                                                # Fusion unité + double -> triple
                                                print(f"Fusion de l'unité avec un double en {target_hex}")
                                                del plateau.pieces[piece.position]
                                                plateau.pieces[target_hex] = Triple(piece.couleur, target_hex)
                                                piece = plateau.pieces[target_hex]  # La nouvelle pièce devient active

                                                # Actions possibles pour le Triple
                                                actions_possibles = piece.mouvements_possibles(plateau)
                                                afficher_plateau(screen, plateau, size, highlighted=actions_possibles)
                                                continue  # Attendre un clic pour déplacer le Triple

                                            if isinstance(piece, Double) and isinstance(autre_piece, Unite) and piece.couleur == autre_piece.couleur:
                                                # Fusion double + unité -> triple
                                                print(f"Fusion du double avec une unité en {target_hex}")
                                                del plateau.pieces[piece.position]
                                                plateau.pieces[target_hex] = Triple(piece.couleur, target_hex)
                                                piece = plateau.pieces[target_hex]  # La nouvelle pièce devient active

                                                # Actions possibles pour le Triple
                                                actions_possibles = piece.mouvements_possibles(plateau)
                                                afficher_plateau(screen, plateau, size, highlighted=actions_possibles)
                                                continue  # Attendre un clic pour déplacer le Triple

                                            if isinstance(piece, Unite) and isinstance(autre_piece, Unite):
                                                # Fusion unité + unité -> double
                                                print(f"Fusion des unités en {target_hex}")
                                                del plateau.pieces[piece.position]
                                                plateau.pieces[target_hex] = Double(piece.couleur, target_hex)
                                                piece = plateau.pieces[target_hex]  # La nouvelle pièce devient active

                                                # Actions possibles pour le Double
                                                actions_possibles = piece.mouvements_possibles(plateau)
                                                afficher_plateau(screen, plateau, size, highlighted=actions_possibles)
                                                continue  # Attendre un clic pour déplacer le Double

                                            if isinstance(piece, Double) and isinstance(autre_piece, Double) and piece.couleur == autre_piece.couleur and not piece.position == autre_piece.position:
                                                # Fusion double + double -> quadruple
                                                print(f"Fusion des doubles en {target_hex}")
                                                del plateau.pieces[piece.position]
                                                plateau.pieces[target_hex] = Quadruple(piece.couleur, target_hex)
                                                piece = plateau.pieces[target_hex]
                                              

                                        # Déplacement simple
                                        joueur.deplacer_piece(piece.position, target_hex, plateau)
                                        action_realisee = True

                        joueur_actuel = 1 - joueur_actuel

        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main_game()
