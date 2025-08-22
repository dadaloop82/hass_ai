"""
HASS AI Logging System
Organized logging system with daily directories and separate file types
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

_LOGGER = logging.getLogger(__name__)

class AILogger:
    """Logger for AI prompts and responses with organized daily structure"""
    
    def __init__(self, hass):
        self.hass = hass
        # Usa la cartella logs nella root del progetto
        component_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(os.path.dirname(component_dir))  # Da custom_components/hass_ai alla root
        self.log_dir = os.path.join(project_root, "logs")
        self._ensure_log_directory()
        
    def _ensure_log_directory(self):
        """Create log directory if it doesn't exist"""
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
                _LOGGER.debug(f"Created HASS AI log directory: {self.log_dir}")
            except Exception as e:
                _LOGGER.error(f"Failed to create log directory: {e}")
                
    def _get_daily_directory(self) -> str:
        """Get or create directory for today's logs"""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_dir = os.path.join(self.log_dir, today)
        os.makedirs(daily_dir, exist_ok=True)
        return daily_dir
        
    def _save_to_file(self, filename: str, data: dict):
        """Save data to a specific file in today's directory"""
        try:
            daily_dir = self._get_daily_directory()
            filepath = os.path.join(daily_dir, filename)
            
            # Load existing data if file exists
            existing_data = []
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except:
                    existing_data = []
            
            # Add new entry
            existing_data.append(data)
            
            # Save back to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            _LOGGER.error(f"Failed to save to {filename}: {e}")
    
    def log_prompt(self, prompt: str, context: Optional[Dict] = None):
        """Log an AI prompt"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "context": context or {}
        }
        self._save_to_file("prompts.json", log_entry)
        
    def log_response(self, response: str, context: Optional[Dict] = None):
        """Log an AI response"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "response": response,
            "context": context or {}
        }
        self._save_to_file("responses.json", log_entry)
        
    def log_error(self, error_message: str, error_details: Any = None, context: Optional[Dict] = None):
        """Log an AI error"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_message": error_message,
            "error_details": str(error_details) if error_details else None,
            "context": context or {}
        }
        self._save_to_file("errors.json", log_entry)
        
    def log_info(self, message: str, data: Optional[Dict] = None):
        """Log general information"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "data": data or {}
        }
        self._save_to_file("info.json", log_entry)
        
    def get_logs(self, limit: int = 100, level: str = "all", date: Optional[str] = None) -> List[Dict]:
        """Get logs with filtering options
        
        Args:
            limit: Maximum number of logs to return
            level: Type of logs ("prompt", "response", "error", "info", "all")
            date: Specific date in YYYY-MM-DD format, None for today
        """
        try:
            if date:
                log_dir = os.path.join(self.log_dir, date)
            else:
                log_dir = self._get_daily_directory()
                
            if not os.path.exists(log_dir):
                return []
            
            all_logs = []
            
            # Define which files to read based on level
            files_to_read = []
            if level == "all":
                files_to_read = ["prompts.json", "responses.json", "errors.json", "info.json"]
            elif level == "prompt":
                files_to_read = ["prompts.json"]
            elif level == "response":
                files_to_read = ["responses.json"]
            elif level == "error":
                files_to_read = ["errors.json"]
            elif level == "info":
                files_to_read = ["info.json"]
            
            # Read requested files
            for filename in files_to_read:
                filepath = os.path.join(log_dir, filename)
                if os.path.exists(filepath):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            file_logs = json.load(f)
                            # Add type to each log entry
                            log_type = filename.replace('.json', '')
                            for log_entry in file_logs:
                                log_entry['type'] = log_type
                            all_logs.extend(file_logs)
                    except Exception as e:
                        _LOGGER.error(f"Error reading {filepath}: {e}")
            
            # Sort by timestamp and limit
            all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return all_logs[:limit]
            
        except Exception as e:
            _LOGGER.error(f"Error getting logs: {e}")
            return []
            
    def get_available_dates(self) -> List[str]:
        """Get list of available log dates"""
        try:
            if not os.path.exists(self.log_dir):
                return []
            
            dates = []
            for item in os.listdir(self.log_dir):
                item_path = os.path.join(self.log_dir, item)
                if os.path.isdir(item_path) and len(item) == 10 and item.count('-') == 2:
                    dates.append(item)
            
            return sorted(dates, reverse=True)
            
        except Exception as e:
            _LOGGER.error(f"Error getting available dates: {e}")
            return []
