from __future__ import annotations
import logging
import json
import asyncio
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

def _create_localized_prompt(batch_states: list[State], entity_details: list[str], language: str, compact_mode: bool = False) -> str:
    """Create a localized prompt for entity analysis with optional compact mode for token limit recovery."""
    
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
                f"Analizza {len(batch_states)} entità HA. Punteggio 0-5. "
                f"JSON: [{{\"entity_id\":\"...\",\"rating\":0-5,\"reason\":\"breve\",\"category\":\"DATA/CONTROL\",\"management_type\":\"USER/SERVICE\"}}]. "
                f"REASON IN INGLESE. Entità: " + ", ".join(entity_summary[:30])
            )
        else:
            return (
                f"Analyze {len(batch_states)} HA entities. Score 0-5. "
                f"JSON: [{{\"entity_id\":\"...\",\"rating\":0-5,\"reason\":\"brief\",\"category\":\"DATA/CONTROL\",\"management_type\":\"USER/SERVICE\"}}]. "
                f"REASON IN ENGLISH. Entities: " + ", ".join(entity_summary[:30])
            )
    
    if is_italian:
        return (
            f"Come esperto di Home Assistant, analizza queste {len(batch_states)} entità e i loro attributi per valutare la loro importanza per le automazioni su una scala da 0-5:\n\n"
            f"Scala di Valutazione:\n"
            f"0 = Ignora (diagnostica/non necessaria per automazioni)\n"
            f"1 = Molto Bassa (raramente utile, principalmente informativa)\n"
            f"2 = Bassa (occasionalmente utile, piccola comodità)\n"
            f"3 = Media (comunemente utile, buon potenziale per automazioni)\n"
            f"4 = Alta (frequentemente importante, valore significativo per automazioni)\n"
            f"5 = Critica (essenziale per automazioni, sicurezza o protezione)\n\n"
            f"IMPORTANTE - Classifica anche il tipo di entità:\n"
            f"- DATA: Entità che forniscono informazioni (sensori, meteo, stato sistemi)\n"
            f"- CONTROL: Entità controllabili dall'utente (interruttori, luci, termostati)\n\n"
            f"INOLTRE - Determina il tipo di gestione:\n"
            f"- USER: Entità che un utente normale può e dovrebbe gestire (luci, interruttori, termostati)\n"
            f"- SERVICE: Entità gestite automaticamente da servizi/integrazioni (sensori di sistema, diagnostiche)\n\n"
            f"Considera questi fattori:\n"
            f"- Tipo di dispositivo e funzionalità (dal dominio e device_class)\n"
            f"- Attributi che indicano potenziale per automazioni (caratteristiche controllabili)\n"
            f"- Rilevanza di posizione/area (informazioni stanza, zona)\n"
            f"- Importanza per sicurezza e protezione\n"
            f"- Cambiamenti di stato che attivano automazioni utili\n"
            f"- Complessità dell'integrazione vs valore per automazioni\n"
            f"- Distingui tra fonti di dati e dispositivi controllabili\n\n"
            f"Analizza sia lo stato dell'entità CHE i suoi attributi per una valutazione completa.\n"
            f"RISPONDI SEMPRE IN ITALIANO. La tua motivazione (reason) DEVE essere scritta in italiano.\n"
            f"Rispondi in formato JSON rigoroso come array di oggetti con 'entity_id', 'rating', 'reason', 'category' (DATA o CONTROL) e 'management_type' (USER o SERVICE).\n\n"
            f"Entità da analizzare:\n" + "\n".join(entity_details)
        )
    else:
        return (
            f"As a Home Assistant expert, analyze these {len(batch_states)} entities and their attributes to rate their automation importance on a scale of 0-5:\n\n"
            f"Rating Scale:\n"
            f"0 = Ignore (diagnostic/unnecessary for automations)\n"
            f"1 = Very Low (rarely useful, mostly informational)\n"
            f"2 = Low (occasionally useful, minor convenience)\n"
            f"3 = Medium (commonly useful, good automation potential)\n"
            f"4 = High (frequently important, significant automation value)\n"
            f"5 = Critical (essential for automations, security, or safety)\n\n"
            f"IMPORTANT - Also classify the entity type:\n"
            f"- DATA: Entities that provide information (sensors, weather, system status)\n"
            f"- CONTROL: Entities controllable by user (switches, lights, thermostats)\n\n"
            f"ALSO - Determine the management type:\n"
            f"- USER: Entities that a normal user can and should manage (lights, switches, thermostats)\n"
            f"- SERVICE: Entities managed automatically by services/integrations (system sensors, diagnostics)\n\n"
            f"Consider these factors:\n"
            f"- Device type and functionality (from domain and device_class)\n"
            f"- Attributes that indicate automation potential (controllable features)\n"
            f"- Location/area relevance (room, zone information)\n"
            f"- Security and safety importance\n"
            f"- State changes that trigger useful automations\n"
            f"- Integration complexity vs. automation value\n"
            f"- Distinguish between data sources and controllable devices\n\n"
            f"Analyze both the entity state AND its attributes for comprehensive scoring.\n"
            f"ALWAYS RESPOND IN ENGLISH. Your reason field MUST be in English.\n"
            f"Respond in strict JSON format as an array of objects with 'entity_id', 'rating', 'reason', 'category' (DATA or CONTROL), and 'management_type' (USER or SERVICE).\n\n"
            f"Entities to analyze:\n" + "\n".join(entity_details)
        )

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
    "camera": 4,   # Security/monitoring
    "cover": 3,    # Blinds, garage doors etc
    "fan": 3,
    "media_player": 2,
    "weather": 2,
    "sun": 1,      # Less critical for most automations
    "person": 4,   # Person tracking is important
}

