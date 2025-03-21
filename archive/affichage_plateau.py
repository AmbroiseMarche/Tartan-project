from plateau_hexagonal import Plateau_hexagonal
from pieces import Unite, Double, Chapeau
from hexagone import hexagone

# Initialisation du plateau
plateau = Plateau_hexagonal()

# Placement de quelques pièces
plateau.placer_piece(Unite("rouge", hexagone(0, 1, -1)), hexagone(0, 1, -1))
plateau.placer_piece(Double("bleu", hexagone(-1, 1, 0)), hexagone(-1, 1, 0))
plateau.placer_piece(Chapeau("vert", hexagone(-2, 2, 0)), hexagone(-2, 2, 0))

# Affichage graphique
plateau.afficher(size=40)
