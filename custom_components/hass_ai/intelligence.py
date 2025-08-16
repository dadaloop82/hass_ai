from __future__ import annotations
import logging
import json
import asyncio
from datetime import datetime
from typing import Optional

from .const import (
    AI_PROVIDER_LOCAL, 
    CONF_CONVERSATION_AGENT, 
    MAX_TOKEN_ERROR_KEYWORDS,
    TOKEN_LIMIT_ERROR_MESSAGE,
    MIN_BATCH_SIZE,
    BATCH_REDUCTION_FACTOR
)
from homeassistant.core import HomeAssistant, State
from homeassistant.components import conversation, websocket_api
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

def _estimate_tokens(text: str) -> int:
    """Estimate token count for text (rough approximation: 1 token ≈ 4 characters)."""
    return len(text) // 4

def _get_localized_message(message_key: str, language: str, **kwargs) -> str:
    """Get localized messages based on language."""
    is_italian = language.startswith('it')
    
    messages = {
        'batch_request': {
            'it': f"📤 Invio richiesta per gruppo {kwargs.get('batch_num')} ({kwargs.get('entities_count')} dispositivi)",
            'en': f"📤 Sending request for group {kwargs.get('batch_num')} ({kwargs.get('entities_count')} devices)"
        },
        'batch_response': {
            'it': f"📥 Risposta ricevuta per gruppo {kwargs.get('batch_num')} ({kwargs.get('entities_count')} dispositivi)",
            'en': f"📥 Response received for group {kwargs.get('batch_num')} ({kwargs.get('entities_count')} devices)"
        },
        'batch_reduction': {
            'it': f"⚠️ Errore di risposta, riprovo con gruppo più piccolo (tentativo {kwargs.get('retry_attempt')})",
            'en': f"⚠️ Response error, retrying with smaller group (attempt {kwargs.get('retry_attempt')})"
        },
        'token_limit_title': {
            'it': "Token Limit Raggiunti",
            'en': "Token Limit Reached"
        },
        'token_limit_message': {
            'it': f"Scansione fermata al gruppo {kwargs.get('batch')}. Riprova con gruppi più piccoli.",
            'en': f"Scan stopped at group {kwargs.get('batch')}. Try again with smaller groups."
        }
    }
    
    return messages.get(message_key, {}).get('it' if is_italian else 'en', f"Message key '{message_key}' not found")

def _create_localized_prompt(batch_states: list[State], entity_details: list[str], language: str, compact_mode: bool = False, analysis_type: str = "comprehensive") -> str:
    """Create a comprehensive prompt for entity analysis that includes all types of analysis."""
    
    is_italian = language.startswith('it')
    
    if compact_mode:
        # Ultra-compact prompt when hitting token limits
        entity_summary = []
        for state in batch_states:
            # Essential info only: entity_id, domain, state, name
            name = state.attributes.get('friendly_name', state.entity_id.split('.')[-1])
            summary = f"{state.entity_id}({state.domain},{state.state},{name[:20]})"
            entity_summary.append(summary)
        
        if is_italian:
            return (
                f"Valuta {len(batch_states)} entità HA per utilità domotica. Punteggio 0-5 (0=inutile, 5=essenziale). "
                f"JSON: [{{\"entity_id\":\"...\",\"rating\":0-5,\"reason\":\"utilità automazioni\",\"category\":\"DATA/CONTROL/ALERTS\",\"management_type\":\"USER/SERVICE\"}}]. "
                f"REASON: utilità domotica. Entità: " + ", ".join(entity_summary[:30])
            )
        else:
            return (
                f"Evaluate {len(batch_states)} HA entities for home automation utility. Score 0-5 (0=useless, 5=essential). "
                f"JSON: [{{\"entity_id\":\"...\",\"rating\":0-5,\"reason\":\"automation utility\",\"category\":\"DATA/CONTROL/ALERTS\",\"management_type\":\"USER/SERVICE\"}}]. "
                f"REASON: home automation value. Entities: " + ", ".join(entity_summary[:30])
            )
    
    # Comprehensive analysis prompt that covers all aspects
    if is_italian:
        prompt = (
            f"Analizza {len(batch_states)} entità Home Assistant per CASA INTELLIGENTE. Valuta l'utilità considerando TUTTI questi aspetti con pari importanza. Punteggio 0-5:\n"
            f"0=Inutile, 1=Molto poco utile, 2=Poco utile, 3=Mediamente utile, 4=Molto utile, 5=Essenziale\n"
            f"\nCRITERI DI VALUTAZIONE EQUILIBRATA (tutti importanti):\n"
            f"• BENESSERE DELLE PERSONE: Parametri vitali, fitness, qualità dell'aria, comfort\n"
            f"• GESTIONE DELLA CASA: Controllo luci, climatizzazione, sicurezza, presenza\n"
            f"• OTTIMIZZAZIONE AUTOMAZIONI: Efficienza, logiche, trigger, condizioni\n"
            f"• RISPARMIO ENERGETICO: Monitoraggio consumi, ottimizzazione, controllo dispositivi\n"
            f"\nCATEGORIE (UN'ENTITÀ PUÒ AVERE PIÙ CATEGORIE, scegli TUTTE quelle che si applicano):\n"
            f"- DATA: Fornisce dati o misurazioni utili\n"
            f"- CONTROL: Permette il controllo diretto di dispositivi o servizi\n"
            f"- ALERTS: Può generare allarmi o monitoraggio critico\n"
            f"- SERVICE: Può essere gestita tramite servizi, automazioni o API\n"
            f"\nESEMPI CATEGORIE MULTIPLE:\n"
            f"• Sensore batteria smartphone: ['DATA', 'ALERTS']\n"
            f"• Sensore temperatura: ['DATA', 'ALERTS']\n"
            f"• Update sensor: ['DATA', 'ALERTS', 'SERVICE']\n"
            f"• Interruttore luci: ['CONTROL', 'SERVICE']\n"
            f"• Sensore presenza: ['DATA']\n"
            f"• Conversation agent: ['CONTROL', 'SERVICE']\n"
            f"\nAssegna tutte le categorie che si applicano.\n"
            f"\nJSON: [{{\"entity_id\":\"...\",\"rating\":0-5,\"reason\":\"DESCRIZIONE SPECIFICA del valore\",\"category\":[\"DATA\",\"ALERTS\",\"CONTROL\",\"SERVICE\"],\"management_type\":\"USER/SERVICE\"}}]\n"
            f"- ALERTS: Monitoraggio critico (batterie, salute fuori norma, emergenze, manutenzione)\n"
            f"\nVALUTAZIONE ALERTS:\n"
            f"• Sensori batteria → SEMPRE ALERTS\n"
            f"• Parametri salute critici (ossigeno <95%, battito anomalo) → ALERTS\n"
            f"• Update e manutenzione → ALERTS\n"
            f"• Condizioni ambientali estreme → ALERTS\n"
            f"\nTIPO GESTIONE:\n"
            f"- USER: Utente controlla direttamente\n"
            f"- SERVICE: Richiede automazioni/servizi (conversation, telecamere, cloud)\n"
            f"\nREASON: Spiega COSA FA e PERCHÉ è importante per casa intelligente O benessere personale!\n"
            f"ESEMPI BUONI: 'Monitora saturazione ossigeno per salute cardiovascolare', 'Controlla illuminazione per comfort', 'Rileva presenza per sicurezza'\n"
            f"\nJSON: [{{\"entity_id\":\"...\",\"rating\":0-5,\"reason\":\"DESCRIZIONE SPECIFICA del valore per domotica/salute/benessere\",\"category\":\"DATA/CONTROL/ALERTS\",\"management_type\":\"USER/SERVICE\"}}]\n"
            f"REASON OBBLIGATORIO: NON sottovalutare mai i parametri di salute! Saturazione ossigeno, battito cardiaco, pressione sono VITALI. Descrivi COSA FA l'entità e PERCHÉ è importante per domotica/salute/benessere!\n\n" + "\n".join(entity_details)
        )
    else:
        prompt = (
            f"Analyze {len(batch_states)} Home Assistant entities for SMART HOME. Evaluate usefulness considering ALL these aspects with equal importance. Rating 0-5:\n"
            f"0=Useless, 1=Very low utility, 2=Low utility, 3=Medium utility, 4=Very useful, 5=Essential\n"
            f"\nBALANCED EVALUATION CRITERIA (all equally important):\n"
            f"• PERSONAL WELLNESS: Vital parameters, fitness, air quality, comfort\n"
            f"• HOME MANAGEMENT: Light control, climate, security, presence\n"
            f"• AUTOMATION OPTIMIZATION: Efficiency, logic, triggers, conditions\n"
            f"• ENERGY SAVING: Consumption monitoring, optimization, device control\n"
            f"\nCATEGORIES (ENTITY CAN HAVE MULTIPLE CATEGORIES):\n"
            f"- DATA: Useful information and measurements\n"
            f"- CONTROL: Actionable controls\n"
            f"- ALERTS: Critical monitoring and alarms\n"
            f"\nMULTI-CATEGORY EXAMPLES:\n"
            f"• Phone battery sensor: ['DATA', 'ALERTS'] (information + low battery alert)\n"
            f"• Temperature sensor: ['DATA', 'ALERTS'] (data + extreme temperature alert)\n"
            f"• Update sensor: ['DATA', 'ALERTS'] (information + maintenance alert)\n"
            f"• Light switch: ['CONTROL'] (control only)\n"
            f"• Presence sensor: ['DATA'] (information only)\n"
            f"\nALERTS: ALWAYS assign if entity can generate alarms or critical monitoring:\n"
            f"• Batteries (low), temperatures (extreme), wind (strong), available updates\n"
            f"• Health parameters out of range, offline devices, system errors\n"
            f"\nMANAGEMENT TYPE:\n"
            f"- USER: User controls directly\n"
            f"- SERVICE: Requires automations/services (conversation, cameras, cloud)\n"
            f"\nREASON: Explain WHAT IT DOES and WHY it's important for at least ONE of the 4 criteria above!\n"
            f"\nJSON: [{{\"entity_id\":\"...\",\"rating\":0-5,\"reason\":\"SPECIFIC description of value\",\"category\":[\"DATA\",\"ALERTS\"] or [\"CONTROL\"] etc,\"management_type\":\"USER/SERVICE\"}}]\n" + "\n".join(entity_details)
        )
    
    # Log token estimation
    token_count = _estimate_tokens(prompt)
    _LOGGER.info(f"Prompt tokens estimated: {token_count}, type: {analysis_type}")
    
    return prompt