async def get_entities_importance_batched(
    hass: HomeAssistant, 
    states: list[State],
    batch_size: int = 10,  # Process 10 entities at a time
    ai_provider: str = "OpenAI",
    api_key: str = None,
    connection = None,
    msg_id: str = None,
    conversation_agent: str = None,
    language: str = "en"  # Add language parameter
) -> list[dict]:
    """Calculate the importance of multiple entities using external AI providers in batches with dynamic size reduction."""
    
    if not states:
        _LOGGER.warning("No entities provided for analysis")
        return []
    
    _LOGGER.info(f"Starting AI analysis with provider: {ai_provider}, API key present: {bool(api_key)}")
    
    # Local agent doesn't need API key
    if ai_provider != AI_PROVIDER_LOCAL and not api_key:
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
            all_results.append(_create_fallback_result(state.entity_id, 0))
        return all_results
    
    all_results = []
    current_batch_size = batch_size
    remaining_states = states.copy()
    overall_batch_num = 0
    token_limit_retries = 0
    max_retries = 3
    use_compact_mode = False  # Start with full mode
    
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
        
        success = await _process_single_batch(
            hass, batch_states, overall_batch_num, ai_provider, 
            connection, msg_id, conversation_agent, all_results, language, use_compact_mode
        )
        
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
                        fallback_result = _create_fallback_result(state.entity_id, overall_batch_num, "token_limit_exceeded")
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
            all_results.append(_create_fallback_result(state.entity_id, 0))

    # Send scan completion message to frontend
    if connection and msg_id:
        connection.send_message(websocket_api.event_message(msg_id, {
            "type": "scan_complete",
            "data": {
                "total_entities": len(all_results),
                "message": f"Scansione completata! Analizzate {len(all_results)} entità"
            }
        }))

    _LOGGER.info(f"🏁 Completed analysis of {len(states)} entities, got {len(all_results)} results")
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
    use_compact_prompt: bool = False  # Add compact mode flag
) -> bool:
    """Process a single batch and return True if successful, False if token limit exceeded."""
    
    # Create detailed entity information for AI analysis
    entity_details = []
    
    if not use_compact_prompt:
        # Full detailed analysis
        for state in batch_states:
            # Get comprehensive entity info including key attributes
            attributes = dict(state.attributes)
            
            # Extract important attributes for analysis
            important_attrs = {}
            
            # Common important attributes
            attr_keys = [
                'device_class', 'unit_of_measurement', 'friendly_name', 
                'supported_features', 'entity_category', 'icon',
                'room', 'area', 'location', 'zone', 'floor',
                # Climate specific
                'temperature', 'target_temperature', 'hvac_mode', 'hvac_modes',
                # Light specific  
                'brightness', 'color_mode', 'supported_color_modes',
                # Sensor specific
                'state_class', 'last_changed', 'last_updated',
                # Security specific
                'device_type', 'tamper', 'battery_level',
                # Media specific
                'source', 'volume_level', 'media_title',
                # Cover specific
                'current_position', 'position',
                # Switch/Binary sensor specific
                'device_class',
            ]
            
            for key in attr_keys:
                if key in attributes and attributes[key] is not None:
                    important_attrs[key] = attributes[key]
            
            # Create detailed description
            entity_description = (
                f"- Entity: {state.entity_id}\n"
                f"  Domain: {state.domain}\n" 
                f"  Name: {state.attributes.get('friendly_name', state.entity_id.split('.')[-1])}\n"
                f"  Current State: {state.state}\n"
                f"  Attributes: {json.dumps(important_attrs, default=str)}\n"
            )
            
            entity_details.append(entity_description)
    
    # Add delay to make AI analysis visible
    await asyncio.sleep(1.5 if use_compact_prompt else 2.5)
    
    # Create localized prompt based on user's language and mode
    prompt = _create_localized_prompt(batch_states, entity_details, language, compact_mode=use_compact_prompt)
    
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
                
                return False  # Signal token limit exceeded
                
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
                fallback_result = _create_fallback_result(state.entity_id, batch_num)
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
                        if category not in ["DATA", "CONTROL"]:
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
                        all_results.append(result)
                        
                        # Send result to frontend immediately
                        if connection and msg_id:
                            connection.send_message(websocket_api.event_message(msg_id, {
                                "type": "entity_result",
                                "result": result
                            }))
                    else:
                        _LOGGER.warning(f"Invalid rating {rating} for entity {item['entity_id']}, using fallback")
                        fallback_result = _create_fallback_result(item["entity_id"], batch_num)
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
                fallback_result = _create_fallback_result(state.entity_id, batch_num)
                all_results.append(fallback_result)
                
                # Send fallback result to frontend
                if connection and msg_id:
                    connection.send_message(websocket_api.event_message(msg_id, {
                        "type": "entity_result",
                        "result": fallback_result
                    }))

    except json.JSONDecodeError as e:
        _LOGGER.warning(f"AI response is not valid JSON for batch {batch_num} - Raw response: {response_text} - Error: {e}")
        _LOGGER.info(f"Falling back to domain-based classification for batch {batch_num}")
        # Use fallback for all entities in this batch
        for state in batch_states:
            fallback_result = _create_fallback_result(state.entity_id, batch_num)
            all_results.append(fallback_result)
            
            # Send fallback result to frontend
            if connection and msg_id:
                connection.send_message(websocket_api.event_message(msg_id, {
                    "type": "entity_result",
                    "result": fallback_result
                }))
    except Exception as e:
        _LOGGER.error(f"Error querying AI for batch {batch_num}: {e}")
        _LOGGER.info(f"Falling back to domain-based classification for batch {batch_num}")
        # Use fallback for all entities in this batch
        for state in batch_states:
            fallback_result = _create_fallback_result(state.entity_id, batch_num)
            all_results.append(fallback_result)
            
            # Send fallback result to frontend
            if connection and msg_id:
                connection.send_message(websocket_api.event_message(msg_id, {
                    "type": "entity_result",
                    "result": fallback_result
                }))

    return True  # Success


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


