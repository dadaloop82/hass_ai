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
from homeassistant.helpers import storage
from homeassistant.util import dt as dt_util
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE
from .const import DOMAIN
import json

_LOGGER = logging.getLogger(__name__)

# Alert level configurations
ALERT_LEVELS = {
    "WARNING": {"color": "#ff9800", "icon": "⚠️", "priority": 1},
    "ALERT": {"color": "#f44336", "icon": "🚨", "priority": 2}, 
    "CRITICAL": {"color": "#d32f2f", "icon": "🔥", "priority": 3}
}

# No default thresholds - all thresholds must come from AI analysis
# This ensures intelligent, context-aware threshold generation for every entity type

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
            store = storage.Store(self.hass, 1, f"{DOMAIN}_alert_config")
            config = await store.async_load() or {}
            
            self.notification_service = config.get("notification_service", "notify.notify")
            self.use_input_text = config.get("use_input_text", False)
            self.input_text_entity = config.get("input_text_entity", "input_text.hass_ai_alerts")
            self.monitored_entities = config.get("monitored_entities", {})
            
            # CRITICAL: Clean up any invalid entities that were loaded from storage
            await self._cleanup_invalid_monitored_entities()
            
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
            store = storage.Store(self.hass, 1, f"{DOMAIN}_alert_config")
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
    
    async def _cleanup_invalid_monitored_entities(self):
        """Clean up any invalid entities from monitored_entities at startup"""
        try:
            entities_to_remove = []
            for entity_id in list(self.monitored_entities.keys()):
                if not self.is_valid_alert_entity(entity_id, {}):
                    entities_to_remove.append(entity_id)
                    domain = entity_id.split('.')[0]
                    _LOGGER.warning(f"STARTUP CLEANUP: Removing {entity_id} - domain '{domain}' is excluded")
            
            for entity_id in entities_to_remove:
                # Clear from all tracking dictionaries
                if entity_id in self.monitored_entities:
                    del self.monitored_entities[entity_id]
                if entity_id in self.last_notifications:
                    del self.last_notifications[entity_id]
                if entity_id in self.active_alerts:
                    del self.active_alerts[entity_id]
            
            if entities_to_remove:
                await self._save_configuration()
                _LOGGER.info(f"Startup cleanup: Removed {len(entities_to_remove)} invalid entities from monitoring")
                
        except Exception as e:
            _LOGGER.error(f"Error during startup cleanup: {e}")
            
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
            
    def is_valid_alert_entity(self, entity_id: str, entity_data: Dict) -> bool:
        """
        Determine if an entity is suitable for alert monitoring.
        Only numeric, boolean, or predefined value entities are valid.
        """
        domain = entity_id.split('.')[0]
        state = self.hass.states.get(entity_id)
        
        # Exclude domains that contain free text or non-deterministic values
        EXCLUDED_DOMAINS = {
            "input_text",           # Free text input
            "input_datetime",       # Date/time selection
            "input_select",         # Dropdown selection (text values)
            "device_tracker",       # Location names (home, away, etc.)
            "person",              # Location tracking (text based)
            "zone",                # Geographic zones
            "weather",             # Weather conditions (text descriptions)
            "media_player",        # Media states (titles, artists, etc.)
            "calendar",            # Calendar events (text descriptions)
            "image",               # Image data
            "camera",              # Camera streams
            "tts",                 # Text-to-speech
            "conversation",        # Conversation agents
            "persistent_notification", # Notification messages
            "automation",          # Automation states (limited utility)
            "script",              # Script execution (limited utility)
            "scene",               # Scene states (limited utility)
            "group",               # Group states (aggregated, not direct)
            "remote",              # Remote control states
            "vacuum",              # Vacuum states (docking, cleaning, etc.)
            "timer",               # Timer states
            "counter",             # Counter values (might be valid but often not alertable)
            "input_number",        # User input numbers (not sensor data)
            "input_boolean",       # User toggles (not sensor data)
            "sun",                 # Sun position (predictable, not alertable)
            "updater",             # Update checker (text based)
        }
        
        if domain in EXCLUDED_DOMAINS:
            return False
        
        if not state:
            return False
            
        current_state = state.state
        attributes = state.attributes or {}
        
        # Skip unavailable or unknown states
        if current_state in [STATE_UNKNOWN, STATE_UNAVAILABLE, None]:
            return False
            
        # Domain-based validation
        if domain == "sensor":
            # Numeric sensors with units are good candidates
            unit = attributes.get("unit_of_measurement")
            device_class = attributes.get("device_class")
            
            # Battery sensors - always valid
            if device_class == "battery" or "battery" in entity_id.lower():
                return True
                
            # Temperature, humidity, pressure sensors
            if device_class in ["temperature", "humidity", "pressure", "illuminance", "power", "energy"]:
                return True
                
            # Numeric values with units
            if unit and self._is_numeric_state(current_state):
                return True
                
            # CO2, AQI, and other measurable values
            if any(keyword in entity_id.lower() for keyword in ["co2", "aqi", "pm", "noise", "signal"]):
                return self._is_numeric_state(current_state)
                
            # Avoid text-based sensors
            if any(keyword in entity_id.lower() for keyword in ["status", "mode", "text", "message", "name"]):
                return False
                
            # Health monitoring sensors
            if any(keyword in entity_id.lower() for keyword in ["heart", "oxygen", "blood", "steps"]):
                return self._is_numeric_state(current_state)
                
            return False
            
        elif domain == "binary_sensor":
            # Most binary sensors are valid for alerts
            device_class = attributes.get("device_class")
            
            # Security and safety sensors
            if device_class in ["door", "window", "motion", "smoke", "gas", "moisture", "safety"]:
                return True
                
            # Connectivity and update sensors  
            if device_class in ["connectivity", "update", "problem"]:
                return True
                
            # Generic binary sensors with meaningful names
            if any(keyword in entity_id.lower() for keyword in ["open", "closed", "detected", "alarm", "alert"]):
                return True
                
            return False
            
        elif domain == "switch":
            # Only security/safety switches
            if any(keyword in entity_id.lower() for keyword in ["security", "alarm", "emergency", "safety"]):
                return True
            return False
            
        elif domain == "light":
            # Only emergency/indicator lights
            if any(keyword in entity_id.lower() for keyword in ["emergency", "alarm", "indicator", "warning"]):
                return True
            return False
            
        elif domain == "device_tracker":
            # Presence can be an alert (person not home)
            return True
            
        elif domain == "person":
            # Person presence/location
            return True
            
        # Default: reject text-based or highly variable entities
        return False
        
    def _is_numeric_state(self, state_value: str) -> bool:
        """Check if a state value is numeric"""
        try:
            float(state_value)
            return True
        except (ValueError, TypeError):
            return False
            
    async def configure_entity_alerts(self, entity_id: str, entity_data: Dict, custom_thresholds: Optional[Dict] = None):
        """Configure alert thresholds for an entity"""
        
        # CRITICAL: First validate if entity is suitable for monitoring
        if not self.is_valid_alert_entity(entity_id, entity_data):
            domain = entity_id.split('.')[0]
            _LOGGER.warning(f"REJECTING {entity_id} - domain '{domain}' is in excluded list or not suitable for alerts")
            return
            
        # Use only custom thresholds (from AI analysis) - no defaults!
        thresholds = custom_thresholds
        
        if not thresholds:
            # If no AI-generated thresholds provided, we cannot configure this entity
            _LOGGER.debug(f"Skipping {entity_id} - no AI-generated thresholds provided (AI analysis required)")
            return
            
        domain = entity_id.split('.')[0]
        entity_type = self._detect_entity_type(entity_id, entity_data)
            
        self.monitored_entities[entity_id] = {
            "weight": entity_data.get("overall_weight", 3),
            "thresholds": thresholds,
            "entity_type": entity_type,
            "last_check": None,
            "current_level": None,
            "enabled": True
        }
        
        await self._save_configuration()
        _LOGGER.info(f"Configured AI-generated alerts for {entity_id}: {thresholds}")
        
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
        _LOGGER.info("🔔 Alert monitoring started")
        
    async def _stop_monitoring(self):
        """Stop the monitoring loop"""
        if not self.is_monitoring:
            return
            
        self.is_monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        _LOGGER.info("🔔 Alert monitoring stopped")
        
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
        entities_checked = 0
        
        try:
            # Send monitoring start signal to frontend
            self._send_monitoring_signal("start", {"count": len(self.monitored_entities)})
            
            for entity_id, config in self.monitored_entities.items():
                if not config.get("enabled", True):
                    continue
                    
                # Skip entities without valid thresholds
                thresholds = config.get("thresholds", {})
                if not thresholds or not any(thresholds.values()):
                    continue
                    
                # Filter by minimum weight if configured
                weight = config.get("weight", 3)
                min_weight = self._get_min_weight_filter()
                if weight < min_weight:
                    continue
                    
                entities_checked += 1
                
                # Calculate check interval based on weight
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
                
        except Exception as e:
            _LOGGER.error(f"Error during entity monitoring: {e}")
        finally:
            # Send monitoring end signal to frontend
            self._send_monitoring_signal("end", {"entities_checked": entities_checked})
            
    def _calculate_check_interval(self, weight: int) -> float:
        """Calculate check interval based on weight: peso 5: 30 secondi, peso 4: 1 minuto, peso 3: 5 minuti, peso 2: 15 minuti, peso 1: 30 minuti"""
        weight_intervals = {5: 0.5, 4: 1.0, 3: 5.0, 2: 15.0, 1: 30.0}  # minutes
        return weight_intervals.get(weight, 5.0)  # Default to 5 minutes for invalid weights

    def _send_monitoring_signal(self, signal_type: str, details=None):
        """Send monitoring signal to frontend via websocket."""
        try:
            signal_data = {
                "type": f"hass_ai_monitoring_{signal_type}",
                "timestamp": datetime.now().isoformat(),
                "details": details or {}
            }
            
            # Send to all connected websocket clients
            self.hass.loop.call_soon_threadsafe(
                self.hass.bus.async_fire,
                "hass_ai_monitoring_signal",
                signal_data
            )
        except Exception as e:
            _LOGGER.warning(f"Error sending monitoring signal: {e}")

    def _get_min_weight_filter(self) -> int:
        """Get minimum weight filter for current monitoring level."""
        config = self.hass.data.get(DOMAIN, {})
        return config.get("min_weight_filter", 3)  # Default to weight 3 and above
            
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
                    # Determine if this sensor should alert on LOW values or HIGH values
                    should_alert_on_low = self._should_alert_on_low_value(entity_id, state)
                    
                    if should_alert_on_low:
                        # Alert when value is BELOW or EQUAL to threshold (battery, signal strength, etc.)
                        if current_value <= threshold:
                            return level
                    else:
                        # Alert when value is ABOVE or EQUAL to threshold (temperature, humidity, etc.)
                        if current_value >= threshold:
                            return level
                        
        except (ValueError, TypeError):
            pass
            
        return None

    def _should_alert_on_low_value(self, entity_id: str, state: State) -> bool:
        """Determine if this sensor should alert when value is LOW (vs HIGH)"""
        entity_lower = entity_id.lower()
        device_class = state.attributes.get('device_class', '').lower()
        unit = state.attributes.get('unit_of_measurement', '').lower()
        
        # Sensors that should alert on LOW values
        low_value_indicators = [
            # Battery related
            'battery', 'batteria', 'power_level',
            # Signal strength
            'signal', 'rssi', 'wifi', 'segnale', 'strength',
            # Storage/Disk space  
            'available', 'free', 'remaining', 'libero', 'disponibile',
            # Health/Performance indicators
            'uptime', 'connectivity', 'connettivita',
            # Ink/Toner
            'ink', 'toner', 'cartridge', 'cartuccia',
            # Air quality (sometimes lower is better)
            'air_quality' if 'poor' not in entity_lower else None
        ]
        
        # Device classes that typically alert on low values
        low_value_device_classes = [
            'battery', 'signal_strength', 'power'
        ]
        
        # Units that typically indicate "low is bad"
        low_value_units = ['%', 'percent', 'gb', 'mb', 'tb']
        
        # Check entity name for low-value keywords
        if any(keyword and keyword in entity_lower for keyword in low_value_indicators):
            return True
            
        # Check device class
        if device_class in low_value_device_classes:
            return True
            
        # Special case: if it's a percentage and looks like battery/signal/storage
        if unit in ['%', 'percent'] and any(keyword in entity_lower for keyword in ['battery', 'signal', 'storage', 'disk', 'available', 'free']):
            return True
            
        # Default: most sensors alert on HIGH values (temperature, humidity, CPU usage, etc.)
        return False
        
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
            
            # Check if user prefers friendly messages
            config = self.hass.data.get(DOMAIN, {})
            use_friendly_messages = config.get("use_friendly_messages", False)
            
            if use_friendly_messages:
                if is_italian:
                    prompt = f"""Crea un messaggio informale e amichevole per allerte casa intelligente.

ALLERTE ({len(alert_details)}):
{chr(10).join([f"• {a['level']} - {a['name']}: {a['value']}{a['unit']}" for a in alert_details])}

STILE:
- Tono amichevole e rassicurante
- Usa emoji divertenti 😊
- Come se parlassi con un amico
- Max 200 caratteri
- Evita allarmismi
- Suggerisci soluzioni semplici

ESEMPI:
"😊 Hey! La batteria del sensore è un po' scarica (12%), magari è ora di cambiarla!"
"🔋 Piccolo promemoria: alcuni sensori potrebbero aver bisogno di nuove batterie"
"🏠 Tutto ok in casa, solo qualche sensore che chiede attenzione!"

FORMATO: [emoji amichevole] [messaggio rassicurante] + [suggerimento pratico]"""
                else:
                    prompt = f"""Create a friendly, informal smart home alert message.

ALERTS ({len(alert_details)}):
{chr(10).join([f"• {a['level']} - {a['name']}: {a['value']}{a['unit']}" for a in alert_details])}

STYLE:
- Friendly and reassuring tone
- Use fun emojis 😊
- Like talking to a friend
- Max 200 characters
- Avoid alarmist language
- Suggest simple solutions

EXAMPLES:
"😊 Hey! Your sensor battery is getting low (12%), might be time for a change!"
"🔋 Friendly reminder: a few sensors could use fresh batteries"
"🏠 Everything's good at home, just some sensors asking for attention!"

FORMAT: [friendly emoji] [reassuring message] + [practical suggestion]"""
            else:
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
            # CRITICAL: Never monitor our own input_text entity!
            if entity_id == self.input_text_entity:
                _LOGGER.debug(f"Skipping {entity_id} - this is our own alert display entity")
                continue
                
            # Check if entity has ALERTS category
            categories = data.get("category", [])
            if isinstance(categories, str):
                categories = [categories]
                
            if "ALERTS" in categories:
                # Validate if entity is suitable for alert monitoring
                if self.is_valid_alert_entity(entity_id, data):
                    alert_entities[entity_id] = data
                else:
                    _LOGGER.debug(f"Entity {entity_id} has ALERTS category but is not suitable for monitoring (text/variable values)")
        
        # Remove entities without valid thresholds from monitored_entities
        entities_to_remove = []
        for entity_id, config in self.monitored_entities.items():
            # CRITICAL: Remove ALL entities that should be excluded by domain validation
            if not self.is_valid_alert_entity(entity_id, {}):
                entities_to_remove.append(entity_id)
                domain = entity_id.split('.')[0]
                _LOGGER.warning(f"FORCE REMOVING {entity_id} - domain '{domain}' should be excluded from alerts!")
                continue
                
            # Remove if entity no longer exists in Home Assistant
            if not self.hass.states.get(entity_id):
                entities_to_remove.append(entity_id)
                _LOGGER.info(f"Removing {entity_id} - entity no longer exists")
                continue
                
            # Remove if no valid thresholds
            thresholds = config.get("thresholds", {})
            if not thresholds or not any(thresholds.values()):
                entities_to_remove.append(entity_id)
                _LOGGER.debug(f"Removing {entity_id} - no valid thresholds")
                continue
                
            # Remove if entity is no longer in ALERTS category
            if entity_id not in alert_entities:
                entities_to_remove.append(entity_id)
                _LOGGER.info(f"Removing {entity_id} - no longer has ALERTS category")
                
        for entity_id in entities_to_remove:
            # Also clear from last_notifications to stop notifications completely
            if entity_id in self.last_notifications:
                del self.last_notifications[entity_id]
            if entity_id in self.active_alerts:
                del self.active_alerts[entity_id]
            del self.monitored_entities[entity_id]
                
        # Configure new alert entities
        for entity_id, data in alert_entities.items():
            if entity_id not in self.monitored_entities:
                await self.configure_entity_alerts(entity_id, data)
                
        _LOGGER.info(f"Updated {len(alert_entities)} valid alert entities for monitoring")
        
        # Log which entities were filtered out
        filtered_count = len([entity_id for entity_id, entity_data in entities_data.items() 
                            if "ALERTS" in (entity_data.get("category", []) if isinstance(entity_data.get("category", []), list) 
                                          else [entity_data.get("category", "")]) 
                            and not self.is_valid_alert_entity(entity_id, entity_data)])
        if filtered_count > 0:
            _LOGGER.info(f"Filtered out {filtered_count} text/variable entities from alert monitoring")
        
    async def get_alert_status(self) -> Dict:
        """Get current alert monitoring status"""
        active_alerts = {}
        all_alert_entities = {}
        total_monitored = len(self.monitored_entities)
        
        for entity_id, config in self.monitored_entities.items():
            alert_level = await self._check_entity_alert(entity_id, config)
            state = self.hass.states.get(entity_id)
            
            # Get entity info
            friendly_name = state.attributes.get("friendly_name", entity_id) if state else entity_id
            current_value = state.state if state else "unknown"
            unit = state.attributes.get("unit_of_measurement", "") if state else ""
            device_class = state.attributes.get("device_class", "") if state else ""
            
            # Add to all entities list
            all_alert_entities[entity_id] = {
                "friendly_name": friendly_name,
                "current_value": current_value,
                "unit": unit,
                "device_class": device_class,
                "weight": config.get("weight", 3),
                "thresholds": config.get("thresholds", {}),
                "entity_type": config.get("entity_type", "unknown"),
                "last_check": config.get("last_check"),
                "enabled": config.get("enabled", True),
                "is_alert": alert_level is not None,
                "alert_level": alert_level
            }
            
            # Add to active alerts if in alert state
            if alert_level:
                active_alerts[entity_id] = {
                    "level": alert_level,
                    "value": current_value,
                    "weight": config.get("weight", 3),
                    "thresholds": config.get("thresholds", {}),
                    "friendly_name": friendly_name,
                    "unit": unit
                }
                
        return {
            "monitoring_enabled": self.is_monitoring,
            "total_monitored": total_monitored,
            "active_alerts": active_alerts,
            "all_alert_entities": all_alert_entities,
            "notification_service": self.notification_service,
            "use_input_text": self.use_input_text,
            "input_text_entity": self.input_text_entity,
            "input_text_exists": self.hass.states.get(self.input_text_entity) is not None,
            "last_check": dt_util.utcnow().isoformat()
        }
        
    async def get_detailed_alert_report(self) -> Dict:
        """Get detailed report of all alert entities and their states"""
        report = {
            "timestamp": dt_util.utcnow().isoformat(),
            "monitoring_enabled": self.is_monitoring,
            "monitored_entities": {},
            "alert_summary": {
                "total_entities": 0,
                "enabled_entities": 0,
                "active_alerts": 0,
                "critical_alerts": 0,
                "alert_alerts": 0,
                "warning_alerts": 0
            }
        }
        
        for entity_id, config in self.monitored_entities.items():
            state = self.hass.states.get(entity_id)
            alert_level = await self._check_entity_alert(entity_id, config)
            
            entity_info = {
                "entity_id": entity_id,
                "friendly_name": state.attributes.get("friendly_name", entity_id) if state else entity_id,
                "domain": entity_id.split('.')[0],
                "current_state": state.state if state else "unavailable",
                "unit": state.attributes.get("unit_of_measurement", "") if state else "",
                "device_class": state.attributes.get("device_class", "") if state else "",
                "weight": config.get("weight", 3),
                "entity_type": config.get("entity_type", "unknown"),
                "thresholds": config.get("thresholds", {}),
                "enabled": config.get("enabled", True),
                "last_check": config.get("last_check"),
                "current_alert_level": alert_level,
                "is_valid_state": state is not None and state.state not in [STATE_UNKNOWN, STATE_UNAVAILABLE],
                "state_attributes": dict(state.attributes) if state else {}
            }
            
            report["monitored_entities"][entity_id] = entity_info
            
            # Update summary
            report["alert_summary"]["total_entities"] += 1
            if config.get("enabled", True):
                report["alert_summary"]["enabled_entities"] += 1
            
            if alert_level:
                report["alert_summary"]["active_alerts"] += 1
                if alert_level == "CRITICAL":
                    report["alert_summary"]["critical_alerts"] += 1
                elif alert_level == "ALERT":
                    report["alert_summary"]["alert_alerts"] += 1
                elif alert_level == "WARNING":
                    report["alert_summary"]["warning_alerts"] += 1
        
        return report
