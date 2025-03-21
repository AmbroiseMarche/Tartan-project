from hexagone import hexagone

class Piece:
    def __init__(self, couleur, position):
        self.couleur = couleur
        self.position = position
        self.immobilisee = False  # par défaut
        self.just_formed = False #par defaut

    def __repr__(self):
        return f"{self.__class__.__name__}({self.couleur}, {self.position})"

    def mouvements_possibles(self, plateau):
        raise NotImplementedError("Cette méthode doit être surchargée par les sous-classes.")
    
    def peut_bouger(self):
        return not self.immobilisee
    

class Unite(Piece):
    def mouvements_possibles(self, plateau):
        voisins = self.position.neighbors(plateau)
        mouvements = set()

        for voisin in voisins:
            if voisin in plateau.cases_libres():
                mouvements.add(voisin)  # Case libre
            elif voisin in plateau.pieces and plateau.pieces[voisin].couleur == self.couleur and (isinstance(plateau.pieces[voisin], Unite) or isinstance(plateau.pieces[voisin], Double)):
                mouvements.add(voisin)  # Case occupée par une unité alliée (fusion possible)

        return mouvements

class Double(Piece):
    def mouvements_possibles(self, plateau):
        """Retourne les déplacements possibles pour une pile de 2."""
        # Étape 1 : Obtenir les cases adjacentes à la position actuelle (filtrées)
        voisins = {
            voisin for voisin in self.position.neighbors(plateau)
            if voisin not in plateau.casesinterdites and voisin not in plateau.pieces
        }

        
        # Étape 2 : Retirer temporairement la pièce du plateau (pour éviter de bloquer son propre mouvement)
        plateau.pieces.pop(self.position, None)

        # Étape 3 : Obtenir toutes les cases voisines des voisins
        mouvements = set()
        for voisin in voisins:
            voisins_des_voisins = voisin.neighbors(plateau)
            for case in voisins_des_voisins:
                if (case in plateau.cases_libres() or
                    (case in plateau.pieces and 
                     (isinstance(plateau.pieces[case], Unite) or 
                      isinstance(plateau.pieces[case], Double) and plateau.pieces[case].couleur == self.couleur))) and case not in mouvements:
                    mouvements.add(case)

        # Étape 4 : Remettre la pièce sur le plateau
        plateau.pieces[self.position] = self

        return mouvements



class Triple(Piece):
    def mouvements_possibles(self, plateau):
        """Retourne les déplacements possibles pour une pile de 2."""
        # Étape 1 : Obtenir les cases adjacentes à la position actuelle (filtrées)
        voisins = {
            voisin for voisin in self.position.neighbors(plateau)
            if voisin not in plateau.casesinterdites and voisin not in plateau.pieces
        }

        # Étape 2 : Retirer temporairement la pièce du plateau (pour éviter de bloquer son propre mouvement)
        plateau.pieces.pop(self.position, None)

        # Etape 3 : Obtenir les cases adjacentes aux cases adjacentes (filtrées)
        voisinsins = set()
        for voisin in voisins:
            voisinsins.update(voisin.neighbors(plateau) if voisin not in plateau.casesinterdites and voisin not in plateau.pieces else set())

        # Étape 4 : Obtenir toutes les cases voisines accessibles des voisinsins
        mouvements = set()
        for voisinsin in voisinsins:
            voisins_du_voisinsin = voisinsin.neighbors(plateau)
            for case in voisins_du_voisinsin:
                if (case in plateau.cases_libres() or
                    (case in plateau.pieces and 
                      isinstance(plateau.pieces[case], Double) and plateau.pieces[case].couleur != self.couleur)) and case not in mouvements:
                    mouvements.add(case)

        # Étape 4 : Remettre la pièce sur le plateau
        plateau.pieces[self.position] = self
        
        return mouvements


class Quadruple(Piece):
    def mouvements_possibles(self, plateau):
        return set()

class Chapeau(Piece):
    def mouvements_possibles(self, plateau):
        """
        Le chapeau se déplace d'1 case.
        Il ne peut pas aller sur une case sombre (sauf placement initial éventuel).
        Il ne peut pas aller sur une case contenant déjà un chapeau.
        Sinon, il peut aller sur une case libre ou occupée (alliée ou ennemie).
        """
        if not self.peut_bouger():
            return set()

        moves = set()
        for voisin in self.position.neighbors(plateau):
            # Interdire les cases sombres
            if voisin in plateau.casesinterdites:
                continue
            # S'il y a déjà un chapeau, on refuse
            if voisin in plateau.pieces and isinstance(plateau.pieces[voisin], Chapeau):
                continue
            # Sinon, c'est OK (case libre ou occupée par une pièce sans chapeau)
            moves.add(voisin)
        return moves

class ChapeauxInit:
    """Représente les 2 chapeaux (rouge et bleu) au centre au début du jeu."""
    
    def __init__(self, position):
        self.position = position
        self.chapeaux = ["rouge", "bleu"]  # Les 2 chapeaux en question

    def __repr__(self):
        return f"ChapeauxInit({self.chapeaux}, pos={self.position})"

    # Pas besoin de mouvements_possibles, car on ne les déplace pas "tel quel".
