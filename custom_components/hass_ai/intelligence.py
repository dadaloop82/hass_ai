from __future__ import annotations
import logging
import json

from homeassistant.core import State
from homeassistant.components import conversation

_LOGGER = logging.getLogger(__name__)

async def get_entities_importance(
    hass: conversation.AbstractConversationAgent, 
    states: list[State]
) -> list[dict]:
    """Calculate the importance of multiple entities using the conversation agent."""
    
    entity_details = []
    for state in states:
        entity_details.append(
            f"- entity_id: {state.entity_id}, name: {state.name}, state: {state.state}, attributes: {state.attributes}"
        )
    
    prompt = (
        f"As a Home Assistant expert, analyze the following entities and rate their automation importance on a scale of 0 (ignore) to 5 (essential). "
        f"Provide a brief, one-sentence reason for each. Respond strictly in JSON format, as an array of objects. "
        f"Each object should have 'entity_id', 'rating', and 'reason' keys.\n"
        f"Entities:\n" + "\n".join(entity_details)
    )

    all_results = []
    try:
        agent_response = await conversation.async_converse(hass, prompt, None, "en")
        response_text = agent_response.response.speech["plain"]["speech"]

        # Attempt to parse the response as JSON
        parsed_response = json.loads(response_text)

        if isinstance(parsed_response, list):
            for item in parsed_response:
                if isinstance(item, dict) and "entity_id" in item and "rating" in item and "reason" in item:
                    all_results.append({
                        "entity_id": item["entity_id"],
                        "overall_weight": int(item["rating"]),
                        "overall_reason": item["reason"],
                        "prompt": prompt, # Store the single prompt for all entities
                        "response_text": response_text, # Store the single response for all entities
                    })
                else:
                    _LOGGER.warning(f"Malformed item in AI response: {item}")
        else:
            _LOGGER.warning(f"AI response is not a list: {response_text}")

    except json.JSONDecodeError as e:
        _LOGGER.warning(f"AI response is not valid JSON: {response_text} - Error: {e}")
    except Exception as e:
        _LOGGER.warning(f"Error querying AI for entities: {e}")

    # Fallback for entities that didn't get a valid response or if AI failed
    for state in states:
        if not any(res["entity_id"] == state.entity_id for res in all_results):
            all_results.append({
                "entity_id": state.entity_id,
                "overall_weight": 1,
                "overall_reason": "AI analysis failed or response malformed; using default weight.",
                "prompt": prompt if 'prompt' in locals() else "No prompt generated.",
                "response_text": response_text if 'response_text' in locals() else "No response received.",
            })

    return all_results
