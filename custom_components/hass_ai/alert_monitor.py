"""
HASS AI Alert Monitoring System
Monitors entities with ALERTS category and sends intelligent notifications
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE
import json

_LOGGER = logging.getLogger(__name__)

# Alert level configurations
ALERT_LEVELS = {
    "WARNING": {"color": "#ff9800", "icon": "⚠️", "priority": 1},
    "ALERT": {"color": "#f44336", "icon": "🚨", "priority": 2}, 
    "CRITICAL": {"color": "#d32f2f", "icon": "🔥", "priority": 3}
}

# Default thresholds for different entity types
DEFAULT_THRESHOLDS = {
    "sensor": {
        "temperature": {"WARNING": 25, "ALERT": 30, "CRITICAL": 35},
        "humidity": {"WARNING": 70, "ALERT": 80, "CRITICAL": 90},
        "battery": {"WARNING": 20, "ALERT": 10, "CRITICAL": 5},
        "co2": {"WARNING": 1000, "ALERT": 1500, "CRITICAL": 2000},
        "pressure": {"WARNING": 980, "ALERT": 960, "CRITICAL": 940}
    },
    "binary_sensor": {
        "door": {"WARNING": True, "ALERT": True, "CRITICAL": True},
        "window": {"WARNING": True, "ALERT": True, "CRITICAL": True},
        "motion": {"WARNING": True, "ALERT": True, "CRITICAL": True},
        "smoke": {"WARNING": True, "ALERT": True, "CRITICAL": True},
        "gas": {"WARNING": True, "ALERT": True, "CRITICAL": True}
    },
    "switch": {
        "security": {"WARNING": False, "ALERT": False, "CRITICAL": False}
    },
    "light": {
        "emergency": {"WARNING": False, "ALERT": False, "CRITICAL": False}
    }
}

class AlertMonitor:
    """Monitors alert entities and manages notifications"""
    
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.monitored_entities: Dict[str, Dict] = {}
        self.last_notifications: Dict[str, datetime] = {}
        self.active_alerts: Dict[str, Dict] = {}
        self.notification_service = None
        self.use_input_text = False  # Flag to use input_text instead of notification service
        self.input_text_entity = "input_text.hass_ai_alerts"  # Entity ID for alert display
        self.is_monitoring = False
        self._monitor_task = None
        
    async def async_setup(self):
        """Initialize the alert monitor"""
        await self._load_configuration()
        await self._start_monitoring()
        _LOGGER.info("Alert monitor initialized")
        
    async def async_unload(self):
        """Cleanup alert monitor"""
        if self._monitor_task:
            self._monitor_task.cancel()
        self.is_monitoring = False
        _LOGGER.info("Alert monitor stopped")
        
    async def _load_configuration(self):
        """Load alert configuration from storage"""
        try:
            from . import DOMAIN
            store = self.hass.helpers.storage.Store(1, f"{DOMAIN}_alert_config")
            config = await store.async_load() or {}
            
            self.notification_service = config.get("notification_service", "notify.notify")
            self.use_input_text = config.get("use_input_text", False)
            self.input_text_entity = config.get("input_text_entity", "input_text.hass_ai_alerts")
            self.monitored_entities = config.get("monitored_entities", {})
            
            # Create input_text entity if using that mode
            if self.use_input_text:
                await self._ensure_input_text_entity()
            
            _LOGGER.info(f"Loaded alert config: {len(self.monitored_entities)} entities, mode: {'input_text' if self.use_input_text else 'notification'}")
            
        except Exception as e:
            _LOGGER.error(f"Error loading alert configuration: {e}")
            
    async def _save_configuration(self):
        """Save alert configuration to storage"""
        try:
            from . import DOMAIN
            store = self.hass.helpers.storage.Store(1, f"{DOMAIN}_alert_config")
            config = {
                "notification_service": self.notification_service,
                "use_input_text": self.use_input_text,
                "input_text_entity": self.input_text_entity,
                "monitored_entities": self.monitored_entities,
                "last_update": dt_util.utcnow().isoformat()
            }
            await store.async_save(config)
            _LOGGER.info("Alert configuration saved")
            
        except Exception as e:
            _LOGGER.error(f"Error saving alert configuration: {e}")
            
    async def _ensure_input_text_entity(self):
        """Ensure input_text entity exists for alert display"""
        try:
            # Check if entity exists
            state = self.hass.states.get(self.input_text_entity)
            if not state:
                # Create the input_text entity through service call
                await self.hass.services.async_call(
                    "input_text",
                    "reload",
                    {},
                    blocking=True
                )
                
                # Add entity configuration via YAML update (if possible)
                _LOGGER.info(f"Input text entity {self.input_text_entity} should be configured in configuration.yaml:")
                _LOGGER.info(f"""