# Entity importance categories for better classification
ENTITY_IMPORTANCE_MAP = {
    "climate": 4,  # HVAC controls are typically important
    "light": 3,    # Lights are moderately important
    "switch": 3,   # Switches are moderately important
    "sensor": 2,   # Sensors provide data but less critical for automation
    "binary_sensor": 2,
    "device_tracker": 3,  # Location tracking is important
    "alarm_control_panel": 5,  # Security is critical
    "lock": 5,     # Security related
    "camera": 4,   # Security/monitoring - can be enhanced
    "cover": 3,    # Blinds, garage doors etc
    "fan": 3,
    "media_player": 2,  # Can be enhanced with audio analysis
    "weather": 2,
    "sun": 1,      # Less critical for most automations
    "person": 4,   # Person tracking is important
}

# Auto-categorization based on domain and entity characteristics
def _auto_categorize_entity(state: State) -> tuple[list[str], str]:
    """Automatically categorize entity based on domain and characteristics.
    Returns (categories_list, management_type)."""
    domain = state.domain
    entity_id = state.entity_id
    attributes = state.attributes
    entity_state = state.state
    
    categories = []
    
    # Check for alerts/problems first
    if entity_state in ['unavailable', 'unknown', 'error']:
        return ['ALERTS'], 'SERVICE'
    
    # Battery sensors should be both DATA and ALERTS
    if 'battery' in entity_id.lower() or attributes.get('battery_level') is not None:
        return ['DATA', 'ALERTS'], 'USER'  # Data for monitoring + alerts for low battery
    
    # Update entities are both DATA and ALERTS
    if domain == 'update' or 'update' in entity_id.lower():
        return ['DATA', 'ALERTS'], 'SERVICE'  # Information + maintenance alerts
    
    # Domain-based categorization with multi-category support
    if domain == 'sun':
        # Sun provides important data for automation timing
        return ['DATA'], 'USER'
    elif domain == 'conversation':
        # Conversation agents require service integration
        return ['CONTROL'], 'SERVICE'  # Service because needs API/automation
    elif domain == 'camera':
        # Cameras provide data but require services to operate
        return ['DATA'], 'SERVICE'
    elif domain in ['sensor', 'binary_sensor']:
        # Improved sensor categorization with multi-category support
        entity_lower = entity_id.lower()
        
        # Health and fitness sensors - can have alerts for out-of-range values
        if any(keyword in entity_lower for keyword in ['heart_rate', 'calories', 'steps', 'distance', 'sleep', 'weight', 'blood', 'fitness', 'oxygen', 'saturation', 'pulse', 'bp', 'pressure', 'glucose', 'cholesterol', 'bmi', 'body_mass', 'hydration', 'stress', 'recovery']):
            # Health sensors provide data but can also alert if values are abnormal
            return ['DATA', 'ALERTS'], 'USER'
        
        # Environmental sensors that can trigger alerts
        if any(keyword in entity_lower for keyword in ['wind', 'storm', 'flood', 'earthquake', 'emergency']):
            return ['DATA', 'ALERTS'], 'USER'
        
        # Temperature sensors - data + alerts for extreme values
        if 'temperature' in entity_lower:
            return ['DATA', 'ALERTS'], 'USER'
            
        # System diagnostic sensors
        if any(keyword in entity_lower for keyword in ['rssi', 'linkquality', 'uptime', 'memory', 'cpu', 'disk', 'connection']):
            return ['DATA'], 'SERVICE'
        
        # Default sensors are DATA only
        return ['DATA'], 'USER'
        
    elif domain in ['weather']:
        return ['DATA'], 'USER'
    elif domain in ['device_tracker', 'person', 'zone']:
        return ['DATA'], 'USER'
    elif domain in ['switch', 'light', 'climate', 'cover', 'fan', 'media_player']:
        return ['CONTROL'], 'USER'
    elif domain in ['lock', 'alarm_control_panel']:
        return ['CONTROL'], 'SERVICE'
    elif domain in ['input_boolean', 'input_select', 'input_number', 'input_text']:
        return ['CONTROL'], 'USER'
    elif domain in ['alert', 'automation']:
        return ['ALERTS'], 'SERVICE'
    else:
        # Enhanced pattern matching for unknown domains
        entity_lower = entity_id.lower()
        
        # Weather patterns - for custom weather sensors
        if any(keyword in entity_lower for keyword in ['meteo', 'weather', 'forecast', 'temperatura', 'temperature', 'humidity', 'pressure', 'wind', 'rain', 'snow', 'precipitation']):
            return ['DATA'], 'USER'
        
        # Health and wellness patterns - data + alerts
        if any(keyword in entity_lower for keyword in ['health', 'heart', 'calories', 'steps', 'fitness', 'sleep', 'weight', 'oxygen', 'saturation', 'pulse', 'blood', 'pressure', 'glucose', 'bmi', 'hydration', 'stress', 'recovery']):
            return ['DATA', 'ALERTS'], 'USER'
        
        # Alert patterns - only alerts
        if any(keyword in entity_lower for keyword in ['error', 'warning', 'alert', 'alarm']):
            return ['ALERTS'], 'USER'
        
        # Control patterns  
        if any(keyword in entity_lower for keyword in ['switch', 'control', 'toggle', 'button', 'command']):
            return ['CONTROL'], 'USER'
            
        # Default to DATA for informational entities
        return ['DATA'], 'USER'

# Alert Severity Levels for user notification thresholds
ALERT_SEVERITY_LEVELS = {
    "LOW": {"description": "Low priority - informational", "priority": 1},
    "MEDIUM": {"description": "Medium priority - attention needed", "priority": 2}, 
    "HIGH": {"description": "High priority - immediate action", "priority": 3},
    "CRITICAL": {"description": "Critical - urgent intervention required", "priority": 4}
}

