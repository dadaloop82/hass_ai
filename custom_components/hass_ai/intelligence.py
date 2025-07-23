from homeassistant.core import State

def get_entity_importance(state: State) -> dict:
    """Calculate the initial importance of an entity."""
    domain = state.domain
    attributes = state.attributes
    entity_id = state.entity_id
    weight = 1
    reasons = []

    domain_weights = {
        "alarm_control_panel": 5, "lock": 5, "climate": 4, "light": 3,
        "switch": 3, "binary_sensor": 3, "sensor": 2, "media_player": 2
    }
    weight = domain_weights.get(domain, 1)
    if weight > 1: reasons.append(f"Domain '{domain}'")

    device_class = attributes.get("device_class")
    if device_class:
        device_class_weights = {
            "motion": 2, "door": 2, "window": 2, "smoke": 2, "safety": 2, "lock": 2,
            "power": 1, "temperature": 1, "humidity": 1, "energy": 1
        }
        bonus = device_class_weights.get(device_class, 0)
        if bonus > 0:
            weight += bonus
            reasons.append(f"Class '{device_class}'")

    name = attributes.get("friendly_name", "").lower()
    entity_id_lower = entity_id.lower()
    keywords = {
        "main": 2, "master": 2, "living": 1, "kitchen": 1, "front_door": 2, "alarm": 2
    }
    for key, bonus in keywords.items():
        if key in name or key in entity_id_lower:
            weight += bonus
            reasons.append(f"Keyword '{key}'")

    weight = max(1, min(5, weight))
    return {"weight": weight, "reason": ", ".join(reasons) or "Default"}
