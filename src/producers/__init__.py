"""Event producers: stand-ins for the platform's game and social subsystems.

They depend only on IEventBus and domain events. They never import anything
from the notification pipeline.
"""

from src.producers.game_engine import GameEngine
from src.producers.social_system import SocialSystem

__all__ = ["GameEngine", "SocialSystem"]