# Auto-threshold generation for different entity types
async def _generate_auto_thresholds(hass: HomeAssistant, entity_id: str, state: State) -> dict:
    """Generate automatic thresholds for an entity using AI evaluation."""
    domain = state.domain
    attributes = state.attributes
    current_value = state.state
    
    # Default thresholds
    result = {
        "auto_generated": True,
        "thresholds": {},
        "entity_type": "unknown"
    }
    
    try:
        # Get conversation agent for AI threshold generation
        conversation_agent = hass.data.get("hass_ai", {}).get("conversation_agent")
        if conversation_agent:
            # Create AI prompt for threshold generation
            unit = attributes.get('unit_of_measurement', '')
            device_class = attributes.get('device_class', '')
            
            # Check if this entity warrants alert thresholds - be more inclusive
            needs_thresholds = False
            entity_lower = entity_id.lower()
            
            if domain == 'binary_sensor':
                device_class = attributes.get('device_class', '')
                if (device_class in ['battery', 'problem', 'safety', 'smoke', 'gas', 'moisture', 'update'] or
                    any(keyword in entity_lower for keyword in ['battery', 'update', 'problem', 'error', 'warning', 'alert'])):
                    needs_thresholds = True
                    
            elif domain == 'sensor':
                try:
                    num_value = float(current_value)
                    # Much more inclusive criteria for sensors that need thresholds
                    if (any(keyword in entity_lower for keyword in ['battery', 'temperature', 'humidity', 'wind', 'cpu', 'memory', 'disk', 'signal', 'rssi', 'heart_rate', 'blood', 'weight', 'calories', 'steps']) or
                        device_class in ['battery', 'temperature', 'humidity', 'signal_strength', 'power'] or
                        'update' in entity_lower or 'health' in entity_lower):
                        needs_thresholds = True
                except (ValueError, TypeError):
                    # Even non-numeric sensors might need thresholds if they're alert-related
                    if any(keyword in entity_lower for keyword in ['battery', 'update', 'status', 'state', 'error', 'warning']):
                        needs_thresholds = True
            
            elif domain == 'update':
                # Update entities should always have thresholds
                needs_thresholds = True
            
            if needs_thresholds:
                # AI-generated thresholds prompt
                threshold_prompt = (
                    f"Proponi soglie di allerta intelligenti per l'entità: {entity_id}\n"
                    f"Valore attuale: {current_value} {unit}\n"
                    f"Tipo dispositivo: {device_class}\n"
                    f"Dominio: {domain}\n\n"
                    f"Genera 3 soglie di allerta (LOW, MEDIUM, HIGH) con valori specifici e appropriati.\n"
                    f"Considera l'utilizzo pratico nella domotica e benessere:\n\n"
                    f"ESEMPI PER TIPO:\n"
                    f"• Batterie: LOW=30%, MEDIUM=20%, HIGH=10% (critico)\n"
                    f"• Temperature casa: LOW=15°C, MEDIUM=10°C, HIGH=5°C (freddo) o LOW=28°C, MEDIUM=32°C, HIGH=35°C (caldo)\n"
                    f"• Umidità: LOW=30%, MEDIUM=25%, HIGH=20% (secco) o LOW=70%, MEDIUM=80%, HIGH=90% (umido)\n"
                    f"• Vento: LOW=20km/h, MEDIUM=40km/h, HIGH=60km/h (pericoloso)\n"
                    f"• CPU/Sistema: LOW=70%, MEDIUM=85%, HIGH=95% (sovraccarico)\n"
                    f"• Salute (battiti): LOW=50bpm, MEDIUM=40bpm, HIGH=35bpm (basso) o LOW=100bpm, MEDIUM=120bpm, HIGH=140bpm (alto)\n"
                    f"• Update: Presenza aggiornamenti disponibili\n\n"
                    f"SCEGLI VALORI REALISTICI per la domotica e considera il contesto dell'entità.\n\n"
                    f"JSON: {{\"LOW\":{{\"value\":numero,\"condition\":\"condizione leggibile\",\"description\":\"descrizione del problema\"}},\"MEDIUM\":{{\"value\":numero,\"condition\":\"condizione leggibile\",\"description\":\"descrizione del problema\"}},\"HIGH\":{{\"value\":numero,\"condition\":\"condizione leggibile\",\"description\":\"descrizione del problema\"}}}}"
                )
                
                try:
                    # Send to AI for threshold generation
                    ai_response = await conversation_agent.async_process(threshold_prompt, None, None)
                    if ai_response and hasattr(ai_response, 'response') and ai_response.response:
                        # Try to parse AI response
                        import json
                        response_text = ai_response.response.speech.get('plain', {}).get('speech', '') if hasattr(ai_response.response, 'speech') else str(ai_response.response)
                        
                        # Extract JSON from response
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1
                        if json_start >= 0 and json_end > json_start:
                            threshold_data = json.loads(response_text[json_start:json_end])
                            result.update({
                                "entity_type": "ai_generated",
                                "thresholds": threshold_data
                            })
                            return result
                            
                except Exception as e:
                    _LOGGER.debug(f"AI threshold generation failed for {entity_id}: {e}")
        
        # Fallback to basic thresholds for obvious cases
        if domain == 'binary_sensor':
            device_class = attributes.get('device_class', '')
            entity_lower = entity_id.lower()
            
            # Identify what should trigger alerts for binary sensors
            if (device_class in ['battery', 'problem', 'safety', 'smoke', 'gas', 'moisture', 'motion', 'door', 'window', 'connectivity', 'update'] or
                any(keyword in entity_lower for keyword in ['battery', 'problem', 'error', 'offline', 'disconnected', 'fault', 'alarm', 'warning', 'update', 'maintenance'])):
                
                # Determine what state is "alerting" based on device class and name patterns
                alert_state = 'on'  # Default
                alert_description = "Sensor activated"
                
                if device_class == 'battery' or 'battery' in entity_lower:
                    alert_state = 'on'  # Battery low = on
                    alert_description = "Battery is low"
                elif device_class in ['problem', 'safety', 'smoke', 'gas'] or any(word in entity_lower for word in ['problem', 'error', 'fault', 'smoke', 'gas']):
                    alert_state = 'on'  # Problem detected = on
                    alert_description = "Problem detected"
                elif device_class == 'connectivity' or any(word in entity_lower for word in ['offline', 'disconnected', 'connection']):
                    alert_state = 'off'  # Disconnected = off
                    alert_description = "Device disconnected"
                elif device_class == 'update' or 'update' in entity_lower:
                    alert_state = 'on'  # Update available = on
                    alert_description = "Update available"
                elif device_class in ['door', 'window'] or any(word in entity_lower for word in ['door', 'window']):
                    alert_state = 'on'  # Open = on (may be alerting depending on context)
                    alert_description = "Opening detected"
                
                result.update({
                    "entity_type": "binary_alert",
                    "alert_state": alert_state,
                    "thresholds": {
                        "LOW": {"condition": f"state == '{alert_state}'", "description": f"{alert_description}"},
                        "MEDIUM": {"condition": f"state == '{alert_state}' for > 5 minutes", "description": f"Persistent: {alert_description.lower()}"},
                        "HIGH": {"condition": f"state == '{alert_state}' for > 30 minutes", "description": f"Long-term: {alert_description.lower()}"}
                    }
                })
            return result
            
        # Numeric sensors - enhanced fallback thresholds
        elif domain == 'sensor':
            try:
                num_value = float(current_value)
                unit = attributes.get('unit_of_measurement', '')
                device_class = attributes.get('device_class', '')
                entity_lower = entity_id.lower()
                
                # Battery percentage - only generate if clearly a battery sensor
                if (device_class == 'battery' or 'battery_level' in entity_lower) and 0 <= num_value <= 100:
                    result.update({
                        "entity_type": "battery_percent",
                        "thresholds": {
                            "LOW": {"value": 30, "condition": "< 30%", "description": "Battery getting low"},
                            "MEDIUM": {"value": 20, "condition": "< 20%", "description": "Battery low"},
                            "HIGH": {"value": 10, "condition": "< 10%", "description": "Battery critical"}
                        }
                    })
                
                # Temperature sensors (°C)
                elif (device_class == 'temperature' or 'temperature' in entity_lower) and unit in ['°C', 'C']:
                    if 5 <= num_value <= 40:  # Reasonable indoor range
                        result.update({
                            "entity_type": "temperature_indoor",
                            "thresholds": {
                                "LOW": {"value": 15, "condition": "< 15°C", "description": "Temperature too cold"},
                                "MEDIUM": {"value": 10, "condition": "< 10°C", "description": "Temperature very cold"},
                                "HIGH": {"value": 5, "condition": "< 5°C", "description": "Temperature critically cold"}
                            }
                        })
                
                # Heart rate sensors (BPM)
                elif any(keyword in entity_lower for keyword in ['heart_rate', 'pulse', 'bpm']) and 30 <= num_value <= 200:
                    result.update({
                        "entity_type": "heart_rate",
                        "thresholds": {
                            "LOW": {"value": 50, "condition": "< 50 BPM", "description": "Heart rate low"},
                            "MEDIUM": {"value": 40, "condition": "< 40 BPM", "description": "Heart rate very low"},
                            "HIGH": {"value": 35, "condition": "< 35 BPM", "description": "Heart rate critically low"}
                        }
                    })
                
                # CPU/Memory usage (percentage)
                elif any(keyword in entity_lower for keyword in ['cpu', 'memory', 'disk']) and 0 <= num_value <= 100:
                    result.update({
                        "entity_type": "system_usage",
                        "thresholds": {
                            "LOW": {"value": 70, "condition": "> 70%", "description": "High system usage"},
                            "MEDIUM": {"value": 85, "condition": "> 85%", "description": "Very high system usage"},
                            "HIGH": {"value": 95, "condition": "> 95%", "description": "Critical system usage"}
                        }
                    })
                
                # Signal strength (negative dBm or positive %)
                elif any(keyword in entity_lower for keyword in ['rssi', 'signal', 'linkquality']):
                    if unit == 'dBm' and -100 <= num_value <= 0:
                        result.update({
                            "entity_type": "signal_dbm",
                            "thresholds": {
                                "LOW": {"value": -70, "condition": "< -70 dBm", "description": "Weak signal"},
                                "MEDIUM": {"value": -80, "condition": "< -80 dBm", "description": "Very weak signal"},
                                "HIGH": {"value": -90, "condition": "< -90 dBm", "description": "Signal critical"}
                            }
                        })
                        
            except (ValueError, TypeError):
                # Non-numeric sensor - check for update sensors
                if 'update' in entity_lower or device_class == 'update':
                    result.update({
                        "entity_type": "update_status",
                        "thresholds": {
                            "LOW": {"condition": "state != 'up-to-date'", "description": "Update available"},
                            "MEDIUM": {"condition": "state == 'pending' for > 1 day", "description": "Update pending for a while"},
                            "HIGH": {"condition": "state == 'pending' for > 7 days", "description": "Update overdue"}
                        }
                    })
        
        # Update domain entities
        elif domain == 'update':
            result.update({
                "entity_type": "update_entity",
                "thresholds": {
                    "LOW": {"condition": "state == 'on'", "description": "Update available"},
                    "MEDIUM": {"condition": "has_new_release for > 3 days", "description": "Update available for several days"},
                    "HIGH": {"condition": "has_new_release for > 14 days", "description": "Update overdue - security risk"}
                }
            })
                
    except Exception as e:
        _LOGGER.warning(f"Error generating auto-thresholds for {entity_id}: {e}")
    
    return result

# Alert Severity Levels for user notification thresholds (moved definition)
ALERT_SEVERITY_LEVELS = {
    "MEDIUM": {
        "value": 1,
        "description": "Medium priority alert - normal monitoring",
        "color": "#FFA500",  # Orange
        "icon": "mdi:alert-circle-outline"
    },
    "SEVERE": {
        "value": 2, 
        "description": "Severe alert - requires attention",
        "color": "#FF6B6B",  # Red
        "icon": "mdi:alert"
    },
    "CRITICAL": {
        "value": 3,
        "description": "Critical alert - immediate action required", 
        "color": "#DC143C",  # Dark Red
        "icon": "mdi:alert-octagon"
    }
}

