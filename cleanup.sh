#!/bin/bash

# Script de nettoyage pour supprimer les fichiers redondants après restructuration

# Liste des fichiers à supprimer
FILES_TO_REMOVE=(
  "affichage_plateau.py"
  "alphazero.py"
  "game_phase.py"
  "game_phase_w_split.py"
  "hexagone.py"
  "main_pygame.py"
  "pieces.py"
  "placement_phase.py"
  "plateau_hexagonal.py"
  "player.py"
  "rl.py"
  "test.py"
  "whole_python.py"
  "whole_pythonv2.py"
)

# Créer un dossier d'archive au cas où
mkdir -p archive

# Déplacer les fichiers dans l'archive au lieu de les supprimer directement
for file in "${FILES_TO_REMOVE[@]}"; do
  if [ -f "$file" ]; then
    echo "Archiving: $file"
    mv "$file" "archive/"
  fi
done

# Déplacer également les documents vers docs/
mv "Code de restitution.docx" "docs/" 2>/dev/null
mv "Règles_officielles_hexgame.pdf" "docs/" 2>/dev/null
mv "Theme.pdf" "docs/" 2>/dev/null
mv "createur.pdf" "docs/" 2>/dev/null

echo "Cleanup complete. Original files have been moved to the 'archive' directory."
echo "If everything works correctly with the new structure, you can delete the 'archive' directory."