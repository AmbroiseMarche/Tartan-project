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

                # Vérifier si la case est occupée et n'est pas un Quadruple
                if clicked_hex in plateau.pieces and not isinstance(plateau.pieces[clicked_hex], Quadruple):
                    cell = plateau.pieces[clicked_hex]
                    
                    # Test immédiat : si le contenu est un tuple, on refuse la sélection
                    if isinstance(cell, tuple):
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

                    # Cas général pour une pièce classique
                    piece = cell
                    # Ici, on est certain que cell n'est ni un tuple ni un ChapeauxInit
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
    Retourne True si une action valide est réalisée (terminant le tour),
    ou False si la sélection est annulée.
    Pour un Chapeau, si le déplacement se fait sur une case déjà occupée,
    on crée une superposition (tuple) (occupant, chapeau) au lieu de supprimer l'occupant.
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
                        
                        # Cas spécifique pour Chapeau
                        if isinstance(piece, Chapeau):
                            if isinstance(cell_content, tuple) or isinstance(cell_content, Chapeau):
                                print("Cette case est déjà champotée. Choisissez une autre destination.")
                                continue
                            else:
                                print(f"Le Chapeau {piece.couleur} champote la pièce {cell_content} en {target_hex}")
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
                        # Case libre : déplacement simple
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