# Default alert thresholds for different entity domains
DEFAULT_ALERT_THRESHOLDS = {
    "binary_sensor": {"default": "MEDIUM", "smoke": "CRITICAL", "gas": "CRITICAL", "motion": "MEDIUM"},
    "sensor": {"default": "MEDIUM", "battery": "SEVERE", "temperature": "MEDIUM", "humidity": "MEDIUM"},
    "alarm_control_panel": {"default": "CRITICAL"},
    "device_tracker": {"default": "MEDIUM"},
    "camera": {"default": "SEVERE"},
    "lock": {"default": "CRITICAL"},
    "climate": {"default": "SEVERE"},
    "switch": {"default": "MEDIUM"},
    "light": {"default": "MEDIUM"},
    "cover": {"default": "MEDIUM"}
}

# Entity Enhancement Detection Patterns
ENHANCEMENT_PATTERNS = {
    "vision": {
        "domains": ["camera"],
        "attributes": ["entity_picture", "stream_source", "snapshot_url"],
        "services": ["openai_conversation", "google_generative_ai_conversation", "frigate"],
        "description": "AI vision analysis for camera feeds",
        "output_type": "description_sensor"
    },
    "audio": {
        "domains": ["media_player"],
        "attributes": ["media_title", "media_artist", "source", "sound_mode"],
        "services": ["shazam", "whisper", "spotify"],
        "description": "Audio content analysis and recognition",
        "output_type": "audio_analysis_sensor"
    },
    "analytics": {
        "domains": ["sensor"],
        "name_patterns": ["power_", "energy_", "consumption_", "usage_", "cost_"],
        "services": ["forecast", "statistics", "trend_analysis"],
        "description": "Advanced analytics and predictions",
        "output_type": "analytics_sensor"
    },
    "weather": {
        "domains": ["weather"],
        "attributes": ["forecast", "temperature", "humidity"],
        "services": ["openweathermap", "met", "weather_analysis"],
        "description": "Enhanced weather insights and forecasting",
        "output_type": "weather_enhanced"
    }
}

def _get_entity_alert_threshold(entity_id: str, domain: str, hass: HomeAssistant = None) -> dict:
    """Get the alert threshold for an entity (user customizable)."""
    
    # Try to load user-customized threshold from storage
    if hass:
        try:
            storage_data = hass.data.get("hass_ai_alert_thresholds", {})
            if entity_id in storage_data:
                return storage_data[entity_id]
        except Exception:
            pass
    
    # Use default threshold based on domain and entity type
    domain_thresholds = DEFAULT_ALERT_THRESHOLDS.get(domain, {"default": "MEDIUM"})
    
    # Check for specific entity types
    entity_name = entity_id.lower()
    for entity_type, threshold in domain_thresholds.items():
        if entity_type != "default" and entity_type in entity_name:
            return {
                "level": threshold,
                "customized": False,
                "description": ALERT_SEVERITY_LEVELS[threshold]["description"],
                "color": ALERT_SEVERITY_LEVELS[threshold]["color"],
                "icon": ALERT_SEVERITY_LEVELS[threshold]["icon"]
            }
    
    # Use default for domain
    default_threshold = domain_thresholds.get("default", "MEDIUM")
    return {
        "level": default_threshold,
        "customized": False,
        "description": ALERT_SEVERITY_LEVELS[default_threshold]["description"],
        "color": ALERT_SEVERITY_LEVELS[default_threshold]["color"],
        "icon": ALERT_SEVERITY_LEVELS[default_threshold]["icon"]
    }

def _save_entity_alert_threshold(entity_id: str, threshold_level: str, hass: HomeAssistant) -> bool:
    """Save user-customized alert threshold for an entity."""
    
    if threshold_level not in ALERT_SEVERITY_LEVELS:
        return False
    
    try:
        # Initialize storage if not exists
        if "hass_ai_alert_thresholds" not in hass.data:
            hass.data["hass_ai_alert_thresholds"] = {}
        
        hass.data["hass_ai_alert_thresholds"][entity_id] = {
            "level": threshold_level,
            "customized": True,
            "description": ALERT_SEVERITY_LEVELS[threshold_level]["description"],
            "color": ALERT_SEVERITY_LEVELS[threshold_level]["color"],
            "icon": ALERT_SEVERITY_LEVELS[threshold_level]["icon"],
            "updated_at": datetime.now().isoformat()
        }
        
        return True
    except Exception as e:
        _LOGGER.error(f"Failed to save alert threshold for {entity_id}: {e}")
        return False

def _analyze_entities_for_enhancement(states: list[State], language: str) -> list[dict]:
    """Analyze entities for enhancement opportunities without using AI tokens."""
    
    results = []
    is_italian = language.startswith('it')
    
    for state in states:
        entity_id = state.entity_id
        domain = entity_id.split('.')[0]
        
        # Check each enhancement pattern
        opportunities = []
        for enhancement_type, pattern in ENHANCEMENT_PATTERNS.items():
            if _entity_matches_enhancement_pattern(state, pattern):
                confidence = _calculate_enhancement_confidence(state, pattern)
                
                description = pattern["description"]
                if is_italian:
                    description = _translate_enhancement_description(description)
                
                opportunity = {
                    "enhancement_type": enhancement_type,
                    "description": description,
                    "confidence": confidence,
                    "services": pattern.get("services", []),
                    "output_type": pattern["output_type"]
                }
                opportunities.append(opportunity)
        
        # Create result for this entity
        if opportunities:
            # Use the opportunity with highest confidence
            best_opportunity = max(opportunities, key=lambda x: x['confidence'])
            
            result = {
                "entity_id": entity_id,
                "rating": min(5, int(best_opportunity['confidence'] * 5)),  # Convert to 0-5 scale
                "reason": f"Enhancement opportunity: {best_opportunity['description']}",
                "category": "ENHANCED",
                "management_type": "SERVICE",
                "enhancement_type": best_opportunity['enhancement_type'],
                "confidence": best_opportunity['confidence'],
                "services": best_opportunity['services'],
                "output_type": best_opportunity['output_type']
            }
        else:
            # No enhancement opportunities found
            result = {
                "entity_id": entity_id,
                "rating": 0,
                "reason": "No enhancement opportunities detected",
                "category": "DATA",
                "management_type": "USER"
            }
        
        results.append(result)
    
    _LOGGER.info(f"Enhancement analysis complete: {len([r for r in results if r['rating'] > 0])} opportunities found from {len(states)} entities")
    return results

def _entity_matches_enhancement_pattern(state: State, pattern: dict) -> bool:
    """Check if an entity matches an enhancement pattern."""
    entity_id = state.entity_id
    domain = entity_id.split('.')[0]
    
    # Check domain match
    if "domains" in pattern and domain not in pattern["domains"]:
        return False
    
    # Check name patterns
    if "name_patterns" in pattern:
        entity_name = entity_id.lower()
        if not any(pattern_name in entity_name for pattern_name in pattern["name_patterns"]):
            return False
    
    # Check required attributes
    if "attributes" in pattern:
        entity_attrs = state.attributes
        if not any(attr in entity_attrs for attr in pattern["attributes"]):
            return False
    
    return True

def _calculate_enhancement_confidence(state: State, pattern: dict) -> float:
    """Calculate confidence score for enhancement opportunity."""
    confidence = 0.5  # Base confidence
    
    # Increase confidence based on available attributes
    if "attributes" in pattern:
        entity_attrs = state.attributes
        matching_attrs = sum(1 for attr in pattern["attributes"] if attr in entity_attrs)
        confidence += (matching_attrs / len(pattern["attributes"])) * 0.3
    
    # Factor in entity state availability
    if state.state not in [None, "unavailable", "unknown"]:
        confidence += 0.2
    
    return min(confidence, 1.0)

def _translate_enhancement_description(description: str) -> str:
    """Translate enhancement descriptions to Italian."""
    translations = {
        "AI vision analysis for camera feeds": "Analisi visiva AI per flussi telecamera",
        "Audio content analysis and recognition": "Analisi e riconoscimento contenuto audio",
        "Advanced analytics and predictions": "Analisi avanzate e previsioni",
        "Enhanced weather insights and forecasting": "Approfondimenti meteo avanzati e previsioni"
    }
    return translations.get(description, description)

