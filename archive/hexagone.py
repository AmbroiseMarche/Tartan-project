class hexagone:
    def __init__(self, q, r, s, contenu=' '):
        self.q = q
        self.r = r
        self.s = s
        self.contenu = contenu

    def __repr__(self):
        return f"Hex({self.q}, {self.r}, {self.s})"  # ou avec contenu si désiré

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
            hexagone(self.q + 1, self.r - 1, self.s),
            hexagone(self.q + 1, self.r, self.s - 1),
            hexagone(self.q, self.r + 1, self.s - 1),
            hexagone(self.q - 1, self.r + 1, self.s),
            hexagone(self.q - 1, self.r, self.s + 1),
            hexagone(self.q, self.r - 1, self.s + 1),
        ]
        return set(potential).intersection(plateau.plateau_hexagonal_complet)
