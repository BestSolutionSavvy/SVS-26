import json
import os
from datetime import datetime
from pathlib import Path


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
        self.log_file = os.path.join(log_dir, f"violations_{timestamp}.jsonl")
        self.buffer = []
        self.buffer_size = buffer_size

    def log_violation(self, rule_name: str, frame_count: int, scene_data: dict) -> None:
        """
        Log a rule violation (buffered).
        
        Args:
            rule_name: Name of the violated rule
            frame_count: Frame number when violation occurred
            scene_data: Data describing the scene when the violation occurred
        """
        scene_data_serializable = {
            k: str(v) if hasattr(v, '__dict__') else v
            for k, v in scene_data.items()
        }
        
        entry = {
            "rule": rule_name,
            "frame": frame_count,
            "scene": scene_data_serializable,
            "timestamp": datetime.now().strftime('%H:%M:%S.%f')[:-3]
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