async def get_entities_importance_batched(
    hass: HomeAssistant, 
    states: list[State],
    batch_size: int = 10,  # Process 10 entities at a time
    ai_provider: str = "OpenAI",
    api_key: str = None,
    connection = None,
    msg_id: str = None,
    conversation_agent: str = None,
    language: str = "en",  # Add language parameter
    analysis_type: str = "importance",  # Add analysis type parameter
    cancellation_check: callable = None  # Function to check if operation is cancelled
) -> list[dict]:
    """Calculate the importance of multiple entities using external AI providers in batches with dynamic size reduction.
    
    analysis_type can be: 'importance', 'health', 'enhanced'
    """
    
    if not states:
        _LOGGER.warning("No entities provided for analysis")
        return []
    
    _LOGGER.info(f"Starting AI analysis with provider: {ai_provider}, analysis type: {analysis_type}, API key present: {bool(api_key)}")
    
    # Enhanced analysis doesn't require AI API
    if analysis_type == "enhanced":
        return _analyze_entities_for_enhancement(states, language)
    
    # Local agent doesn't need API key for other analysis types
    if ai_provider != AI_PROVIDER_LOCAL and not api_key and analysis_type in ["importance", "alerts"]:
        _LOGGER.error(f"No API key provided for {ai_provider}! Using fallback classification.")
        # Send debug info about missing API key
        if connection and msg_id:
            debug_data = {
                "aiProvider": ai_provider,
                "currentBatch": 0,
                "lastPrompt": "ERRORE: Nessuna chiave API configurata!",
                "lastResponse": f"Fallback alla classificazione domain-based perché non è stata trovata la chiave API per {ai_provider}"
            }
            connection.send_message(websocket_api.event_message(msg_id, {
                "type": "debug_info", 
                "data": debug_data
            }))
        # Use fallback for all entities if no API key
        all_results = []
        for state in states:
            all_results.append(_create_fallback_result(state.entity_id, 0, "no_api_key", state))
        return all_results
    
    all_results = []
    current_batch_size = batch_size
    remaining_states = states.copy()
    overall_batch_num = 0
    token_limit_retries = 0
    max_retries = 3
    use_compact_mode = False  # Start with full mode
    
    # Token usage tracking
    total_tokens_used = 0
    total_prompt_chars = 0
    total_response_chars = 0
    
    _LOGGER.info(f"🚀 Starting batch processing with initial batch size: {current_batch_size}")
    
    hass_id = id(hass)
    while remaining_states:
        # STOP: Check if operation was cancelled using the provided callback
        if cancellation_check and cancellation_check():
            _LOGGER.info("🛑 Batch analysis STOPPED by user request (immediate)")
            break
        overall_batch_num += 1
        
        # Take entities for current batch
        batch_states = remaining_states[:current_batch_size]
        
        _LOGGER.info(f"📦 Processing batch {overall_batch_num} with {len(batch_states)} entities (batch size: {current_batch_size}, retry: {token_limit_retries}, compact: {use_compact_mode})")
        
        # Send batch info to frontend
        if connection and msg_id:
            connection.send_message(websocket_api.event_message(msg_id, {
                "type": "batch_info",
                "data": {
                    "batch_number": overall_batch_num,
                    "batch_size": current_batch_size,
                    "entities_in_batch": len(batch_states),
                    "remaining_entities": len(remaining_states) - len(batch_states),
                    "retry_attempt": token_limit_retries,
                    "compact_mode": use_compact_mode,
                    "total_entities": len(states),
                    "processed_entities": len(all_results)
                }
            }))
        
        success, batch_stats = await _process_single_batch(
            hass, batch_states, overall_batch_num, ai_provider, 
            connection, msg_id, conversation_agent, all_results, language, use_compact_mode, analysis_type, cancellation_check
        )
        
        # Accumulate token statistics
        total_tokens_used += batch_stats.get("total_tokens", 0)
        total_prompt_chars += batch_stats.get("prompt_chars", 0)
        total_response_chars += batch_stats.get("response_chars", 0)
        
        if success:
            # Batch successful - remove processed entities and reset retry counter
            remaining_states = remaining_states[current_batch_size:]
            token_limit_retries = 0
            use_compact_mode = False  # Reset to full mode on success
            _LOGGER.info(f"✅ Batch {overall_batch_num} completed successfully")
            
        else:
            # Token limit exceeded - try different strategies
            token_limit_retries += 1
            
            # First try: enable compact mode if not already enabled
            if not use_compact_mode and token_limit_retries == 1:
                use_compact_mode = True
                _LOGGER.warning(f"🔄 Token limit in batch {overall_batch_num}, trying compact mode (retry {token_limit_retries}/{max_retries})")
                
                # Send compact mode info to frontend
                if connection and msg_id:
                    connection.send_message(websocket_api.event_message(msg_id, {
                        "type": "batch_compact_mode",
                        "data": {
                            "batch": overall_batch_num,
                            "retry_attempt": token_limit_retries,
                            "reason": "Attivazione modalità compatta per gestire limite token",
                            "message": _get_localized_message('batch_reduction', language, 
                                                            retry_attempt=token_limit_retries)
                        }
                    }))
                
                # Don't increment overall_batch_num since we're retrying the same batch
                overall_batch_num -= 1
                continue
            
            if token_limit_retries > max_retries:
                # Max retries exceeded, try with minimum batch size one more time
                if current_batch_size > MIN_BATCH_SIZE:
                    _LOGGER.warning(f"🔄 Max retries exceeded, trying with minimum batch size {MIN_BATCH_SIZE}")
                    current_batch_size = MIN_BATCH_SIZE
                    use_compact_mode = True  # Force compact mode
                    token_limit_retries = 1  # Reset for one final attempt
                else:
                    # Even minimum batch size failed, use fallback for remaining entities
                    _LOGGER.error(f"🛑 Even minimum batch size {MIN_BATCH_SIZE} failed after {max_retries} retries")
                    _LOGGER.info(f"📋 Using fallback classification for remaining {len(remaining_states)} entities")
                    
                    # Send fallback results to frontend immediately
                    for state in remaining_states:
                        fallback_result = _create_fallback_result(state.entity_id, overall_batch_num, "token_limit_exceeded", state)
                        all_results.append(fallback_result)
                        
                        # Send each fallback result to frontend
                        if connection and msg_id:
                            connection.send_message(websocket_api.event_message(msg_id, {
                                "type": "entity_result",
                                "result": fallback_result
                            }))
                    break
            else:
                new_batch_size = max(MIN_BATCH_SIZE, int(current_batch_size * BATCH_REDUCTION_FACTOR))
                
                _LOGGER.warning(f"⚠️ Token limit in batch {overall_batch_num}, reducing batch size from {current_batch_size} to {new_batch_size} (retry {token_limit_retries}/{max_retries})")
                
                # Send reduction info to frontend
                if connection and msg_id:
                    connection.send_message(websocket_api.event_message(msg_id, {
                        "type": "batch_size_reduced",
                        "data": {
                            "old_size": current_batch_size,
                            "new_size": new_batch_size,
                            "retry_attempt": token_limit_retries,
                            "reason": "Token limit exceeded",
                            "message": _get_localized_message('batch_reduction', language, 
                                                            old_size=current_batch_size, 
                                                            new_size=new_batch_size, 
                                                            retry_attempt=token_limit_retries)
                        }
                    }))
                
                current_batch_size = new_batch_size
                
                # Don't increment overall_batch_num since we're retrying the same batch
                overall_batch_num -= 1  # Counteract the increment that will happen at loop start

    # Ensure all entities have a result (fallback for any missing)
    processed_entity_ids = {res["entity_id"] for res in all_results}
    for state in states:
        if state.entity_id not in processed_entity_ids:
            all_results.append(_create_fallback_result(state.entity_id, 0, "missing_result", state))

    # Send scan completion message to frontend with token statistics
    if connection and msg_id:
        connection.send_message(websocket_api.event_message(msg_id, {
            "type": "scan_complete",
            "data": {
                "total_entities": len(all_results),
                "message": f"Scansione completata! Analizzate {len(all_results)} entità",
                "token_stats": {
                    "total_tokens": total_tokens_used,
                    "prompt_chars": total_prompt_chars,
                    "response_chars": total_response_chars,
                    "average_tokens_per_entity": round(total_tokens_used / len(all_results), 1) if all_results else 0
                }
            }
        }))

    _LOGGER.info(f"🏁 Completed analysis of {len(states)} entities, got {len(all_results)} results")
    _LOGGER.info(f"📊 Token usage: {total_tokens_used} total tokens ({total_prompt_chars} prompt chars, {total_response_chars} response chars)")
    _LOGGER.info(f"📈 Average: {round(total_tokens_used / len(all_results), 1) if all_results else 0} tokens per entity")
    return all_results
        
