from homeassistant.core import State

def get_entity_importance(state: State) -> dict:
    """Calculate the initial importance of an entity and its attributes."""
    domain = state.domain
    attributes = state.attributes
    entity_id = state.entity_id
    
    entity_weight = 1
    entity_reasons = []
    attribute_details = {}

    # Domain-based weighting
    domain_weights = {
        "alarm_control_panel": 5, "lock": 5, "climate": 4, "light": 3,
        "switch": 3, "binary_sensor": 3, "sensor": 2, "media_player": 2,
        "person": 4, "device_tracker": 3, "automation": 4, "script": 3
    }
    domain_calculated_weight = domain_weights.get(domain, 1)
    if domain_calculated_weight > 1:
        entity_weight += domain_calculated_weight - 1 # Add only the bonus
        entity_reasons.append(f"Domain '{domain}' (base {domain_calculated_weight})")

    # Device class weighting
    device_class = attributes.get("device_class")
    if device_class:
        device_class_weights = {
            "motion": 2, "door": 2, "window": 2, "smoke": 2, "safety": 2, "lock": 2,
            "power": 1, "temperature": 1, "humidity": 1, "energy": 1, "battery": 1,
            "presence": 2, "occupancy": 2
        }
        bonus = device_class_weights.get(device_class, 0)
        if bonus > 0:
            entity_weight += bonus
            entity_reasons.append(f"Device Class '{device_class}' (bonus {bonus})")

    # Name and entity_id keyword weighting
    name = attributes.get("friendly_name", "").lower()
    entity_id_lower = entity_id.lower()
    keywords = {
        "main": 2, "master": 2, "living": 1, "kitchen": 1, "front_door": 2, "alarm": 2,
        "security": 2, "camera": 2, "temperature": 1, "humidity": 1, "energy": 1,
        "motion": 1, "presence": 1
    }
    for key, bonus in keywords.items():
        if key in name or key in entity_id_lower:
            entity_weight += bonus
            entity_reasons.append(f"Keyword '{key}' in name/ID (bonus {bonus})")

    # Attribute-based weighting
    for attr_key, attr_value in attributes.items():
        attr_weight = 1
        attr_reasons = []

        # Common attributes that might indicate importance
        if attr_key in ["battery_level", "temperature", "humidity", "current_power_w", "last_triggered", "on"]: # Add more relevant attributes
            attr_weight += 1
            attr_reasons.append(f"Common attribute '{attr_key}'")
        
        # Check for specific attribute values that might indicate importance
        if isinstance(attr_value, (bool, int, float)):
            if attr_key == "battery_level" and isinstance(attr_value, (int, float)) and attr_value < 20:
                attr_weight += 2
                attr_reasons.append(f"Low battery level ({attr_value}%)")
            elif attr_key == "on" and attr_value is True:
                attr_weight += 1
                attr_reasons.append(f"Attribute '{attr_key}' is True")
            # Add more value-based checks as needed

        # If an attribute has a significant value (e.g., a large number for energy)
        if isinstance(attr_value, (int, float)) and attr_value > 100 and "energy" in attr_key:
            attr_weight += 1
            attr_reasons.append(f"High value for '{attr_key}'")

        # Cap attribute weight
        attr_weight = max(1, min(5, attr_weight))
        attribute_details[attr_key] = {
            "weight": attr_weight,
            "reason": ", ".join(attr_reasons) or "Default"
        }
        # Add attribute weight to entity weight, but with diminishing returns or only if significant
        if attr_weight > 1:
            entity_weight += (attr_weight - 1) * 0.5 # Add half the bonus from attribute to entity

    # Cap entity weight
    entity_weight = max(1, min(5, entity_weight))
    
    return {
        "entity_id": entity_id,
        "overall_weight": round(entity_weight),
        "overall_reason": ", ".join(entity_reasons) or "Default",
        "attribute_details": attribute_details
    }