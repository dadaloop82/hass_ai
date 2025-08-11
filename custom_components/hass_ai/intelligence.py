from __future__ import annotations
import logging
import json
import asyncio
from typing import Optional

from .const import AI_PROVIDER_OPENAI, AI_PROVIDER_GEMINI, AI_PROVIDER_LOCAL
from homeassistant.core import HomeAssistant, State
from homeassistant.components import conversation, websocket_api
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

# Try to import AI libraries, but don't fail if they're not available
try:
    import openai
    OPENAI_AVAILABLE = True
    _LOGGER.info("✅ OpenAI library successfully imported")
except ImportError as e:
    OPENAI_AVAILABLE = False
    _LOGGER.warning(f"❌ OpenAI library not available: {e}")

try:
    import google.generativeai as genai
    GOOGLE_AI_AVAILABLE = True
    _LOGGER.info("✅ Google Generative AI library successfully imported")
except ImportError as e:
    GOOGLE_AI_AVAILABLE = False
    _LOGGER.warning(f"❌ Google Generative AI library not available: {e}")

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
            
            # Choose AI provider based on configuration
            if ai_provider == AI_PROVIDER_LOCAL:
                response_text = await _query_local_agent(hass, prompt)
                _LOGGER.debug(f"Local Agent response for batch {batch_num}: {response_text[:200]}...")
            elif ai_provider == AI_PROVIDER_OPENAI and OPENAI_AVAILABLE and api_key:
                response_text = await _query_openai(prompt, api_key)
                _LOGGER.debug(f"OpenAI response for batch {batch_num}: {response_text[:200]}...")
            elif ai_provider == AI_PROVIDER_GEMINI and GOOGLE_AI_AVAILABLE and api_key:
                response_text = await _query_gemini(prompt, api_key)
                _LOGGER.debug(f"Gemini response for batch {batch_num}: {response_text[:200]}...")
            else:
                _LOGGER.error(f"AI provider {ai_provider} not available or missing API key")
                # Send debug info about provider unavailable
                if connection and msg_id:
                    suggestion = ""
                    if ai_provider == "Gemini" and not GOOGLE_AI_AVAILABLE and OPENAI_AVAILABLE:
                        suggestion = " Suggerimento: Prova a cambiare il provider ad OpenAI nelle impostazioni dell'integrazione."
                    elif ai_provider == "OpenAI" and not OPENAI_AVAILABLE and GOOGLE_AI_AVAILABLE:
                        suggestion = " Suggerimento: Prova a cambiare il provider a Gemini nelle impostazioni dell'integrazione."
                    
                    debug_data = {
                        "aiProvider": ai_provider,
                        "currentBatch": batch_num,
                        "lastPrompt": f"ERRORE: Provider {ai_provider} non disponibile!",
                        "lastResponse": f"OpenAI disponibile: {OPENAI_AVAILABLE}, Gemini disponibile: {GOOGLE_AI_AVAILABLE}, Chiave API presente: {bool(api_key)}.{suggestion}"
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


async def _query_openai(prompt: str, api_key: str) -> str:
    """Query OpenAI API."""
    if not OPENAI_AVAILABLE:
        raise Exception("OpenAI library not available")
    
    client = openai.AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.1
    )
    return response.choices[0].message.content


async def _query_gemini(prompt: str, api_key: str) -> str:
    """Query Google Gemini API."""
    if not GOOGLE_AI_AVAILABLE:
        raise Exception("Google Generative AI library not available")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    response = await model.generate_content_async(prompt)
    return response.text


async def _query_local_agent(hass: HomeAssistant, prompt: str) -> str:
    """Query Home Assistant local conversation agent."""
    try:
        # Get the conversation agent
        agent = await conversation.async_get_agent(hass, None)
        
        # Create a conversation request
        conversation_input = conversation.ConversationInput(
            text=prompt,
            context=conversation.ConversationContext(),
            conversation_id=None,
            device_id=None,
            language=hass.config.language
        )
        
        # Process the conversation
        result = await agent.async_process(conversation_input)
        
        # Return the response text
        return result.response.response_type.text
        
    except Exception as e:
        _LOGGER.error(f"Error querying local conversation agent: {e}")
        # Return a simple structured response as fallback
        return """[
{"entity_id": "fallback", "rating": 2, "reason": "Agente locale non disponibile, usando classificazione domain-based"}
]"""