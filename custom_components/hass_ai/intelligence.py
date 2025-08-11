from __future__ import annotations
import logging
import json
from typing import Optional

from homeassistant.core import HomeAssistant, State
from homeassistant.components import conversation
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

# Try to import AI libraries, but don't fail if they're not available
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    _LOGGER.info("OpenAI library not available, falling back to conversation agent")

try:
    import google.generativeai as genai
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    GOOGLE_AI_AVAILABLE = False
    _LOGGER.info("Google Generative AI library not available, falling back to conversation agent")

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
    ai_provider: str = "conversation",
    api_key: str = None
) -> list[dict]:
    """Calculate the importance of multiple entities using the conversation agent in batches."""
    
    if not states:
        _LOGGER.warning("No entities provided for analysis")
        return []
    
    all_results = []
    total_batches = (len(states) + batch_size - 1) // batch_size
    
    for i in range(0, len(states), batch_size):
        batch_states = states[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        _LOGGER.debug(f"Processing batch {batch_num}/{total_batches} with {len(batch_states)} entities")
        
        # Create detailed entity information for AI analysis
        entity_details = []
        for state in batch_states:
            # Get basic entity info
            entity_info = {
                "entity_id": state.entity_id,
                "domain": state.domain,
                "name": state.name or state.entity_id.split(".")[-1],
                "state": str(state.state),
                "unit": state.attributes.get("unit_of_measurement", ""),
                "device_class": state.attributes.get("device_class", ""),
                "friendly_name": state.attributes.get("friendly_name", "")
            }
            
            entity_details.append(
                f"- entity_id: {entity_info['entity_id']}, "
                f"domain: {entity_info['domain']}, "
                f"name: {entity_info['friendly_name']}, "
                f"state: {entity_info['state']}, "
                f"device_class: {entity_info['device_class']}"
            )
        
        prompt = (
            f"As a Home Assistant expert, analyze these {len(batch_states)} entities and rate their automation importance on a scale of 0-5:\n"
            f"0 = Ignore (diagnostic/unnecessary)\n"
            f"1 = Very Low (rarely useful)\n"
            f"2 = Low (occasionally useful)\n"
            f"3 = Medium (commonly useful)\n"
            f"4 = High (frequently important)\n"
            f"5 = Critical (essential for automations)\n\n"
            f"Consider: device type, location relevance, automation potential, security importance.\n"
            f"Respond in strict JSON format as an array of objects with 'entity_id', 'rating', and 'reason'.\n\n"
            f"Entities:\n" + "\n".join(entity_details)
        )

        try:
            # Choose AI provider based on configuration
            if ai_provider == "conversation":
                response_text = await _query_conversation_agent(hass, prompt)
            elif ai_provider == "OpenAI" and OPENAI_AVAILABLE and api_key:
                response_text = await _query_openai(prompt, api_key)
            elif ai_provider == "Gemini" and GOOGLE_AI_AVAILABLE and api_key:
                response_text = await _query_gemini(prompt, api_key)
            else:
                _LOGGER.warning(f"AI provider {ai_provider} not available, falling back to conversation agent")
                response_text = await _query_conversation_agent(hass, prompt)

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
            _LOGGER.warning(f"AI response is not valid JSON for batch {batch_num}: {response_text[:200]}... - Error: {e}")
            # Use fallback for all entities in this batch
            for state in batch_states:
                all_results.append(_create_fallback_result(state.entity_id, batch_num))
        except Exception as e:
            _LOGGER.error(f"Error querying AI for batch {batch_num}: {e}")
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
        "overall_reason": f"{reason_map[importance]} (AI analysis unavailable, using domain-based classification)",
        "analysis_method": "domain_fallback",
        "batch_number": batch_num,
    }


async def _query_conversation_agent(hass: HomeAssistant, prompt: str) -> str:
    """Query the Home Assistant conversation agent."""
    agent_response = await conversation.async_converse(hass, prompt, None, "en")
    return agent_response.response.speech["plain"]["speech"]


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