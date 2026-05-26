import os
from kivy.utils import platform
from player import get_best_player, VLC_AVAILABLE, FFPY_AVAILABLE

print(f"Platform: {platform}")
print(f"VLC Available: {VLC_AVAILABLE}")
print(f"FFPyPlayer Available: {FFPY_AVAILABLE}")

player = get_best_player()
print(f"Selected Player: {type(player).__name__}")
