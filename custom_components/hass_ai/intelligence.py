from __future__ import annotations
import logging
import json
import asyncio
from typing import Optional

from .const import AI_PROVIDER_LOCAL
from homeassistant.core import HomeAssistant, State
from homeassistant.components import conversation, websocket_api
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

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
    msg_id: str = None
) -> list[dict]:
    """Calculate the importance of multiple entities using external AI providers in batches."""
    
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
    total_batches = (len(states) + batch_size - 1) // batch_size
    
    for i in range(0, len(states), batch_size):
        batch_states = states[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        _LOGGER.debug(f"Processing batch {batch_num}/{total_batches} with {len(batch_states)} entities")
        
        # Create detailed entity information for AI analysis
        entity_details = []
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
        
        # Add delay to make AI analysis visible (2-3 seconds per batch)
        await asyncio.sleep(2.5)
        
        prompt = (
            f"As a Home Assistant expert, analyze these {len(batch_states)} entities and their attributes to rate their automation importance on a scale of 0-5:\n\n"
            f"Rating Scale:\n"
            f"0 = Ignore (diagnostic/unnecessary for automations)\n"
            f"1 = Very Low (rarely useful, mostly informational)\n"
            f"2 = Low (occasionally useful, minor convenience)\n"
            f"3 = Medium (commonly useful, good automation potential)\n"
            f"4 = High (frequently important, significant automation value)\n"
            f"5 = Critical (essential for automations, security, or safety)\n\n"
            f"Consider these factors:\n"
            f"- Device type and functionality (from domain and device_class)\n"
            f"- Attributes that indicate automation potential (controllable features)\n"
            f"- Location/area relevance (room, zone information)\n"
            f"- Security and safety importance\n"
            f"- State changes that trigger useful automations\n"
            f"- Integration complexity vs. automation value\n\n"
            f"Analyze both the entity state AND its attributes for comprehensive scoring.\n"
            f"Respond in strict JSON format as an array of objects with 'entity_id', 'rating', and 'reason'.\n\n"
            f"Entities to analyze:\n" + "\n".join(entity_details)
        )

        try:
            # Send debug info to frontend
            if connection and msg_id:
                debug_data = {
                    "aiProvider": ai_provider,
                    "currentBatch": batch_num,
                    "lastPrompt": prompt,
                    "lastResponse": ""
                }
                connection.send_message(websocket_api.event_message(msg_id, {
                    "type": "debug_info", 
                    "data": debug_data
                }))
            
            # Use Local Agent only
            if ai_provider == AI_PROVIDER_LOCAL:
                response_text = await _query_local_agent(hass, prompt)
                _LOGGER.debug(f"Local Agent response for batch {batch_num}: {response_text[:200]}...")
            else:
                _LOGGER.error(f"AI provider {ai_provider} not supported. Only Local Agent is available.")
                # Send debug info about provider unavailable
                if connection and msg_id:
                    debug_data = {
                        "aiProvider": ai_provider,
                        "currentBatch": batch_num,
                        "lastPrompt": f"ERRORE: Provider {ai_provider} non supportato!",
                        "lastResponse": "Solo l'Agente Locale è disponibile. Assicurati di avere configurato una LLM come Ollama."
                    }
                    connection.send_message(websocket_api.event_message(msg_id, {
                        "type": "debug_info", 
                        "data": debug_data
                    }))
                # Use fallback for all entities in this batch
                for state in batch_states:
                    all_results.append(_create_fallback_result(state.entity_id, batch_num))
                continue

            # Send response debug info to frontend
            if connection and msg_id:
                debug_data = {
                    "aiProvider": ai_provider,
                    "currentBatch": batch_num,
                    "lastPrompt": prompt,
                    "lastResponse": response_text[:1000] + ("..." if len(response_text) > 1000 else "")
                }
                connection.send_message(websocket_api.event_message(msg_id, {
                    "type": "debug_info", 
                    "data": debug_data
                }))

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
                            all_results.append({
                                "entity_id": item["entity_id"],
                                "overall_weight": rating,
                                "overall_reason": item["reason"],
                                "analysis_method": "ai_conversation",
                                "batch_number": batch_num,
                            })
                        else:
                            _LOGGER.warning(f"Invalid rating {rating} for entity {item['entity_id']}, using fallback")
                            all_results.append(_create_fallback_result(item["entity_id"], batch_num))
                    else:
                        _LOGGER.warning(f"Malformed AI response item: {item}")
            else:
                _LOGGER.warning(f"AI response is not a list, using fallback for batch {batch_num}")
                # Use fallback for all entities in this batch
                for state in batch_states:
                    all_results.append(_create_fallback_result(state.entity_id, batch_num))

        except json.JSONDecodeError as e:
            _LOGGER.warning(f"AI response is not valid JSON for batch {batch_num} - Raw response: {response_text} - Error: {e}")
            _LOGGER.info(f"Falling back to domain-based classification for batch {batch_num}")
            # Use fallback for all entities in this batch
            for state in batch_states:
                all_results.append(_create_fallback_result(state.entity_id, batch_num))
        except Exception as e:
            _LOGGER.error(f"Error querying AI for batch {batch_num}: {e}")
            _LOGGER.info(f"Falling back to domain-based classification for batch {batch_num}")
            # Use fallback for all entities in this batch
            for state in batch_states:
                all_results.append(_create_fallback_result(state.entity_id, batch_num))

    # Ensure all entities have a result (fallback for any missing)
    processed_entity_ids = {res["entity_id"] for res in all_results}
    for state in states:
        if state.entity_id not in processed_entity_ids:
            all_results.append(_create_fallback_result(state.entity_id, 0))

    _LOGGER.info(f"Completed analysis of {len(states)} entities, got {len(all_results)} results")
    return all_results


def _create_fallback_result(entity_id: str, batch_num: int) -> dict:
    """Create a fallback result when AI analysis fails."""
    domain = entity_id.split(".")[0]
    
    # Use domain-based importance mapping
    importance = ENTITY_IMPORTANCE_MAP.get(domain, 2)
    
    reason_map = {
        0: "Entity marked as ignore - likely diagnostic or unnecessary",
        1: "Very low importance - rarely used in automations",
        2: "Low importance - domain suggests limited automation value",
        3: "Medium importance - commonly useful for automations",
        4: "High importance - frequently used in smart home automations",
        5: "Critical importance - essential for security/safety automations"
    }
    
    return {
        "entity_id": entity_id,
        "overall_weight": importance,
        "overall_reason": f"{reason_map[importance]} (using domain-based classification)",
        "analysis_method": "domain_fallback",
        "batch_number": batch_num,
    }


async def _query_local_agent(hass: HomeAssistant, prompt: str) -> str:
    """Query Home Assistant local conversation agent using HA services."""
    try:
        _LOGGER.info(f"🤖 Querying local conversation agent via HA services...")
        
        # Try to detect available conversation agents by looking at entities
        conversation_agents = []
        for entity_id in hass.states.async_entity_ids("conversation"):
            if entity_id != "conversation.home_assistant":  # Skip default agent
                conversation_agents.append(entity_id)
                _LOGGER.info(f"🔍 Found conversation agent: {entity_id}")
        
        # Use the first non-default agent found, or None for default
        agent_id = conversation_agents[0] if conversation_agents else None
        
        if agent_id:
            _LOGGER.info(f"🎯 Using conversation agent: {agent_id}")
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