async def _process_single_batch(
    hass: HomeAssistant,
    batch_states: list[State], 
    batch_num: int,
    ai_provider: str,
    connection,
    msg_id: str,
    conversation_agent: str,
    all_results: list,
    language: str = "en",  # Add language parameter
    use_compact_prompt: bool = False,  # Add compact mode flag
    analysis_type: str = "importance",  # Add analysis type parameter
    cancellation_check: callable = None  # Function to check if operation is cancelled
) -> tuple[bool, dict]:
    """Process a single batch and return success status and token statistics."""
    
    # Check for cancellation before processing
    if cancellation_check and cancellation_check():
        _LOGGER.info(f"Batch {batch_num} cancelled before processing")
        return False, {"prompt_tokens": 0, "response_tokens": 0, "total_tokens": 0}
    
    # Create detailed entity information for AI analysis
    entity_details = []
    
    # Create minimal entity information for AI analysis
    for state in batch_states:
        # Just the basics: entity_id, domain, state, name
        name = state.attributes.get('friendly_name', state.entity_id.split('.')[-1])
        entity_description = f"{state.entity_id} ({state.domain}, {state.state}, {name[:20]})"
        entity_details.append(entity_description)
    
    # Add delay to make AI analysis visible
    await asyncio.sleep(1.5 if use_compact_prompt else 2.5)
    
    # Create localized prompt based on user's language and mode
    prompt = _create_localized_prompt(batch_states, entity_details, language, compact_mode=use_compact_prompt, analysis_type=analysis_type)
    
    # Log prompt size for debugging
    prompt_size = len(prompt)
    _LOGGER.info(f"📝 Batch {batch_num} prompt size: {prompt_size} chars ({'compact' if use_compact_prompt else 'full'} mode)")

    try:
        # Send simple progress info to frontend instead of full debug
        if connection and msg_id:
            connection.send_message(websocket_api.event_message(msg_id, {
                "type": "scan_progress", 
                "data": {
                    "message": _get_localized_message('batch_request', language, batch_num=batch_num, entities_count=len(batch_states)) + (" (modalità compatta)" if use_compact_prompt else ""),
                    "batch_number": batch_num,
                    "entities_count": len(batch_states),
                    "compact_mode": use_compact_prompt,
                    "prompt_size": prompt_size
                }
            }))
        
        # Use Local Agent only
        if ai_provider == AI_PROVIDER_LOCAL:
            response_text = await _query_local_agent(hass, prompt, conversation_agent)
            _LOGGER.debug(f"Local Agent response for batch {batch_num}: {response_text[:200]}...")
            
            # Send simple response confirmation
            if connection and msg_id:
                connection.send_message(websocket_api.event_message(msg_id, {
                    "type": "scan_progress",
                    "data": {
                        "message": _get_localized_message('batch_response', language, batch_num=batch_num, entities_count=len(batch_states)),
                        "batch_number": batch_num,
                        "entities_count": len(batch_states),
                        "response_size": len(response_text)
                    }
                }))
            
            # Check for token limit exceeded
            if _check_token_limit_exceeded(response_text):
                _LOGGER.error(f"🚨 Token limit exceeded in batch {batch_num} ({'compact' if use_compact_prompt else 'full'} mode)")
                
                # Send token limit error to frontend
                if connection and msg_id:
                    connection.send_message(websocket_api.event_message(msg_id, {
                        "type": "token_limit_exceeded",
                        "data": {
                            "batch": batch_num,
                            "compact_mode": use_compact_prompt,
                            "title": _get_localized_message('token_limit_title', language),
                            "message": _get_localized_message('token_limit_message', language, batch=batch_num),
                            "response": response_text[:500]  # Show only first 500 chars
                        }
                    }))
                
                # Return minimal stats even on token limit
                prompt_tokens = _estimate_tokens(prompt)
                batch_stats = {
                    "prompt_tokens": prompt_tokens,
                    "response_tokens": _estimate_tokens(response_text),
                    "total_tokens": prompt_tokens + _estimate_tokens(response_text)
                }
                
                return False, batch_stats  # Signal token limit exceeded
                
        else:
            _LOGGER.error(f"AI provider {ai_provider} not supported. Only Local Agent is available.")
            # Send simple error message to frontend
            if connection and msg_id:
                connection.send_message(websocket_api.event_message(msg_id, {
                    "type": "scan_progress",
                    "data": {
                        "message": f"❌ Provider {ai_provider} non supportato. Uso fallback per batch {batch_num}",
                        "batch_number": batch_num,
                        "entities_count": len(batch_states)
                    }
                }))
            # Use fallback for all entities in this batch
            for state in batch_states:
                fallback_result = _create_fallback_result(state.entity_id, batch_num, "unsupported_provider", state)
                all_results.append(fallback_result)
                
                # Send fallback result to frontend
                if connection and msg_id:
                    connection.send_message(websocket_api.event_message(msg_id, {
                        "type": "entity_result",
                        "result": fallback_result
                    }))
            return True  # Continue processing

        # Clean response text (remove markdown formatting if present)
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # Parse JSON response
        parsed_response = json.loads(response_text)

        if isinstance(parsed_response, list):
            for item in parsed_response:
                if isinstance(item, dict) and all(key in item for key in ["entity_id", "rating", "reason"]):
                    # Validate rating is within bounds
                    rating = int(item["rating"])
                    if 0 <= rating <= 5:
                        # Get category - can be string or array
                        category = item.get("category", ["DATA"])  # Default to DATA instead of UNKNOWN
                        if isinstance(category, str):
                            # Convert single category to array
                            category = [category]
                        elif not isinstance(category, list):
                            category = ["DATA"]  # Default to DATA instead of UNKNOWN
                        
                        # Validate all categories (now includes SERVICE)
                        valid_categories = ["DATA", "CONTROL", "ALERTS", "SERVICE"]
                        category = [cat for cat in category if cat in valid_categories]
                        if not category:
                            category = ["DATA"]
                        
                        # Get management_type, default to 'user' if not provided
                        management_type = item.get("management_type", "user")
                        if management_type.lower() not in ["user", "service"]:
                            management_type = "user"
                        else:
                            management_type = management_type.lower()
                            
                        result = {
                            "entity_id": item["entity_id"],
                            "overall_weight": rating,
                            "overall_reason": item["reason"],
                            "category": category,
                            "management_type": management_type,
                            "analysis_method": "ai_conversation",
                            "batch_number": batch_num,
                        }
                        
                        # Generate auto-thresholds for relevant entities (more inclusive approach)
                        state = next((s for s in batch_states if s.entity_id == item["entity_id"]), None)
                        if state and hass:
                            # Check if entity warrants automatic threshold generation
                            should_generate_thresholds = (
                                'ALERTS' in category or  # Entities categorized as ALERTS
                                'battery' in item["entity_id"].lower() or  # Battery entities
                                state.domain in ['binary_sensor', 'update'] or  # Binary sensors and update entities
                                (state.domain == 'sensor' and state.attributes.get('device_class') in ['battery', 'temperature', 'humidity', 'signal_strength']) or  # Specific sensor types
                                any(keyword in item["entity_id"].lower() for keyword in ['temperature', 'humidity', 'cpu', 'memory', 'disk', 'heart_rate', 'signal'])  # Keyword matching
                            )
                            
                            if should_generate_thresholds:
                                auto_thresholds = await _generate_auto_thresholds(hass, item["entity_id"], state)
                                if auto_thresholds.get("thresholds"):
                                    result["auto_thresholds"] = auto_thresholds
                                    _LOGGER.debug(f"Generated auto-thresholds for {item['entity_id']}: {auto_thresholds['entity_type']}")
                        
                        
                        all_results.append(result)
                        
                        # Send result to frontend immediately
                        if connection and msg_id:
                            connection.send_message(websocket_api.event_message(msg_id, {
                                "type": "entity_result",
                                "result": result
                            }))
                    else:
                        _LOGGER.warning(f"Invalid rating {rating} for entity {item['entity_id']}, using fallback")
                        # Find the corresponding state
                        entity_state = next((s for s in batch_states if s.entity_id == item["entity_id"]), None)
                        fallback_result = _create_fallback_result(item["entity_id"], batch_num, "invalid_rating", entity_state)
                        all_results.append(fallback_result)
                        
                        # Send fallback result to frontend
                        if connection and msg_id:
                            connection.send_message(websocket_api.event_message(msg_id, {
                                "type": "entity_result",
                                "result": fallback_result
                            }))
                else:
                    _LOGGER.warning(f"Malformed AI response item: {item}")
        else:
            _LOGGER.warning(f"AI response is not a list, using fallback for batch {batch_num}")
            # Use fallback for all entities in this batch
            for state in batch_states:
                fallback_result = _create_fallback_result(state.entity_id, batch_num, "invalid_response", state)
                all_results.append(fallback_result)
                
                # Send fallback result to frontend
                if connection and msg_id:
                    connection.send_message(websocket_api.event_message(msg_id, {
                        "type": "entity_result",
                        "result": fallback_result
                    }))
        
        # Return minimal stats for fallback cases
        prompt_tokens = _estimate_tokens(prompt)
        batch_stats = {
            "prompt_tokens": prompt_tokens,
            "response_tokens": _estimate_tokens(response_text) if 'response_text' in locals() else 0,
            "total_tokens": prompt_tokens + (_estimate_tokens(response_text) if 'response_text' in locals() else 0)
        }
        
        return True, batch_stats  # Fallback success with stats

    except json.JSONDecodeError as e:
        _LOGGER.warning(f"AI response is not valid JSON for batch {batch_num} - Raw response: {response_text} - Error: {e}")
        _LOGGER.info(f"Falling back to domain-based classification for batch {batch_num}")
        # Use fallback for all entities in this batch
        for state in batch_states:
            fallback_result = _create_fallback_result(state.entity_id, batch_num, "json_decode_error", state)
            all_results.append(fallback_result)
            
            # Send fallback result to frontend
            if connection and msg_id:
                connection.send_message(websocket_api.event_message(msg_id, {
                    "type": "entity_result",
                    "result": fallback_result
                }))
        
        # Return minimal stats for JSON decode error
        prompt_tokens = _estimate_tokens(prompt)
        batch_stats = {
            "prompt_tokens": prompt_tokens,
            "response_tokens": _estimate_tokens(response_text) if 'response_text' in locals() else 0,
            "total_tokens": prompt_tokens + (_estimate_tokens(response_text) if 'response_text' in locals() else 0)
        }
        
        return True, batch_stats  # Fallback success with stats
    except Exception as e:
        _LOGGER.error(f"Error querying AI for batch {batch_num}: {e}")
        _LOGGER.info(f"Falling back to domain-based classification for batch {batch_num}")
        # Use fallback for all entities in this batch
        for state in batch_states:
            fallback_result = _create_fallback_result(state.entity_id, batch_num, "processing_error", state)
            all_results.append(fallback_result)
            
            # Send fallback result to frontend
            if connection and msg_id:
                connection.send_message(websocket_api.event_message(msg_id, {
                    "type": "entity_result",
                    "result": fallback_result
                }))

    # Calculate token statistics for this batch
    prompt_tokens = _estimate_tokens(prompt)
    response_tokens = _estimate_tokens(response_text) if 'response_text' in locals() else 0
    
    batch_stats = {
        "prompt_tokens": prompt_tokens,
        "response_tokens": response_tokens,
        "total_tokens": prompt_tokens + response_tokens
    }
    
    return True, batch_stats  # Success with statistics


