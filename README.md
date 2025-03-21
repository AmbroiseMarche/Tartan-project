# Hexagonal Board Game

A strategic game played on a hexagonal grid.

## Game Overview

This is a two-player strategy game played on a hexagonal board. Players take turns placing and moving pieces, with the goal of outmaneuvering their opponent.

### Game Mechanics

- **Pieces**: Units, Doubles, Triples, Quadruples, and Hats
- **Board**: Hexagonal grid with forbidden cells (dark hexes)
- **Movement**: Different pieces have different movement rules
- **Fusion**: Pieces can combine to form more powerful pieces

## Installation

This game requires Python 3.8+ and Pygame.

1. Clone the repository
   ```
   git clone https://github.com/yourusername/hexgame.git
   cd hexgame
   ```

2. Set up a virtual environment (optional but recommended)
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```
   pip install -r requirements.txt
   ```

## Running the Game

To start the game:

```
python -m src.main
```

### Command Line Arguments

- `--skip-placement`: Skip the initial placement phase and use a preset configuration

## Game Rules

The game consists of two phases:

1. **Placement Phase**: Players take turns placing units on the board
2. **Movement Phase**: Players take turns moving pieces and performing actions

### Piece Types and Movement Rules

- **Unit**: Moves to adjacent cells, can fuse with other units
- **Double**: Moves up to 2 cells, can fuse with units
- **Triple**: Moves up to 3 cells, can attack doubles
- **Quadruple**: Cannot move (immobile)
- **Hat**: Moves to adjacent cells, can move on top of other pieces

## Development

The project structure is organized as follows:

- `src/core/`: Core game components (board, pieces)
- `src/game/`: Game mechanics and phases
- `src/ui/`: Rendering and user interface
- `src/ai/`: AI players (planned)

## License

[MIT License](LICENSE)