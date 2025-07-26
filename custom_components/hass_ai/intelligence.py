from __future__ import annotations
import logging
import re

from homeassistant.core import State
from homeassistant.components import conversation

_LOGGER = logging.getLogger(__name__)

async def get_entity_importance(
    hass: conversation.AbstractConversationAgent, 
    state: State
) -> dict:
    """Calculate the importance of an entity using the conversation agent."""
    
    prompt = (
        f"As a Home Assistant expert, rate the automation importance of this entity on a scale of 0 (ignore) to 5 (essential). "
        f"Provide a brief, one-sentence reason. Entity: {state.entity_id}, Name: {state.name}, State: {state.state}, Attributes: {state.attributes}. "
        f"Respond strictly in the format: Rating: [0-5], Reason: [Your reason]"
    )

    try:
        agent_response = await conversation.async_converse(hass, prompt, None, "en")
        response_text = agent_response.response.speech["plain"]["speech"]

        rating_match = re.search(r"Rating: (\d)", response_text)
        reason_match = re.search(r"Reason: (.*)", response_text)

        if rating_match and reason_match:
            rating = int(rating_match.group(1))
            reason = reason_match.group(1).strip()
            return {
                "overall_weight": rating,
                "overall_reason": reason,
                "prompt": prompt,
                "response_text": response_text,
            }

    except Exception as e:
        _LOGGER.warning(f"Error querying AI for entity {state.entity_id}: {e}")

    # Fallback if AI fails or response is malformed
    return {
        "overall_weight": 1,
        "overall_reason": "AI analysis failed; using default weight.",
    }