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
            f"Analizza {len(batch_states)} entità HA per UTILITÀ DOMOTICA. Valuta quanto sono utili per automazioni, controllo casa, benessere e ottimizzazione. Punteggio 0-5:\n"
            f"0=Inutile per domotica, 1=Molto poco utile, 2=Poco utile, 3=Mediamente utile, 4=Molto utile, 5=Essenziale per automazioni\n"
            f"\nVALUTA INTELLIGENTEMENTE:\n"
            f"• Utilità per automazioni e controllo casa\n"
            f"• Importanza per comfort, sicurezza, risparmio energetico\n"
            f"• Valore per monitoraggio e manutenzione\n"
            f"• Rilevanza per presenza, benessere, ottimizzazione\n"
            f"\nCATEGORIE (scegli in base alla funzione principale):\n"
            f"- DATA: informazioni utili (sensori ambientali, stato dispositivi, misurazioni)\n"
            f"- CONTROL: controlli azionabili (interruttori, regolazioni, comandi)\n" 
            f"- ALERTS: monitoraggio critico (batterie scariche, guasti, manutenzione, sicurezza, problemi)\n"
            f"\nIMPORTANTE per ALERTS: Sensori di batteria, vento forte, temperature estreme, umidità critica possono essere ALERTS!\n"
            f"\nTIPO GESTIONE:\n"
            f"- USER: l'utente può controllare/configurare direttamente\n"
            f"- SERVICE: richiede servizi tecnici o automazioni di sistema\n"
            f"\nJSON: [{{\"entity_id\":\"...\",\"rating\":0-5,\"reason\":\"DESCRIZIONE DETTAGLIATA: cosa fa questo sensore e PERCHÉ è utile per la domotica. Spiega il valore specifico per automazioni/controllo casa\",\"category\":\"DATA/CONTROL/ALERTS\",\"management_type\":\"USER/SERVICE\"}}]\n"
            f"REASON OBBLIGATORIO: Descrivi COSA FA l'entità e PERCHÉ è importante per la domotica. NON dire solo 'utilità automazioni' ma spiega il valore specifico!\n\n" + "\n".join(entity_details)
        )
    else:
        prompt = (
            f"Analyze {len(batch_states)} HA entities for HOME AUTOMATION UTILITY. Evaluate how useful they are for automations, house control, wellness and optimization. Score 0-5:\n"
            f"0=Useless for automation, 1=Very low utility, 2=Low utility, 3=Medium utility, 4=High utility, 5=Essential for automations\n"
            f"\nEVALUATE INTELLIGENTLY:\n"
            f"• Utility for automations and house control\n"
            f"• Importance for comfort, security, energy saving\n"
            f"• Value for monitoring and maintenance\n"
            f"• Relevance for presence, wellness, optimization\n"
            f"\nCATEGORIES (choose based on primary function):\n"
            f"- DATA: useful information (environmental sensors, device status, measurements)\n"
            f"- CONTROL: actionable controls (switches, adjustments, commands)\n"
            f"- ALERTS: critical monitoring (low batteries, failures, maintenance, security, issues)\n"
            f"\nIMPORTANT for ALERTS: Battery sensors, strong wind, extreme temperatures, critical humidity can be ALERTS!\n"
            f"\nMANAGEMENT TYPE:\n"
            f"- USER: user can directly control/configure\n"
            f"- SERVICE: requires technical services or system automations\n"
            f"\nJSON: [{{\"entity_id\":\"...\",\"rating\":0-5,\"reason\":\"DETAILED DESCRIPTION: what this sensor does and WHY it's useful for home automation. Explain specific value for automations/house control\",\"category\":\"DATA/CONTROL/ALERTS\",\"management_type\":\"USER/SERVICE\"}}]\n"
            f"REASON MANDATORY: Describe WHAT the entity does and WHY it's important for home automation. DON'T just say 'automation utility' but explain the specific value!\n\n" + "\n".join(entity_details)
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
def _auto_categorize_entity(state: State) -> tuple[str, str]:
    """Automatically categorize entity based on domain and characteristics.
    Returns (category, management_type)."""
    domain = state.domain
    entity_id = state.entity_id
    attributes = state.attributes
    entity_state = state.state
    
    # Check for alerts/problems first
    if entity_state in ['unavailable', 'unknown', 'error']:
        return 'ALERTS', 'SERVICE'
    
    # Only keep critical state-based checks, let AI decide the rest
    battery_level = attributes.get('battery_level')
    if battery_level is not None and battery_level < 15:  # Only very critical levels
        return 'ALERTS', 'SERVICE'
    
    # Domain-based categorization with management type - basic guidelines only
    if domain == 'camera':
        # Cameras typically provide data and can benefit from AI vision services
        return 'DATA', 'SERVICE'
    elif domain == 'update':
        # Update entities are informational and may trigger service actions
        return 'DATA', 'SERVICE'
    elif domain in ['sensor', 'binary_sensor']:
        # Let AI decide if sensors are DATA or ALERTS based on their purpose
        # Only obvious diagnostic sensors get SERVICE type
        if any(keyword in entity_id.lower() for keyword in ['rssi', 'linkquality', 'uptime', 'memory', 'cpu', 'disk', 'connection']):
            return 'DATA', 'SERVICE'  # Clear diagnostic sensors
        else:
            return 'DATA', 'USER'  # Let AI decide DATA vs ALERTS in analysis
    elif domain in ['weather']:
        # Weather entities provide important environmental data
        return 'DATA', 'USER'
    elif domain in ['device_tracker', 'person', 'zone']:
        return 'DATA', 'USER'
    elif domain in ['switch', 'light', 'climate', 'cover', 'fan', 'media_player']:
        return 'CONTROL', 'USER'
    elif domain in ['lock', 'alarm_control_panel']:
        return 'CONTROL', 'SERVICE'
    elif domain in ['input_boolean', 'input_select', 'input_number', 'input_text']:
        return 'CONTROL', 'USER'
    elif domain in ['alert', 'automation']:
        return 'ALERTS', 'SERVICE'
    else:
        # Default based on entity name patterns
        if any(keyword in entity_id for keyword in ['temperature', 'humidity', 'pressure']):
            return 'DATA', 'USER'
        elif any(keyword in entity_id for keyword in ['battery', 'signal', 'rssi', 'linkquality']):
            return 'DATA', 'SERVICE'
        elif any(keyword in entity_id for keyword in ['switch', 'light', 'fan', 'heater']):
            return 'CONTROL', 'USER'
        else:
            return 'DATA', 'USER'  # Default to DATA/USER for unknown entities

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
            
            # Check if this entity warrants alert thresholds
            needs_thresholds = False
            
            if domain == 'binary_sensor':
                device_class = attributes.get('device_class', '')
                if device_class in ['battery', 'problem', 'safety', 'smoke', 'gas', 'moisture']:
                    needs_thresholds = True
                    
            elif domain == 'sensor':
                try:
                    num_value = float(current_value)
                    # Only generate for obvious alert-worthy sensors
                    if (device_class == 'battery' or 'battery' in entity_id.lower() or 
                        'temperature' in entity_id.lower() or 'humidity' in entity_id.lower() or
                        'wind' in entity_id.lower() or any(keyword in entity_id.lower() for keyword in ['cpu', 'memory', 'disk'])):
                        needs_thresholds = True
                except (ValueError, TypeError):
                    pass
            
            if needs_thresholds:
                # AI-generated thresholds prompt
                threshold_prompt = (
                    f"Proponi soglie di allerta per l'entità: {entity_id}\n"
                    f"Valore attuale: {current_value} {unit}\n"
                    f"Tipo dispositivo: {device_class}\n"
                    f"Domini: {domain}\n\n"
                    f"Genera 3 soglie di allerta (LOW, MEDIUM, HIGH) con valori specifici appropriati.\n"
                    f"Considera:\n"
                    f"- Batterie: soglie per basso/critico\n"
                    f"- Temperature: soglie per comfort/sicurezza\n"
                    f"- Umidità: soglie per comfort/muffa\n"
                    f"- Vento: soglie per condizioni meteo\n"
                    f"- Sistema: soglie per performance\n\n"
                    f"JSON: {{\"LOW\":{{\"value\":numero,\"condition\":\"condizione\",\"description\":\"descrizione\"}},\"MEDIUM\":{{\"value\":numero,\"condition\":\"condizione\",\"description\":\"descrizione\"}},\"HIGH\":{{\"value\":numero,\"condition\":\"condizione\",\"description\":\"descrizione\"}}}}\n"
                    f"Esempio batteria: {{\"LOW\":{{\"value\":30,\"condition\":\"< 30%\",\"description\":\"Batteria in esaurimento\"}},\"MEDIUM\":{{\"value\":20,\"condition\":\"< 20%\",\"description\":\"Batteria bassa\"}},\"HIGH\":{{\"value\":10,\"condition\":\"< 10%\",\"description\":\"Batteria critica\"}}}}"
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
            if device_class in ['battery', 'problem', 'safety', 'smoke', 'gas', 'moisture']:
                result.update({
                    "entity_type": "binary_alert",
                    "thresholds": {
                        "LOW": {"condition": "state == 'on'", "description": "Sensor activated"},
                        "MEDIUM": {"condition": "state == 'on' for > 5 minutes", "description": "Persistent activation"},
                        "HIGH": {"condition": "state == 'on' for > 30 minutes", "description": "Long-term issue"}
                    }
                })
            return result
            
        # Numeric sensors - basic fallback thresholds
        elif domain == 'sensor':
            try:
                num_value = float(current_value)
                unit = attributes.get('unit_of_measurement', '')
                device_class = attributes.get('device_class', '')
                
                # Battery percentage - only generate if clearly a battery sensor
                if (device_class == 'battery' or 'battery_level' in entity_id.lower()) and 0 <= num_value <= 100:
                    result.update({
                        "entity_type": "battery_percent",
                        "thresholds": {
                            "LOW": {"value": 30, "condition": "< 30%", "description": "Battery getting low"},
                            "MEDIUM": {"value": 20, "condition": "< 20%", "description": "Battery low"},
                            "HIGH": {"value": 10, "condition": "< 10%", "description": "Battery critical"}
                        }
                    })
                    
            except (ValueError, TypeError):
                # Non-numeric sensor
                pass
                
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
    analysis_type: str = "importance"  # Add analysis type parameter
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
    
    while remaining_states:
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
            connection, msg_id, conversation_agent, all_results, language, use_compact_mode, analysis_type
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
                },
                "auto_start_correlations": True  # Signal frontend to auto-start correlations
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
    analysis_type: str = "importance"  # Add analysis type parameter
) -> tuple[bool, dict]:
    """Process a single batch and return success status and token statistics."""
    
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
                        # Get category, default to UNKNOWN if not provided
                        category = item.get("category", "UNKNOWN")
                        if category not in ["DATA", "CONTROL", "HEALTH"]:
                            category = "UNKNOWN"
                        
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
                        
                        # Generate auto-thresholds only for very obvious cases
                        if category == 'ALERTS' or 'battery' in item["entity_id"].lower():
                            state = next((s for s in batch_states if s.entity_id == item["entity_id"]), None)
                            if state and hass:
                                auto_thresholds = await _generate_auto_thresholds(hass, item["entity_id"], state)
                                if auto_thresholds.get("thresholds"):
                                    result["auto_thresholds"] = auto_thresholds
                        
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
        category, management_type = _auto_categorize_entity(state)
    else:
        # Fallback domain-based categorization
        data_domains = {"sensor", "binary_sensor", "weather", "sun", "person", "device_tracker", "camera", "update"}
        control_domains = {"light", "switch", "climate", "cover", "fan", "lock", "input_boolean", "input_number", "input_select", "input_text", "media_player"}
        
        entity_lower = entity_id.lower()
        if ("battery" in entity_lower or 
            "unavailable" in entity_lower or 
            "offline" in entity_lower or
            "signal" in entity_lower or
            "error" in entity_lower or
            "connection" in entity_lower or
            "alarm" in entity_lower or
            "alert" in entity_lower):
            category = "ALERTS"
            management_type = "SERVICE"
        elif domain in data_domains:
            category = "DATA"
            management_type = "USER"
        elif domain in control_domains:
            category = "CONTROL"
            management_type = "USER"
        else:
            category = "DATA"  # Default to DATA
            management_type = "USER"
    
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
        # Create more descriptive reasons for auto-categorization
        domain = entity_id.split('.')[0] if '.' in entity_id else ''
        if domain == 'weather':
            fallback_reason = f"Weather sensor providing {reason_map[importance].lower()} environmental data for automation decisions"
        elif domain == 'sensor' and 'battery' in entity_id.lower():
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
    
    # Generate auto-thresholds only for obvious battery cases in fallback
    if 'battery' in entity_id.lower() and category == 'ALERTS':
        try:
            # Simple fallback threshold logic for obvious battery sensors
            auto_thresholds = {
                "auto_generated": True,
                "entity_type": "fallback_battery",
                "thresholds": {
                    "LOW": {"value": 30, "condition": "< 30%", "description": "Battery getting low"},
                    "MEDIUM": {"value": 20, "condition": "< 20%", "description": "Battery low"},
                    "HIGH": {"value": 10, "condition": "< 10%", "description": "Battery critical"}
                }
            }
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
{"entity_id": "fallback", "rating": 2, "reason": "Servizio conversazione non disponibile - verifica configurazione agente in Impostazioni > Assistenti vocali"}
]"""


async def find_entity_correlations(hass: HomeAssistant, target_entity: dict, all_entities: list[dict], language: str) -> list[dict]:
    """Find correlations between a target entity and other entities using simplified AI prompts."""
    try:
        target_id = target_entity["entity_id"]
        target_weight = target_entity["ai_weight"]
        target_category = target_entity.get("category", "UNKNOWN")
        
        # Only consider entities with weight >= 2 for correlations (more selective)
        candidate_entities = [e for e in all_entities if e["entity_id"] != target_id and e.get("ai_weight", 0) >= 2]
        
        if not candidate_entities:
            return []
        
        # Ultra-simplified prompt to avoid token limits
        is_italian = language.startswith('it')
        
        # Limit candidates to first 8 to keep prompt small
        limited_candidates = candidate_entities[:8]
        candidates_list = ", ".join([e["entity_id"] for e in limited_candidates])
        
        if is_italian:
            prompt = f"""Secondo te l'entità {target_id} potrebbe essere correlata a quale tra queste: {candidates_list}?

Rispondi SOLO JSON: [{{"entity_id":"nome_entità","type":"functional","strength":3,"reason":"breve motivo"}}]
Se nessuna correlazione: []"""
        else:
            prompt = f"""Which of these entities could {target_id} be correlated with: {candidates_list}?

Reply ONLY JSON: [{{"entity_id":"entity_name","type":"functional","strength":3,"reason":"brief reason"}}]
If no correlation: []"""
        
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