"""
Training script for reinforcement learning agents
"""
import os
import matplotlib.pyplot as plt
import pygame
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.callbacks import BaseCallback

from src.ai.environment import HexGameEnv

class PlottingCallback(BaseCallback):
    """Callback for plotting rewards during training."""
    
    def __init__(self, verbose=0):
        super(PlottingCallback, self).__init__(verbose)
        self.episode_rewards = []
        self.episode_lengths = []

    def _on_step(self) -> bool:
        # Collect episode info if available
        infos = self.locals.get("infos", [])
        for info in infos:
            if "episode" in info.keys():
                self.episode_rewards.append(info["episode"]["r"])
                self.episode_lengths.append(info["episode"]["l"])
        return True

    def _on_training_end(self):
        # Plot the reward curve at the end of training
        plt.figure(figsize=(12, 6))
        plt.plot(self.episode_rewards)
        plt.xlabel("Episodes")
        plt.ylabel("Cumulative Reward")
        plt.title("Reward During Training")
        plt.show()

def train_agent(total_timesteps=200000, model_save_path="ppo_hex_game"):
    """
    Train a PPO agent on the hexagonal game.
    
    Args:
        total_timesteps: Number of steps to train for
        model_save_path: Where to save the trained model
        
    Returns:
        model: Trained PPO model
        env: Game environment
    """
    # Create the environment
    env = HexGameEnv()
    
    # Validate the environment conforms to Gym API
    check_env(env, warn=True)
    
    # Create the PPO model with decreasing learning rate
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=lambda progress_remaining: progress_remaining * 0.01,
        tensorboard_log="./logs/"
    )
    
    # Create callback for plotting
    plotting_callback = PlottingCallback()
    
    # Train the model
    model.learn(
        total_timesteps=total_timesteps,
        callback=plotting_callback
    )
    
    # Save the trained model
    model.save(model_save_path)
    print(f"Model saved to {model_save_path}")
    
    return model, env

def evaluate_agent(model, env, episodes=5, render=True):
    """
    Evaluate a trained agent.
    
    Args:
        model: Trained model to evaluate
        env: Environment to evaluate in
        episodes: Number of episodes to evaluate
        render: Whether to render the environment
    """
    for episode in range(episodes):
        obs, info = env.reset()
        done = False
        total_reward = 0
        step_count = 0
        
        while not done:
            # Get action from model
            action, _states = model.predict(obs, deterministic=True)
            
            # Execute action
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            total_reward += reward
            step_count += 1
            
            # Render if requested
            if render:
                env.render()
                pygame.time.wait(300)  # Short delay for visualization
                
        print(f"Episode {episode+1}: {step_count} steps, total reward: {total_reward}")

def main():
    """Run the training and evaluation process."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Define parameters
    TOTAL_TIMESTEPS = 200000
    MODEL_SAVE_PATH = "ppo_hex_game"
    
    # Train the agent
    model, env = train_agent(
        total_timesteps=TOTAL_TIMESTEPS,
        model_save_path=MODEL_SAVE_PATH
    )
    
    # Evaluate the trained agent
    evaluate_agent(model, env, render=True)

if __name__ == "__main__":
    main()