def _check_token_limit_exceeded(response_text: str) -> bool:
    """Check if the response indicates a token limit was exceeded."""
    if not response_text:
        return False
    
    response_lower = response_text.lower()
    for keyword in MAX_TOKEN_ERROR_KEYWORDS:
        if keyword.lower() in response_lower:
            _LOGGER.warning(f"🚨 Token limit keyword detected: '{keyword}' in response")
            return True
    
    return False


def _create_fallback_result(entity_id: str, batch_num: int, reason: str = "domain_fallback", state: State = None) -> dict:
    """Create a fallback result when AI analysis fails."""
    domain = entity_id.split(".")[0]
    
    # Use domain-based importance mapping
    importance = ENTITY_IMPORTANCE_MAP.get(domain, 2)
    
    # Determine management type based on domain
    user_managed_domains = {"light", "switch", "climate", "cover", "fan", "lock", "alarm_control_panel", "input_boolean", "input_number", "input_select", "input_text", "media_player"}
    service_managed_domains = {"sensor", "binary_sensor", "weather", "sun", "system_log", "automation", "script", "camera", "update", "device_tracker", "person", "zone"}
    
    if domain in user_managed_domains:
        management_type = "USER"
    elif domain in service_managed_domains:
        management_type = "SERVICE"
    else:
        management_type = "USER"  # Default to user for unknown domains
    
    # Use auto-categorization if state is available, otherwise fallback to domain-based
    if state:
        categories, management_type = _auto_categorize_entity(state)
        category = categories if categories else ["DATA"]  # Use all categories, not just the first one
    else:
        # Fallback domain-based categorization: GENERIC, sempre almeno DATA
        entity_lower = entity_id.lower()
        category = ["DATA"]
        management_type = "USER"
        # Se ha pattern di controllo
        if any(keyword in entity_lower for keyword in ["switch", "control", "toggle", "button", "command", "conversation"]):
            category.append("CONTROL")
        # Se ha pattern di alert
        if any(keyword in entity_lower for keyword in ["battery", "unavailable", "offline", "signal", "error", "connection", "alarm", "alert", "update", "problem", "warning"]):
            category.append("ALERTS")
        # Se ha pattern di servizio o è conversation/update/camera
        if any(keyword in entity_lower for keyword in ["service", "api", "conversation", "update", "camera"]):
            category.append("SERVICE")
        # Rimuovi duplicati
        category = list(dict.fromkeys(category))
    
    reason_map = {
        0: "Entity marked as ignore - likely diagnostic or unnecessary",
        1: "Very low importance - rarely used in automations",
        2: "Low importance - domain suggests limited automation value",
        3: "Medium importance - commonly useful for automations",
        4: "High importance - frequently used in smart home automations",
        5: "Critical importance - essential for security/safety automations"
    }
    
    if reason == "token_limit_exceeded":
        # Create more descriptive fallback reasons based on domain and characteristics
        domain = entity_id.split('.')[0] if '.' in entity_id else ''
        if domain == 'weather':
            fallback_reason = f"Weather sensor providing {reason_map[importance].lower()} environmental data for home automation"
        elif domain == 'sensor' and 'battery' in entity_id.lower():
            fallback_reason = f"Battery level sensor with {reason_map[importance].lower()} for device monitoring and maintenance alerts"
        elif domain == 'sensor':
            fallback_reason = f"Sensor providing {reason_map[importance].lower()} data for home monitoring and automation triggers"
        elif domain in ['light', 'switch']:
            fallback_reason = f"Control device with {reason_map[importance].lower()} for home automation and comfort"
        else:
            fallback_reason = f"{reason_map[importance]} - domain-based evaluation due to token limit"
        analysis_method = "domain_fallback_token_limit"
    else:
        # Create more descriptive reasons for auto-categorization with enhanced patterns
        domain = entity_id.split('.')[0] if '.' in entity_id else ''
        entity_lower = entity_id.lower()
        
        if domain == 'conversation':
            fallback_reason = f"Voice assistant control interface with {reason_map[importance].lower()} for smart home voice automation and interaction"
        elif any(keyword in entity_lower for keyword in ['meteo', 'weather', 'forecast']):
            fallback_reason = f"Weather information sensor providing {reason_map[importance].lower()} meteorological data for climate-based automations"
        elif domain == 'weather':
            fallback_reason = f"Weather sensor providing {reason_map[importance].lower()} environmental data for automation decisions"
        elif domain == 'sensor' and 'battery' in entity_lower:
            fallback_reason = f"Battery monitoring sensor with {reason_map[importance].lower()} for preventive maintenance alerts"
        elif domain == 'sensor':
            fallback_reason = f"Data sensor with {reason_map[importance].lower()} utility for home automation and monitoring"
        elif domain in ['light', 'switch', 'climate']:
            fallback_reason = f"Control entity with {reason_map[importance].lower()} for smart home operations"
        else:
            fallback_reason = f"{reason_map[importance]} - basic domain-based evaluation"
        analysis_method = "domain_based_categorization"
    
    result = {
        "entity_id": entity_id,
        "overall_weight": importance,
        "overall_reason": fallback_reason,
        "category": category,
        "management_type": management_type,
        "analysis_method": analysis_method,
        "batch_number": batch_num,
    }
    
    # Generate basic auto-thresholds for ALERTS entities in fallback
    if ('ALERTS' in category if isinstance(category, list) else category == 'ALERTS'):
        try:
            # Create basic fallback thresholds without AI assistance
            domain = entity_id.split('.')[0]
            auto_thresholds = {"auto_generated": True, "entity_type": "fallback", "thresholds": {}}
            
            if 'battery' in entity_id.lower():
                auto_thresholds["thresholds"] = {
                    "LOW": {"value": 30, "condition": "< 30%", "description": "Battery getting low"},
                    "MEDIUM": {"value": 20, "condition": "< 20%", "description": "Battery low"},
                    "HIGH": {"value": 10, "condition": "< 10%", "description": "Battery critical"}
                }
            elif domain == 'update' or 'update' in entity_id.lower():
                auto_thresholds["thresholds"] = {
                    "LOW": {"condition": "state == 'on'", "description": "Update available"},
                    "MEDIUM": {"condition": "update available > 3 days", "description": "Update pending"},
                    "HIGH": {"condition": "update available > 14 days", "description": "Update overdue"}
                }
            elif domain == 'binary_sensor':
                auto_thresholds["thresholds"] = {
                    "LOW": {"condition": "state == 'on'", "description": "Alert condition detected"},
                    "MEDIUM": {"condition": "state == 'on' for > 5 min", "description": "Persistent alert"},
                    "HIGH": {"condition": "state == 'on' for > 30 min", "description": "Long-term issue"}
                }
            elif 'temperature' in entity_id.lower():
                auto_thresholds["thresholds"] = {
                    "LOW": {"value": 15, "condition": "< 15°C", "description": "Temperature too cold"},
                    "MEDIUM": {"value": 10, "condition": "< 10°C", "description": "Temperature very cold"}, 
                    "HIGH": {"value": 5, "condition": "< 5°C", "description": "Temperature critically cold"}
                }
            elif any(keyword in entity_id.lower() for keyword in ['heart_rate', 'pulse']):
                auto_thresholds["thresholds"] = {
                    "LOW": {"value": 50, "condition": "< 50 BPM", "description": "Heart rate low"},
                    "MEDIUM": {"value": 40, "condition": "< 40 BPM", "description": "Heart rate very low"},
                    "HIGH": {"value": 35, "condition": "< 35 BPM", "description": "Heart rate critically low"}
                }
            
            if auto_thresholds.get("thresholds"):
                result["auto_thresholds"] = auto_thresholds
        except Exception:
            pass  # Skip auto-thresholds if error
    
    return result