Add this to your configuration.yaml:

input_text:
  hass_ai_alerts:
    name: "HASS AI Alerts"
    max: 1000
    icon: mdi:alert-circle
    initial: "No alerts"
                """)
                
                # Try to set initial state if entity exists after reload
                await asyncio.sleep(2)
                state = self.hass.states.get(self.input_text_entity)
                if state:
                    await self._update_input_text("🟢 HASS AI Alert Monitor Ready")
                    
        except Exception as e:
            _LOGGER.error(f"Error ensuring input_text entity: {e}")
            
    async def _update_input_text(self, message: str):
        """Update the input_text entity with alert message"""
        try:
            await self.hass.services.async_call(
                "input_text",
                "set_value",
                {
                    "entity_id": self.input_text_entity,
                    "value": message[:1000]  # Limit to max length
                },
                blocking=False
            )
            _LOGGER.debug(f"Updated input_text with: {message[:100]}...")
            
        except Exception as e:
            _LOGGER.error(f"Error updating input_text: {e}")
            
    async def configure_entity_alerts(self, entity_id: str, entity_data: Dict, custom_thresholds: Optional[Dict] = None):
        """Configure alert thresholds for an entity"""
        domain = entity_id.split('.')[0]
        entity_type = self._detect_entity_type(entity_id, entity_data)
        
        # Get default thresholds for this entity type
        default_thresholds = DEFAULT_THRESHOLDS.get(domain, {}).get(entity_type, {})
        
        # Use custom thresholds if provided, otherwise defaults
        thresholds = custom_thresholds or default_thresholds
        
        if not thresholds:
            # Auto-generate thresholds based on current state
            thresholds = await self._auto_generate_thresholds(entity_id, entity_data)
            
        self.monitored_entities[entity_id] = {
            "weight": entity_data.get("overall_weight", 3),
            "thresholds": thresholds,
            "entity_type": entity_type,
            "last_check": None,
            "current_level": None,
            "enabled": True
        }
        
        await self._save_configuration()
        _LOGGER.info(f"Configured alerts for {entity_id}: {thresholds}")
        
    def _detect_entity_type(self, entity_id: str, entity_data: Dict) -> str:
        """Detect entity type for threshold configuration"""
        entity_lower = entity_id.lower()
        
        # Check common patterns
        if any(term in entity_lower for term in ['temp', 'temperature']):
            return 'temperature'
        elif any(term in entity_lower for term in ['humid', 'moisture']):
            return 'humidity'
        elif any(term in entity_lower for term in ['batt', 'battery']):
            return 'battery'
        elif any(term in entity_lower for term in ['co2', 'carbon']):
            return 'co2'
        elif any(term in entity_lower for term in ['pressure', 'press']):
            return 'pressure'
        elif any(term in entity_lower for term in ['door', 'porta']):
            return 'door'
        elif any(term in entity_lower for term in ['window', 'finestra']):
            return 'window'
        elif any(term in entity_lower for term in ['motion', 'movimento', 'pir']):
            return 'motion'
        elif any(term in entity_lower for term in ['smoke', 'fumo']):
            return 'smoke'
        elif any(term in entity_lower for term in ['gas', 'leak']):
            return 'gas'
        elif any(term in entity_lower for term in ['security', 'alarm']):
            return 'security'
        elif any(term in entity_lower for term in ['emergency', 'emer']):
            return 'emergency'
        
        return 'generic'
        
    async def _auto_generate_thresholds(self, entity_id: str, entity_data: Dict) -> Dict:
        """Auto-generate alert thresholds based on entity state and type"""
        state = self.hass.states.get(entity_id)
        if not state:
            return {}
            
        domain = entity_id.split('.')[0]
        
        if domain == 'binary_sensor':
            # For binary sensors, alert when state is True (open, detected, etc.)
            return {"WARNING": True, "ALERT": True, "CRITICAL": True}
            
        elif domain == 'sensor':
            try:
                current_value = float(state.state)
                # Generate thresholds based on current value
                return {
                    "WARNING": current_value * 1.2,
                    "ALERT": current_value * 1.5,
                    "CRITICAL": current_value * 2.0
                }
            except (ValueError, TypeError):
                return {}
                
        elif domain in ['switch', 'light']:
            # For switches/lights, alert when they should be on but are off
            return {"WARNING": False, "ALERT": False, "CRITICAL": False}
            
        return {}
        
    async def _start_monitoring(self):
        """Start the monitoring loop"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                await self._check_all_entities()
                await asyncio.sleep(10)  # Check every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Longer delay on error
                
    async def _check_all_entities(self):
        """Check all monitored entities for alert conditions"""
        current_time = dt_util.utcnow()
        alerts_to_notify = []
        
        for entity_id, config in self.monitored_entities.items():
            if not config.get("enabled", True):
                continue
                
            # Calculate check interval based on weight
            weight = config.get("weight", 3)
            interval_minutes = self._calculate_check_interval(weight)
            
            last_check = config.get("last_check")
            if last_check and (current_time - datetime.fromisoformat(last_check)).total_seconds() < interval_minutes * 60:
                continue
                
            # Check entity state
            alert_level = await self._check_entity_alert(entity_id, config)
            config["last_check"] = current_time.isoformat()
            
            if alert_level:
                # Check if we should notify (throttling)
                if self._should_notify(entity_id, alert_level):
                    alerts_to_notify.append({
                        "entity_id": entity_id,
                        "level": alert_level,
                        "weight": weight,
                        "timestamp": current_time
                    })
                    self.last_notifications[entity_id] = current_time
                    
        # Send cumulative notification if there are alerts
        if alerts_to_notify:
            await self._send_cumulative_notification(alerts_to_notify)
            
    def _calculate_check_interval(self, weight: int) -> int:
        """Calculate check interval in minutes based on weight"""
        # Weight 5 = 0.5 minutes (30 seconds)
        # Weight 1 = 30 minutes
        # Linear interpolation between these values
        if weight >= 5:
            return 0.5
        elif weight <= 1:
            return 30
        else:
            # Linear interpolation: y = mx + b
            # At weight 5: 0.5 minutes
            # At weight 1: 30 minutes
            # slope = (30 - 0.5) / (1 - 5) = -7.375
            return max(0.5, 30 - (weight - 1) * 7.375)
            
    async def _check_entity_alert(self, entity_id: str, config: Dict) -> Optional[str]:
        """Check if entity is in alert state"""
        state = self.hass.states.get(entity_id)
        if not state or state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE]:
            return None
            
        thresholds = config.get("thresholds", {})
        if not thresholds:
            return None
            
        domain = entity_id.split('.')[0]
        
        try:
            if domain == 'binary_sensor':
                current_value = state.state == 'on'
            else:
                current_value = float(state.state)
                
            # Check thresholds in order of severity
            for level in ["CRITICAL", "ALERT", "WARNING"]:
                threshold = thresholds.get(level)
                if threshold is None:
                    continue
                    
                if isinstance(threshold, bool):
                    if current_value == threshold:
                        return level
                else:
                    if current_value >= threshold:
                        return level
                        
        except (ValueError, TypeError):
            pass
            
        return None
        
    def _should_notify(self, entity_id: str, alert_level: str) -> bool:
        """Check if we should send notification (throttling logic)"""
        last_notification = self.last_notifications.get(entity_id)
        if not last_notification:
            return True
            
        # Calculate throttling based on alert level
        throttle_minutes = {
            "WARNING": 60,    # 1 hour
            "ALERT": 30,      # 30 minutes
            "CRITICAL": 10    # 10 minutes
        }.get(alert_level, 60)
        
        time_since_last = (dt_util.utcnow() - last_notification).total_seconds() / 60
        return time_since_last >= throttle_minutes
        
    async def _send_cumulative_notification(self, alerts: List[Dict]):
        """Send cumulative notification using AI to create message"""
        try:
            # Generate AI message
            message = await self._generate_alert_message(alerts)
            
            if self.use_input_text:
                # Update input_text entity
                timestamp = dt_util.utcnow().strftime("%H:%M:%S")
                full_message = f"[{timestamp}] {message}"
                await self._update_input_text(full_message)
                _LOGGER.info(f"Updated input_text for {len(alerts)} alerts")
                
            else:
                # Send traditional notification
                if not self.notification_service:
                    _LOGGER.warning("No notification service configured")
                    return
                    
                await self.hass.services.async_call(
                    "notify",
                    self.notification_service.replace("notify.", ""),
                    {
                        "title": "🏠 HASS AI Alert",
                        "message": message,
                        "data": {
                            "priority": "high" if any(a["level"] == "CRITICAL" for a in alerts) else "normal",
                            "tag": "hass_ai_alert",
                            "actions": [
                                {"action": "view_alerts", "title": "View Alerts"},
                                {"action": "dismiss", "title": "Dismiss"}
                            ]
                        }
                    }
                )
                _LOGGER.info(f"Sent notification for {len(alerts)} alerts via {self.notification_service}")
            
        except Exception as e:
            _LOGGER.error(f"Error sending notification: {e}")
            
    async def _generate_alert_message(self, alerts: List[Dict]) -> str:
        """Generate AI-powered alert message"""
        try:
            from .intelligence import _query_local_agent
            
            # Prepare alert data for AI
            alert_details = []
            for alert in alerts:
                entity_id = alert["entity_id"]
                state = self.hass.states.get(entity_id)
                
                if state:
                    alert_details.append({
                        "entity": entity_id,
                        "name": state.attributes.get("friendly_name", entity_id),
                        "level": alert["level"],
                        "value": state.state,
                        "unit": state.attributes.get("unit_of_measurement", ""),
                        "weight": alert["weight"]
                    })
                    
            # Sort by priority and weight
            alert_details.sort(key=lambda x: (ALERT_LEVELS[x["level"]]["priority"], -x["weight"]), reverse=True)
            
            # Create AI prompt
            language = self.hass.config.language or "en"
            is_italian = language.startswith('it')
            
            if is_italian:
                prompt = f"""Crea un messaggio di allerta conciso per la casa intelligente.

ALLERTE ATTIVE ({len(alert_details)}):
{chr(10).join([f"• {a['level']} - {a['name']}: {a['value']}{a['unit']} (peso {a['weight']})" for a in alert_details])}

REGOLE:
- Messaggio max 200 caratteri
- Usa emoji appropriate per livello
- Priorità agli alert CRITICAL/ALERT
- Raggruppa alert simili
- Suggerisci azione se necessario

FORMATO: [emoji] [stato critico] + [dettaglio principale] + [azione consigliata]"""
            else:
                prompt = f"""Create a concise smart home alert message.

ACTIVE ALERTS ({len(alert_details)}):
{chr(10).join([f"• {a['level']} - {a['name']}: {a['value']}{a['unit']} (weight {a['weight']})" for a in alert_details])}

RULES:
- Message max 200 characters
- Use appropriate emojis for level
- Priority to CRITICAL/ALERT
- Group similar alerts
- Suggest action if needed

FORMAT: [emoji] [critical status] + [main detail] + [recommended action]"""

            # Get conversation agent from HASS AI configuration
            conversation_agent = None
            for entry_id, entry_data in self.hass.data.get("hass_ai", {}).items():
                if isinstance(entry_data, dict) and "config" in entry_data:
                    conversation_agent = entry_data["config"].get("conversation_agent")
                    break

            # Get AI response
            if conversation_agent:
                response = await _query_local_agent(self.hass, prompt, conversation_agent)
                return response.strip()
                
        except Exception as e:
            _LOGGER.error(f"Error generating AI alert message: {e}")
            
        # Fallback message
        critical_count = sum(1 for a in alerts if a["level"] == "CRITICAL")
        alert_count = sum(1 for a in alerts if a["level"] == "ALERT")
        warning_count = sum(1 for a in alerts if a["level"] == "WARNING")
        
        if critical_count:
            return f"🔥 {critical_count} CRITICAL alerts detected! Check your home immediately."
        elif alert_count:
            return f"🚨 {alert_count} alerts require attention in your smart home."
        else:
            return f"⚠️ {warning_count} warnings detected in your home system."
            
    async def update_monitored_entities(self, entities_data: Dict):
        """Update monitored entities from AI analysis results"""
        alert_entities = {}
        
        for entity_id, data in entities_data.items():
            # Check if entity has ALERTS category
            categories = data.get("category", [])
            if isinstance(categories, str):
                categories = [categories]
                
            if "ALERTS" in categories:
                alert_entities[entity_id] = data
                
        # Configure new alert entities
        for entity_id, data in alert_entities.items():
            if entity_id not in self.monitored_entities:
                await self.configure_entity_alerts(entity_id, data)
                
        _LOGGER.info(f"Updated {len(alert_entities)} alert entities for monitoring")
        
    async def get_alert_status(self) -> Dict:
        """Get current alert monitoring status"""
        active_alerts = {}
        total_monitored = len(self.monitored_entities)
        
        for entity_id, config in self.monitored_entities.items():
            alert_level = await self._check_entity_alert(entity_id, config)
            if alert_level:
                state = self.hass.states.get(entity_id)
                active_alerts[entity_id] = {
                    "level": alert_level,
                    "value": state.state if state else "unknown",
                    "weight": config.get("weight", 3),
                    "thresholds": config.get("thresholds", {})
                }
                
        return {
            "monitoring_enabled": self.is_monitoring,
            "total_monitored": total_monitored,
            "active_alerts": active_alerts,
            "notification_service": self.notification_service,
            "use_input_text": self.use_input_text,
            "input_text_entity": self.input_text_entity,
            "input_text_exists": self.hass.states.get(self.input_text_entity) is not None,
            "last_check": dt_util.utcnow().isoformat()
        }
