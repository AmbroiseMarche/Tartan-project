import pygame
import math
from plateau_hexagonal import Plateau_hexagonal
from player import Player
from pieces import Unite, Chapeau, Double, Triple, Quadruple, ChapeauxInit
from hexagone import hexagone

###################################################
# Boutons Move/Split
###################################################
move_button_rect = pygame.Rect(20, 50, 100, 40)
split_button_rect = pygame.Rect(130, 50, 100, 40)

def draw_buttons_for_double(screen, piece_double):
    """
    Dessine deux boutons : "Move" et "Split".
    Si piece_double.just_formed est True, on grise (ou on masque) le Split.
    """
    pygame.draw.rect(screen, (180, 180, 180), move_button_rect)
    font = pygame.font.Font(None, 24)
    text_move = font.render("Move", True, (0, 0, 0))
    screen.blit(text_move, (move_button_rect.x + 15, move_button_rect.y + 10))

    # Vérifier si on autorise ou pas le split
    if getattr(piece_double, "just_formed", False):
        print(piece_double.just_formed)
        print('on rentre dans cette boucle getattr de mort')
        # On grise le bouton Split pour signifier qu'il est interdit ce tour
        pygame.draw.rect(screen, (120, 120, 120), split_button_rect)
        text_split = font.render("Split (NO)", True, (50, 50, 50))
        screen.blit(text_split, (split_button_rect.x + 5, split_button_rect.y + 10))
    else:
        # Bouton Split normal
        pygame.draw.rect(screen, (180, 180, 180), split_button_rect)
        text_split = font.render("Split", True, (0, 0, 0))
        screen.blit(text_split, (split_button_rect.x + 15, split_button_rect.y + 10))


##########################################################
# Outils pour convertir un clic pixel -> coordonnées hex
##########################################################
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

##########################################################
# Fonctions d'affichage du plateau
##########################################################

