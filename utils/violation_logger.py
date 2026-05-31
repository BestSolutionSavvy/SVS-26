import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from models.rule import Rule
from models.transition import Transition


class ViolationLogger:
    """Handles logging of rule violations to a JSON file with buffering."""

    def __init__(self, log_dir: str = "logs", buffer_size: int = 10):
        """
        Initialize the violation logger.
        
        Args:
            log_dir: Directory to store logs (default "logs")
            buffer_size: Flush to disk after this many violations (default 10)
        """
        Path(log_dir).mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = os.path.join(log_dir, f"violations_{timestamp}.json")
        self.buffer = []
        self.buffer_size = buffer_size

    def log_violation(self, rule: Rule, transition: Optional[Transition], scene_data: dict) -> None:
        """
        Log a rule violation (buffered).
        
        Args:
            rule: The Rule that was violated
            transition: The Transition that represents the violation
            scene_data: A dictionary of relevant scene data at the time of violation
        """
        scene_data_serializable = {
            k: str(v) if hasattr(v, '__dict__') else v
            for k, v in scene_data.items()
        }
        
        entry = {
            "rule": str(rule),
            "timestamp": datetime.now().strftime('%Y%m%d_%H:%M:%S.%f')[:-3],
            "violation": str(transition),
            "scene": scene_data_serializable,
        }
        
        self.buffer.append(entry)
        
        if len(self.buffer) >= self.buffer_size:
            self.flush()

    def flush(self) -> None:
        """Write buffered violations to disk."""
        if not self.buffer:
            return
        
        with open(self.log_file, 'a') as f:
            for entry in self.buffer:
                f.write(json.dumps(entry) + '\n')
        
        self.buffer.clear()