def _create_fallback_result(entity_id: str, batch_num: int, reason: str = "domain_fallback") -> dict:
    """Create a fallback result when AI analysis fails."""
    domain = entity_id.split(".")[0]
    
    # Use domain-based importance mapping
    importance = ENTITY_IMPORTANCE_MAP.get(domain, 2)
    
    # Determine management type based on domain
    user_managed_domains = {"light", "switch", "climate", "cover", "fan", "lock", "alarm_control_panel", "input_boolean", "input_number", "input_select", "input_text"}
    service_managed_domains = {"sensor", "binary_sensor", "weather", "sun", "system_log", "automation", "script"}
    
    if domain in user_managed_domains:
        management_type = "user"
    elif domain in service_managed_domains:
        management_type = "service"
    else:
        management_type = "user"  # Default to user for unknown domains
    
    # Determine category based on domain
    data_domains = {"sensor", "binary_sensor", "weather", "sun", "person", "device_tracker"}
    category = "DATA" if domain in data_domains else "CONTROL"
    
    reason_map = {
        0: "Entity marked as ignore - likely diagnostic or unnecessary",
        1: "Very low importance - rarely used in automations",
        2: "Low importance - domain suggests limited automation value",
        3: "Medium importance - commonly useful for automations",
        4: "High importance - frequently used in smart home automations",
        5: "Critical importance - essential for security/safety automations"
    }
    
    if reason == "token_limit_exceeded":
        fallback_reason = f"{reason_map[importance]} (fallback due to token limit exceeded)"
        analysis_method = "domain_fallback_token_limit"
    else:
        fallback_reason = f"{reason_map[importance]} (using domain-based classification)"
        analysis_method = "domain_fallback"
    
    return {
        "entity_id": entity_id,
        "overall_weight": importance,
        "overall_reason": fallback_reason,
        "category": category,
        "management_type": management_type,
        "analysis_method": analysis_method,
        "batch_number": batch_num,
    }


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
    """Find correlations between a target entity and other entities using AI."""
    try:
        target_id = target_entity["entity_id"]
        target_weight = target_entity["ai_weight"]
        target_reason = target_entity["reason"]
        target_category = target_entity["category"]
        
        # Only consider entities with weight >= target's weight for correlations
        candidate_entities = [e for e in all_entities if e["entity_id"] != target_id and e["ai_weight"] >= target_weight]
        
        if not candidate_entities:
            return []
        
        # Create a concise prompt for correlation analysis
        is_italian = language.startswith('it')
        
        if is_italian:
            prompt = f"""Analizza se l'entità "{target_id}" (categoria: {target_category}, peso: {target_weight}, motivo: {target_reason}) potrebbe essere correlata con queste altre entità importanti:

{chr(10).join([f"- {e['entity_id']} (categoria: {e['category']}, peso: {e['ai_weight']}, motivo: {e['reason']})" for e in candidate_entities[:10]])}

Rispondi SOLO con un JSON array di correlazioni trovate. Ogni correlazione deve avere:
- "entity_id": ID dell'entità correlata
- "correlation_type": "functional" | "location" | "temporal" | "data_dependency" 
- "strength": numero da 1-5 (5=molto forte)
- "reason": breve spiegazione della correlazione

Se non trovi correlazioni, rispondi con array vuoto: []"""
        else:
            prompt = f"""Analyze if entity "{target_id}" (category: {target_category}, weight: {target_weight}, reason: {target_reason}) could be correlated with these other important entities:

{chr(10).join([f"- {e['entity_id']} (category: {e['category']}, weight: {e['ai_weight']}, reason: {e['reason']})" for e in candidate_entities[:10]])}

Reply ONLY with a JSON array of found correlations. Each correlation must have:
- "entity_id": ID of correlated entity  
- "correlation_type": "functional" | "location" | "temporal" | "data_dependency"
- "strength": number 1-5 (5=very strong)
- "reason": brief explanation of correlation

If no correlations found, reply with empty array: []"""
        
        # Query AI for correlations
        response_text = await _query_local_agent(hass, prompt)
        
        # Parse the response
        try:
            correlations = json.loads(response_text.strip())
            if isinstance(correlations, list):
                # Validate and clean up correlations
                valid_correlations = []
                for corr in correlations:
                    if (isinstance(corr, dict) and 
                        "entity_id" in corr and 
                        "correlation_type" in corr and 
                        "strength" in corr and 
                        "reason" in corr):
                        valid_correlations.append(corr)
                
                _LOGGER.info(f"Found {len(valid_correlations)} correlations for {target_id}")
                return valid_correlations
            else:
                _LOGGER.warning(f"Invalid correlation response format for {target_id}")
                return []
        except json.JSONDecodeError as e:
            _LOGGER.error(f"Failed to parse correlation response for {target_id}: {e}")
            return []
            
    except Exception as e:
        _LOGGER.error(f"Error finding correlations for {target_entity.get('entity_id', 'unknown')}: {e}")
        return []