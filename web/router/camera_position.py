import sys
import os

# 将recycle目录添加到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "recycle"))

from main import main as calculate_camera_position

__all__ = ["calculate_camera_position"]
