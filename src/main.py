"""
Main entry point for the hexagonal game
"""
import argparse
from src.game.game import Game

def main():
    """Parse arguments and start the game."""
    parser = argparse.ArgumentParser(description="Hexagonal Board Game")
    parser.add_argument("--skip-placement", action="store_true", 
                       help="Skip the placement phase and use a preset configuration")
    args = parser.parse_args()
    
    # Create and run the game
    game = Game()
    try:
        game.run(skip_placement=args.skip_placement)
    except KeyboardInterrupt:
        print("Game interrupted by user")
    finally:
        game.quit()

if __name__ == "__main__":
    main()