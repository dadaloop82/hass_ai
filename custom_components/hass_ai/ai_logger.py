"""
HASS AI Logging System
Logs all AI interactions for debugging and analysis
"""
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any

_LOGGER = logging.getLogger(__name__)

class AILogger:
    """Logger for AI prompts and responses"""
    
    def __init__(self, hass):
        self.hass = hass
        # Usa la cartella ai_logs nella root del progetto
        component_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(os.path.dirname(component_dir))  # Da custom_components/hass_ai alla root
        self.log_dir = os.path.join(project_root, "ai_logs")
        self._ensure_log_directory()
        
    def _ensure_log_directory(self):
        """Create log directory if it doesn't exist"""
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
                _LOGGER.debug(f"Created HASS AI log directory: {self.log_dir}")
            except Exception as e:
                _LOGGER.error(f"Failed to create log directory: {e}")
                
    def log_ai_interaction(self, interaction_type: str, data: Dict[str, Any]):
        """Log an AI interaction with timestamp"""
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            "timestamp": timestamp,
            "type": interaction_type,
            "data": data
        }
        
        # Create filename with date
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(self.log_dir, f"ai_interactions_{date_str}.jsonl")
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            _LOGGER.error(f"Failed to write AI log: {e}")
            
    def log_prompt(self, batch_num: int, prompt: str, entities: list, ai_provider: str):
        """Log an AI prompt"""
        self.log_ai_interaction("prompt", {
            "batch_num": batch_num,
            "ai_provider": ai_provider,
            "prompt": prompt,
            "prompt_length": len(prompt),
            "entity_count": len(entities),
            "entities": [entity.entity_id if hasattr(entity, 'entity_id') else str(entity) for entity in entities]
        })
        
    def log_response(self, batch_num: int, response: str, parsed_data: Any, ai_provider: str):
        """Log an AI response"""
        self.log_ai_interaction("response", {
            "batch_num": batch_num,
            "ai_provider": ai_provider,
            "raw_response": response,
            "response_length": len(response) if response else 0,
            "parsed_data": parsed_data,
            "parsing_successful": parsed_data is not None
        })
        
    def log_error(self, batch_num: int, error: str, context: Dict[str, Any]):
        """Log an error during AI processing"""
        self.log_ai_interaction("error", {
            "batch_num": batch_num,
            "error": str(error),
            "context": context
        })
        
    def get_recent_logs(self, hours: int = 24) -> list:
        """Get recent AI interaction logs"""
        recent_logs = []
        
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = os.path.join(self.log_dir, f"ai_interactions_{date_str}.jsonl")
            
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            log_entry = json.loads(line.strip())
                            recent_logs.append(log_entry)
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            _LOGGER.error(f"Failed to read AI logs: {e}")
            
        return recent_logs[-100:]  # Return last 100 entries