def afficher_plateau(screen, plateau, size, highlighted=None, blocked=None):
    """
    Affiche le plateau avec éventuellement :
      - highlighted : ensemble de cases à surligner en jaune
      - blocked : ensemble de cases à afficher en gris foncé (par exemple, bloquées temporairement)

    Gestion des différents cas d'affichage :
      - Si la case contient un ChapeauxInit, affiche 2 chapeaux (rouge et bleu) en offset.
      - Si la case contient un Chapeau, affiche le chapeau en offset.
      - Si la case contient un tuple (occupant, chapeau), affiche l'occupant au centre et le chapeau en offset.
      - Sinon, pour les pièces classiques (Unite, Double, Triple, Quadruple), affiche un cercle au centre et, pour les piles, le nombre correspondant.
    """
    # Si aucune case bloquée n'est spécifiée, utiliser un ensemble vide.
    if blocked is None:
        blocked = set()

    # Remplit l'écran en blanc.
    screen.fill((255, 255, 255))

    # Parcours de toutes les cases du plateau.
    for hex_case in plateau.plateau_hexagonal_complet:
        q, r, s = hex_case.q, hex_case.r, hex_case.s

        # Conversion des coordonnées hexagonales en pixels (avec un décalage pour centrer).
        x = size * (3 / 2 * q) + 400
        y = size * (math.sqrt(3) * (r + q / 2)) + 300

        # Détermine la couleur de fond par défaut.
        color = (200, 200, 200)
        if hex_case in plateau.casesinterdites:
            color = (0, 0, 0)
        elif highlighted and hex_case in highlighted:
            color = (255, 255, 0)
        elif hex_case in blocked:
            color = (150, 150, 150)

        # Dessine l'hexagone (fond et contour).
        points = [
            (x + size * math.cos(math.radians(angle)),
             y + size * math.sin(math.radians(angle)))
            for angle in range(0, 360, 60)
        ]
        pygame.draw.polygon(screen, color, points, 0)
        pygame.draw.polygon(screen, (0, 0, 0), points, 1)

        # Si la case contient une pièce, on l'affiche.
        if hex_case in plateau.pieces:
            cell_content = plateau.pieces[hex_case]

            # --- Cas 1 : Contenu est un tuple (occupant, chapeau) ---
            if isinstance(cell_content, tuple):
                occupant, hat = cell_content
                # Dessiner l'occupant au centre.
                piece_color = (255, 0, 0) if occupant.couleur == "rouge" else (0, 0, 255)
                pygame.draw.circle(screen, piece_color, (int(x), int(y)), size // 3)
                # Pour les piles, afficher le nombre (pour Double, Triple, Quadruple).
                if isinstance(occupant, Double):
                    afficher_nombre(screen, x, y, size, "2")
                elif isinstance(occupant, Triple):
                    afficher_nombre(screen, x, y, size, "3")
                elif isinstance(occupant, Quadruple):
                    afficher_nombre(screen, x, y, size, "4")
                # Dessiner le chapeau en offset (ici, décalé vers la droite).
                dessiner_triangle(screen, x + (size // 4), y, size, hat.couleur)

            # --- Cas 2 : Contenu est un ChapeauxInit (le hack pour le centre) ---
            elif isinstance(cell_content, ChapeauxInit):
                # On suppose que cell_content.chapeaux est une liste contenant "rouge" et/ou "bleu".
                if "rouge" in cell_content.chapeaux:
                    # Affiche le chapeau rouge décalé à droite.
                    dessiner_triangle(screen, x + (size // 4), y, size, "rouge")
                if "bleu" in cell_content.chapeaux:
                    # Affiche le chapeau bleu décalé à gauche.
                    dessiner_triangle(screen, x - (size // 4), y, size, "bleu")

            # --- Cas 3 : Contenu est un Chapeau (unique) ---
            elif isinstance(cell_content, Chapeau):
                # Dessine le chapeau en offset (ici à droite).
                dessiner_triangle(screen, x + (size // 4), y, size, cell_content.couleur)

            # --- Cas 4 : Contenu est une pièce "classique" (Unite, Double, Triple, Quadruple, etc.) ---
            else:
                piece_color = (255, 0, 0) if cell_content.couleur == "rouge" else (0, 0, 255)
                pygame.draw.circle(screen, piece_color, (int(x), int(y)), size // 3)
                from pieces import Double, Triple, Quadruple
                if isinstance(cell_content, Double):
                    afficher_nombre(screen, x, y, size, "2")
                elif isinstance(cell_content, Triple):
                    afficher_nombre(screen, x, y, size, "3")
                elif isinstance(cell_content, Quadruple):
                    afficher_nombre(screen, x, y, size, "4")

    pygame.display.flip()


# --- Fonctions utilitaires de dessin ---

def dessiner_triangle(screen, x, y, size, couleur):
    """
    Dessine un triangle pour représenter un chapeau.
    L'offset et la forme sont fixes ici, mais vous pouvez les ajuster.
    """
    triangle_offset = size // 3
    if couleur == "rouge":
        triangle_points = [
            (x + triangle_offset, y),
            (x + triangle_offset * 2, y - triangle_offset),
            (x + triangle_offset * 2, y + triangle_offset),
        ]
        pygame.draw.polygon(screen, (255, 0, 0), triangle_points, 0)
    elif couleur == "bleu":
        triangle_points = [
            (x - triangle_offset, y),
            (x - triangle_offset * 2, y - triangle_offset),
            (x - triangle_offset * 2, y + triangle_offset),
        ]
        pygame.draw.polygon(screen, (0, 0, 255), triangle_points, 0)


def afficher_nombre(screen, x, y, size, nombre):
    """
    Affiche un nombre au centre d'une pièce.
    Utile pour représenter la taille d'une pile (ex : "2" pour un Double).
    """
    font = pygame.font.Font(None, size)
    text = font.render(nombre, True, (0, 0, 0))
    text_rect = text.get_rect(center=(int(x), int(y)))
    screen.blit(text, text_rect)

##########################################################
# Gestion d'une config initiale (exemple)
##########################################################
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

    plateau.pieces[hexagone(0,0,0)] = ChapeauxInit(hexagone(0,0,0))



##########################################################
# Mécanique de SPLIT : Double -> 3 Unités
##########################################################
def effectuer_split_double(plateau, piece_double, screen, size):
    """
    Split : Double -> 3 Unités
    - Chaque unité doit se trouver dans une fleur différente
    - On grise (bloque) toute la fleur dès qu'on l'a utilisée
    - Exclusion de la fleur centrale (0,0,0)
    """
    old_pos = piece_double.position
    couleur = piece_double.couleur

    # Retirer la Double
    del plateau.pieces[old_pos]

    # Suivi des fleurs déjà choisies
    fleurs_utilisees = set()
    # Ensemble de cases bloquées (grisées) déjà attribuées à des fleurs
    cases_bloquees = set()

    nb_a_placer = 3

    while nb_a_placer > 0:
        # Affichage en tenant compte des cases bloquées
        afficher_plateau(screen, plateau, size, blocked=cases_bloquees)

        # Message (facultatif)
        font = pygame.font.Font(None, 30)
        text = font.render(
            f"Placez l'unité n°{4 - nb_a_placer} (couleur {couleur})",
            True, (0, 0, 0)
        )
        screen.blit(text, (10, 10))
        pygame.display.flip()

        case_valide = None
        while case_valide is None:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    return
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    mx, my = ev.pos
                    q, r, s = pixel_to_hex(mx - 400, my - 300, size)
                    clicked_hex = hexagone(q, r, s)

                    # On vérifie d'abord que ce n'est pas bloqué
                    if clicked_hex in cases_bloquees:
                        print("Cette case est déjà bloquée (fleur déjà utilisée).")
                        continue

                    # Vérifier si c'est OK (case libre, pas sombre)
                    if est_case_valide_split(plateau, clicked_hex):
                        # Récupérer la (ou les) fleurs => liste_fleurs_possible
                        possible_fleurs = plateau.liste_fleurs_possible(clicked_hex)

                        # Enlever la fleur centrale si présente
                        if hexagone(0,0,0) in possible_fleurs:
                            possible_fleurs.remove(hexagone(0,0,0))

                        # Trouver une fleur non encore utilisée
                        fleur_choisie = None
                        for fcenter in possible_fleurs:
                            if fcenter not in fleurs_utilisees:
                                fleur_choisie = fcenter
                                break

                        if fleur_choisie is not None:
                            # On valide ce clic
                            case_valide = clicked_hex
                            # On note cette fleur comme "utilisée"
                            fleurs_utilisees.add(fleur_choisie)

                            # BLOQUER toutes les cases de cette fleur
                            # => fleur = {center} U neighbors(center)
                            fleur_cases = {fleur_choisie} | fleur_choisie.neighbors(plateau)
                            cases_bloquees |= fleur_cases
                        else:
                            print("Impossible: cette case est soit hors fleur, soit dans une fleur déjà utilisée.")
                            # On ne sort pas, on redemande un clic
                    else:
                        print("Case invalide (sombre/occupée).")
            # fin for ev

        # On place l'unité
        nouvelle_unite = Unite(couleur, case_valide)
        plateau.pieces[case_valide] = nouvelle_unite
        nb_a_placer -= 1

    # Après avoir placé les 3 unitéss
    print("==> Split effectué : la Double est remplacée par 3 Unités (fleurs distinctes).")

    # FIN : hors de cette fonction, on repassera `afficher_plateau` normalement
    # (donc plus de cases_bloquees => tout redevient normal)


def est_case_valide_split(plateau, hex_case):
    """
    Vérifie qu'on peut placer une unité de split sur la case :
      - pas sombre
      - pas occupée
    """
    if hex_case in plateau.casesinterdites:
        return False
    if hex_case in plateau.pieces:
        return False
    return True

##########################################################
# MAIN GAME : boucle de jeu
##########################################################
def main_game():
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

    # Configuration initiale : le centre reçoit un ChapeauxInit
    initialiser_configuration(plateau, joueur1, joueur2)
    # initialiser_configuration doit placer, par exemple :
    #   center = hexagone(0,0,0)
    #   plateau.pieces[center] = ChapeauxInit(center)

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

                # Vérifier si la case est occupée (et pas un Quadruple)
                if clicked_hex in plateau.pieces and not isinstance(plateau.pieces[clicked_hex], Quadruple):
                    cell = plateau.pieces[clicked_hex]
                    
                    # Si le contenu est un tuple, la case est champotée SI LE CHAPEAU EST DE LA COULEUR ADVERSE, sinon on peut juste déplacer son chapeau, en faisant en sorte que la pièce elle reste sur la case, seul le chapeau bouge, donc on ensemble le tuple et on le remplace par la piece qui etait chapeautée
                    #modifie cette partie donc
                    if isinstance(cell, tuple) and cell[1].couleur != joueur.couleur:
                        print("Cette case est champotée. Veuillez sélectionner une autre case.")
                        continue

                    # Cas spécial : ChapeauxInit
                    from pieces import ChapeauxInit, Chapeau
                    if isinstance(cell, ChapeauxInit):
                        print("Vous avez cliqué sur le ChapeauxInit.")
                        if joueur.couleur in cell.chapeaux:
                            cell.chapeaux.remove(joueur.couleur)
                            other = cell.chapeaux[0] if cell.chapeaux else None
                            if other is not None:
                                hat_static = Chapeau(other, clicked_hex)
                            else:
                                hat_static = None
                            moving_chapeau = Chapeau(joueur.couleur, clicked_hex)
                            print("moving_chapeau:", moving_chapeau)
                            plateau.pieces[clicked_hex] = moving_chapeau
                            mouvement_fait = realiser_deplacement(moving_chapeau, plateau, screen, size, joueur)
                            if mouvement_fait:
                                if hat_static is not None:
                                    plateau.pieces[clicked_hex] = hat_static
                                joueur_actuel = 1 - joueur_actuel
                        else:
                            print("Ce n'est pas votre chapeau dans ChapeauxInit.")
                        continue

                    # Cas général pour les pièces classiques (Unite, Double, Triple, Chapeau simple)
                    piece = cell
                    if piece.couleur == joueur.couleur and not (isinstance(piece, Chapeau) and piece.couleur != joueur.couleur):
                        if isinstance(piece, Double):
                            afficher_plateau(screen, plateau, size)
                            draw_buttons_for_double(screen, piece)
                            pygame.display.flip()
                            choix_fait = False
                            mouvement_fait = False
                            while not choix_fait:
                                for sub_event in pygame.event.get():
                                    if sub_event.type == pygame.QUIT:
                                        partie_terminee = True
                                        choix_fait = True
                                    elif sub_event.type == pygame.MOUSEBUTTONDOWN and sub_event.button == 1:
                                        mx, my = sub_event.pos
                                        if move_button_rect.collidepoint(mx, my):
                                            choix_fait = True
                                            mouvement_fait = realiser_deplacement(piece, plateau, screen, size, joueur)
                                        elif split_button_rect.collidepoint(mx, my):
                                            print("boucle_split")
                                            if not getattr(piece, "just_formed", False):
                                                print("==> Split de la Double !")
                                                effectuer_split_double(plateau, piece, screen, size)
                                                choix_fait = True
                                                mouvement_fait = True
                                            else:
                                                print("Split impossible pour une pile nouvellement formée.")
                                                choix_fait = True
                                        else:
                                            mouvement_fait = realiser_deplacement(piece, plateau, screen, size, joueur)
                                            choix_fait = True
                            if not partie_terminee and mouvement_fait:
                                piece.just_formed = False
                                joueur_actuel = 1 - joueur_actuel
                        else:
                            mouvement_fait = realiser_deplacement(piece, plateau, screen, size, joueur)
                            if mouvement_fait:
                                piece.just_formed = False
                                joueur_actuel = 1 - joueur_actuel

        clock.tick(30)
    pygame.quit()

def realiser_deplacement(piece, plateau, screen, size, joueur):
    """
    Retourne True si une action valide a été réalisée (terminant le tour),
    Retourne False si la sélection est annulée (le joueur reste actif).

    Pour un Chapeau, si le déplacement se fait sur une case déjà occupée,
    on crée une superposition (tuple) de la forme (occupant, chapeau) au lieu de supprimer l'occupant.
    """
    actions_possibles = piece.mouvements_possibles(plateau)
    afficher_plateau(screen, plateau, size, highlighted=actions_possibles)
    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                x2, y2 = event.pos
                q2, r2, s2 = pixel_to_hex(x2 - 400, y2 - 300, size)
                target_hex = hexagone(q2, r2, s2)
                
                if target_hex in actions_possibles:
                    if target_hex in plateau.pieces:
                        cell_content = plateau.pieces[target_hex]
                        if cell_content is piece:
                            print("Déplacement sur sa propre case. Aucune fusion ni manger.")
                            return True
                        
                        # Gestion spécifique pour un Chapeau
                        if isinstance(piece, Chapeau):
                            if isinstance(cell_content, tuple) or isinstance(cell_content, Chapeau):
                                print("Cette case est déjà champotée. Choisissez une autre destination.")
                                continue
                            else:
                                print(f"Le Chapeau {piece.couleur} champote la pièce {cell_content} en {target_hex}")
                                # Créer la superposition sans supprimer l'occupant
                                plateau.pieces[target_hex] = (cell_content, piece)
                                piece.position = target_hex
                                return True
                        
                        # Pour les pièces non-chapeau, gérer fusion / manger
                        if cell_content.couleur != piece.couleur:
                            if isinstance(piece, Double) and isinstance(cell_content, Unite):
                                print(f"{piece} mange l'Unité ennemie {cell_content} en {target_hex}")
                                del plateau.pieces[target_hex]
                                joueur.deplacer_piece(piece.position, target_hex, plateau)
                                piece.just_formed = False
                                return True
                            if isinstance(piece, Triple) and isinstance(cell_content, Double):
                                print(f"{piece} mange la Double ennemie {cell_content} en {target_hex}")
                                del plateau.pieces[target_hex]
                                joueur.deplacer_piece(piece.position, target_hex, plateau)
                                piece.just_formed = False
                                return True
                        if cell_content.couleur == piece.couleur:
                            if isinstance(piece, Unite) and isinstance(cell_content, Unite):
                                print(f"Fusion des unités en {target_hex}")
                                del plateau.pieces[piece.position]
                                plateau.pieces[target_hex] = Double(piece.couleur, target_hex)
                                new_piece = plateau.pieces[target_hex]
                                new_piece.just_formed = True
                                piece = new_piece
                                actions_possibles = piece.mouvements_possibles(plateau)
                                afficher_plateau(screen, plateau, size, highlighted=actions_possibles)
                                pygame.display.flip()
                                continue
                            if isinstance(piece, Unite) and isinstance(cell_content, Double):
                                print(f"Fusion de l'unité avec un double en {target_hex}")
                                del plateau.pieces[piece.position]
                                plateau.pieces[target_hex] = Triple(piece.couleur, target_hex)
                                new_piece = plateau.pieces[target_hex]
                                new_piece.just_formed = True
                                piece = new_piece
                                actions_possibles = piece.mouvements_possibles(plateau)
                                afficher_plateau(screen, plateau, size, highlighted=actions_possibles)
                                pygame.display.flip()
                                continue
                            if isinstance(piece, Double) and isinstance(cell_content, Unite):
                                print(f"Fusion du double avec une unité en {target_hex}")
                                del plateau.pieces[piece.position]
                                plateau.pieces[target_hex] = Triple(piece.couleur, target_hex)
                                new_piece = plateau.pieces[target_hex]
                                new_piece.just_formed = True
                                piece = new_piece
                                actions_possibles = piece.mouvements_possibles(plateau)
                                afficher_plateau(screen, plateau, size, highlighted=actions_possibles)
                                pygame.display.flip()
                                continue
                            if isinstance(piece, Double) and isinstance(cell_content, Double):
                                print(f"Fusion des doubles en {target_hex}")
                                del plateau.pieces[piece.position]
                                plateau.pieces[target_hex] = Quadruple(piece.couleur, target_hex)
                                piece = plateau.pieces[target_hex]
                                return True
                    else:
                        # Case libre
                        joueur.deplacer_piece(piece.position, target_hex, plateau)
                        piece.just_formed = False
                        return True
                else:
                    if getattr(piece, "just_formed", False):
                        print("Tu viens de former ce Double, tu dois le déplacer !")
                        continue
                    else:
                        return False
    return False

if __name__ == "__main__":
    main_game()