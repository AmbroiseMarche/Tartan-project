"""
Script complet pour entraîner une IA en mode Reinforcement Learning
sur le jeu de stratégie hexagonal via l'environnement HexGameEnv.

Ce script utilise PPO de Stable-Baselines3.
Assurez-vous d'avoir installé les packages nécessaires :
    pip install stable-baselines3
    pip install gymnasium   # ou gym, selon votre version

Il est supposé que la classe HexGameEnv est définie dans votre module principal (par exemple, whole_python.py).
"""

import os
import gymnasium as gym
# Si vous utilisez gymnasium, vous pouvez importer gymnasium à la place de gym.
from stable_baselines3 import PPO
import pygame
from stable_baselines3.common.env_checker import check_env

# Importer votre environnement.
# Adaptez le chemin d'importation selon votre organisation de fichiers.
# Ici, on suppose que HexGameEnv se trouve dans whole_python.py
from whole_python import HexGameEnv
import matplotlib.pyplot as plt
from stable_baselines3.common.callbacks import BaseCallback

class PlottingCallback(BaseCallback):
    def __init__(self, verbose=0):
        super(PlottingCallback, self).__init__(verbose)
        self.episode_rewards = []
        self.episode_counts = []

    def _on_step(self) -> bool:
        # Nous essayons ici de récupérer le cumul des récompenses pour un épisode.
        # Pour cela, il est préférable d'utiliser un environnement Monitor (voir la doc SB3).
        # Ici, nous utilisons self.locals qui contient parfois la variable 'infos'
        # qui peut contenir "episode" avec le cumul de récompenses.
        infos = self.locals.get("infos", [])
        for info in infos:
            if "episode" in info.keys():
                # Enregistre le reward cumulé de l'épisode
                self.episode_rewards.append(info["episode"]["r"])
                self.episode_counts.append(info["episode"]["l"])  # par exemple, la longueur de l'épisode
        return True

    def _on_training_end(self):
        # Trace la courbe des récompenses par épisode
        plt.figure(figsize=(12, 6))
        plt.plot(self.episode_rewards)
        plt.xlabel("Épisodes")
        plt.ylabel("Récompense cumulée")
        plt.title("Courbe de récompense pendant l'entraînement")
        plt.show()

import os
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from whole_python import HexGameEnv  # Assurez-vous que le chemin d'importation est correct

def train_agent(total_timesteps=200000, model_save_path="ppo_hex_game"):
    # Créer une instance de l'environnement
    env = HexGameEnv()
    
    # Vérifier que l'environnement respecte l'API Gym
    check_env(env, warn=True)
    
    # Créer le modèle PPO en utilisant une MLP Policy et un learning rate décroissant.
    # Ici, on démarre avec un learning rate de 0.01 et il décroît linéairement.
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=lambda progress_remaining: progress_remaining * 0.01,
        tensorboard_log="./logs/"
    )
    
    # Entraîner le modèle sur le nombre de timesteps souhaité
    model.learn(total_timesteps=total_timesteps)
    
    # Sauvegarder le modèle entraîné
    model.save(model_save_path)
    print(f"Modèle sauvegardé sous {model_save_path}")
    
    return model, env

def evaluate_agent(model, env, render=True):
    obs, info = env.reset()
    done = False
    total_reward = 0
    step_count = 0
    while not done:
        action, _states = model.predict(obs)
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        total_reward += reward
        step_count += 1
        if render:
            env.render()
        # Petite pause pour visualiser
        import pygame
        pygame.time.wait(500)
    print(f"Partie terminée en {step_count} étapes avec un reward total de {total_reward}")

def main():
    TOTAL_TIMESTEPS = 200000
    MODEL_SAVE_PATH = "ppo_hex_game"
    
    model, env = train_agent(total_timesteps=TOTAL_TIMESTEPS, model_save_path=MODEL_SAVE_PATH)
    evaluate_agent(model, env, render=True)

if __name__ == "__main__":
    import os
    os.makedirs("logs", exist_ok=True)
    main()