async def _query_local_agent(hass: HomeAssistant, prompt: str, conversation_agent: str = None) -> str:
    """Query Home Assistant local conversation agent using HA services."""
    try:
        _LOGGER.info(f"🤖 Querying local conversation agent via HA services...")
        
        # Determine which agent to use
        agent_id = None
        
        if conversation_agent == "auto" or conversation_agent is None:
            # Auto-detect: find first non-default agent
            conversation_agents = []
            for entity_id in hass.states.async_entity_ids("conversation"):
                if entity_id != "conversation.home_assistant":  # Skip default agent
                    conversation_agents.append(entity_id)
                    _LOGGER.info(f"🔍 Found conversation agent: {entity_id}")
            
            agent_id = conversation_agents[0] if conversation_agents else None
            _LOGGER.info(f"🎯 Auto-detected agent: {agent_id}")
            
        elif conversation_agent and conversation_agent != "auto":
            # Use specifically configured agent
            agent_id = conversation_agent
            _LOGGER.info(f"🎯 Using configured agent: {agent_id}")
        
        if agent_id:
            _LOGGER.info(f"✅ Using conversation agent: {agent_id}")
        else:
            _LOGGER.warning(f"⚠️ No custom conversation agents found, using default (may not work well)")
        
        # Use Home Assistant service to process conversation
        _LOGGER.info(f"� Sending conversation via service (prompt length: {len(prompt)} chars)")
        
        service_data = {
            "text": prompt,
            "language": hass.config.language
        }
        
        # Add agent_id if we found a custom agent
        if agent_id:
            service_data["agent_id"] = agent_id
        
        # Call the conversation.process service
        response = await hass.services.async_call(
            "conversation", 
            "process", 
            service_data, 
            blocking=True, 
            return_response=True
        )
        
        _LOGGER.info(f"� Service response: {response}")
        
        # Extract the response text
        if response and "response" in response and "speech" in response["response"]:
            response_text = response["response"]["speech"]["plain"]["speech"]
            _LOGGER.info(f"📄 Extracted response text: {response_text[:200]}...")
            return response_text
        else:
            _LOGGER.error(f"❌ Unexpected service response format: {response}")
            raise Exception(f"Invalid service response format: {response}")
        
    except Exception as e:
        _LOGGER.error(f"❌ Error querying conversation service: {type(e).__name__}: {e}")
        _LOGGER.error(f"🔧 Make sure you have a proper conversation agent configured")
        _LOGGER.error(f"💡 Check Settings > Voice Assistants > Conversation Agent")
        # Return a simple structured response as fallback
        return """[
{"entity_id": "fallback", "rating": 2, "reason": "Servizio conversazione non disponibile - verifica configurazione agente in Impostazioni > Assistenti vocali", "category": ["DATA"], "management_type": "USER"}
]"""


def _extract_room_from_entity(entity_id: str) -> str:
    """Extract room name from entity ID using common patterns."""
    entity_lower = entity_id.lower()
    
    # Common room patterns in Italian and English
    room_patterns = [
        'soggiorno', 'living', 'salotto',
        'cucina', 'kitchen', 
        'camera', 'bedroom', 'letto',
        'bagno', 'bathroom', 'toilet',
        'ingresso', 'entrance', 'entrata',
        'corridoio', 'hallway', 'corridor',
        'studio', 'office', 'ufficio',
        'lavanderia', 'laundry',
        'garage', 'cantina', 'basement',
        'terrazza', 'terrace', 'balcone', 'balcony',
        'giardino', 'garden',
        'taverna', 'mansarda', 'attic'
    ]
    
    for room in room_patterns:
        if room in entity_lower:
            return room
    
    return None


async def find_entity_correlations(hass: HomeAssistant, target_entity: dict, all_entities: list[dict], language: str) -> list[dict]:
    """Find correlations between a target entity and other entities using enhanced smart logic."""
    try:
        target_id = target_entity["entity_id"]
        target_weight = target_entity["ai_weight"]
        target_category = target_entity.get("category", ["DATA"])  # Default to DATA instead of UNKNOWN
        target_domain = target_id.split('.')[0]
        
        # Smart candidate filtering based on target entity type
        candidate_entities = []
        
        # Define smart correlation patterns
        if target_domain == 'switch' or target_domain == 'light':
            # For switches/lights, prioritize presence, motion, time-based entities
            priority_patterns = ['person', 'device_tracker', 'presence', 'motion', 'occupancy', 'binary_sensor', 'sun', 'time']
            room_name = _extract_room_from_entity(target_id)
            
        elif target_domain == 'climate':
            # For climate, prioritize temperature, weather, presence
            priority_patterns = ['temperature', 'weather', 'presence', 'person', 'window', 'door', 'humidity']
            room_name = _extract_room_from_entity(target_id)
            
        elif target_domain == 'cover':
            # For covers, prioritize sun, weather, temperature
            priority_patterns = ['sun', 'weather', 'temperature', 'wind', 'rain', 'brightness', 'illuminance']
            room_name = _extract_room_from_entity(target_id)
            
        elif target_domain == 'media_player':
            # For media, prioritize presence, time
            priority_patterns = ['person', 'presence', 'device_tracker', 'time', 'sun']
            room_name = _extract_room_from_entity(target_id)
            
        elif target_domain == 'alarm_control_panel':
            # For alarms, prioritize presence, doors, windows
            priority_patterns = ['person', 'device_tracker', 'door', 'window', 'motion', 'presence']
            room_name = None
            
        else:
            # Default patterns for other entities
            priority_patterns = ['person', 'presence', 'motion', 'time', 'sun']
            room_name = _extract_room_from_entity(target_id)
        
        # Filter candidates intelligently
        for entity in all_entities:
            if entity["entity_id"] == target_id or entity.get("ai_weight", 0) < 2:
                continue
                
            entity_id = entity["entity_id"]
            entity_domain = entity_id.split('.')[0]
            entity_lower = entity_id.lower()
            
            # Priority score calculation
            score = 0
            
            # Check domain priority
            if entity_domain in priority_patterns:
                score += 10
            
            # Check name pattern matches
            for pattern in priority_patterns:
                if pattern in entity_lower:
                    score += 5
                    
            # Room correlation boost
            if room_name and room_name in entity_lower:
                score += 15
                
            # Add entity with score
            if score > 0:
                candidate_entities.append((entity, score))
        
        # Sort by score and take top candidates
        candidate_entities.sort(key=lambda x: x[1], reverse=True)
        limited_candidates = [e[0] for e in candidate_entities[:12]]  # Increased to 12 best matches
        
        if not limited_candidates:
            return []
        
        # Enhanced correlation prompt
        is_italian = language.startswith('it')
        candidates_list = ", ".join([e["entity_id"] for e in limited_candidates])
        
        if is_italian:
            prompt = f"""Analizza le correlazioni intelligenti per l'automazione domotica:

ENTITÀ PRINCIPALE: {target_id} (tipo: {target_domain})
CANDIDATI: {candidates_list}

CERCA CORRELAZIONI LOGICHE per automazioni casa intelligente:
• LUCI/INTERRUTTORI → presenza persone, sensori movimento, orario, sole
• CLIMA/RISCALDAMENTO → temperatura, presenza, finestre, meteo  
• TAPPARELLE/TENDE → sole, luminosità, temperatura, meteo, orario
• ALLARMI/SICUREZZA → presenza, porte, finestre, movimento
• MEDIA PLAYER → presenza, orario

STESSO AMBIENTE: Se {target_id} è in una stanza, priorità agli oggetti della stessa stanza.

Rispondi SOLO JSON con correlazioni UTILI per automazioni:
[{{"entity_id":"nome_entità","type":"automation","strength":1-5,"reason":"perché utile per automazione"}}]

Esempi validi:
- switch.luce_soggiorno + person.mario = "Accende luce quando Mario è a casa"
- climate.termostato + sensor.temp_esterno = "Regola in base temperatura esterna"
- cover.tapparelle + sun.sun = "Chiude con sole forte per proteggere"

Se nessuna correlazione utile: []"""
        else:
            prompt = f"""Analyze smart correlations for home automation:

MAIN ENTITY: {target_id} (type: {target_domain})
CANDIDATES: {candidates_list}

LOOK FOR LOGICAL CORRELATIONS for smart home automation:
• LIGHTS/SWITCHES → person presence, motion sensors, time, sun
• CLIMATE/HEATING → temperature, presence, windows, weather
• COVERS/BLINDS → sun, brightness, temperature, weather, time  
• ALARMS/SECURITY → presence, doors, windows, motion
• MEDIA PLAYER → presence, time

SAME ROOM: If {target_id} is in a room, prioritize objects from same room.

Reply ONLY JSON with USEFUL correlations for automations:
[{{"entity_id":"entity_name","type":"automation","strength":1-5,"reason":"why useful for automation"}}]

Valid examples:
- switch.living_room_light + person.mario = "Turn on light when Mario is home"
- climate.thermostat + sensor.outdoor_temp = "Adjust based on outdoor temperature"  
- cover.blinds + sun.sun = "Close with strong sun for protection"

If no useful correlation: []"""
        
        _LOGGER.debug(f"Correlation prompt for {target_id}")
        
        # Query AI for correlations with timeout
        try:
            response_text = await asyncio.wait_for(_query_local_agent(hass, prompt), timeout=30.0)
        except asyncio.TimeoutError:
            _LOGGER.warning(f"Correlation query timeout for {target_id}")
            return []
        
        # Parse the response
        try:
            # Clean response text
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            correlations = json.loads(response_text)
            if isinstance(correlations, list):
                # Validate and clean up correlations
                valid_correlations = []
                for corr in correlations:
                    if (isinstance(corr, dict) and 
                        "entity_id" in corr and 
                        isinstance(corr.get("strength"), (int, float)) and
                        1 <= corr.get("strength", 0) <= 5):
                        
                        # Ensure all required fields
                        validated_corr = {
                            "entity_id": corr["entity_id"],
                            "correlation_type": corr.get("type", corr.get("correlation_type", "functional")),
                            "strength": int(corr["strength"]),
                            "reason": corr.get("reason", "AI detected correlation")[:100]  # Limit reason length
                        }
                        valid_correlations.append(validated_corr)
                
                _LOGGER.info(f"Found {len(valid_correlations)} correlations for {target_id}")
                return valid_correlations
            else:
                _LOGGER.warning(f"Invalid correlation response format for {target_id}: not a list")
                return []
                
        except json.JSONDecodeError as e:
            _LOGGER.error(f"Failed to parse correlation response for {target_id}: {e}")
            _LOGGER.debug(f"Raw response: {response_text[:200]}...")
            return []
            
    except Exception as e:
        _LOGGER.error(f"Error finding correlations for {target_entity.get('entity_id', 'unknown')}: {e}")
        return []