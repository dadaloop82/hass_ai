from homeassistant.core import State

REASON_WEIGHTS = {
    # Domain-based reasons
    "domain_alarm": ("Domain: Alarm", 5),
    "domain_lock": ("Domain: Lock", 5),
    "domain_climate": ("Domain: Climate", 4),
    "domain_person": ("Domain: Person", 4),
    "domain_automation": ("Domain: Automation", 4),
    "domain_light": ("Domain: Light", 3),
    "domain_switch": ("Domain: Switch", 3),
    "domain_binary_sensor": ("Domain: Binary Sensor", 3),
    "domain_device_tracker": ("Domain: Device Tracker", 3),
    "domain_script": ("Domain: Script", 3),
    "domain_sensor": ("Domain: Sensor", 2),
    "domain_media_player": ("Domain: Media Player", 2),
    "domain_default": ("Domain: Default", 1),

    # Device class reasons
    "device_class_motion": ("Device Class: Motion", 2),
    "device_class_door": ("Device Class: Door", 2),
    "device_class_window": ("Device Class: Window", 2),
    "device_class_smoke": ("Device Class: Smoke/Safety", 2),
    "device_class_lock": ("Device Class: Lock", 2),
    "device_class_presence": ("Device Class: Presence/Occupancy", 2),
    "device_class_power": ("Device Class: Power/Energy", 1),
    "device_class_temperature": ("Device Class: Temperature", 1),
    "device_class_humidity": ("Device Class: Humidity", 1),
    "device_class_battery": ("Device Class: Battery", 1),

    # Keyword reasons
    "keyword_main": ("Keyword: Main/Master", 2),
    "keyword_living_kitchen": ("Keyword: Living/Kitchen", 1),
    "keyword_security": ("Keyword: Alarm/Security/Door", 2),
    "keyword_monitoring": ("Keyword: Camera/Motion/Presence", 1),
    "keyword_environment": ("Keyword: Temp/Humidity/Energy", 1),

    # Attribute-based reasons
    "attr_common": ("Attribute: Common Important", 1),
    "attr_low_battery": ("Attribute: Low Battery", 2),
    "attr_active": ("Attribute: Is Active", 1),
    "attr_high_value": ("Attribute: High Value", 1),
}

def get_entity_importance(state: State) -> dict:
    """Calculate the initial importance of an entity and its attributes."""
    domain = state.domain
    attributes = state.attributes
    entity_id = state.entity_id
    
    entity_weight = 1
    entity_reasons = []
    attribute_details = {}

    # Domain
    domain_map = {
        "alarm_control_panel": "domain_alarm", "lock": "domain_lock", "climate": "domain_climate",
        "person": "domain_person", "automation": "domain_automation", "light": "domain_light",
        "switch": "domain_switch", "binary_sensor": "domain_binary_sensor", "device_tracker": "domain_device_tracker",
        "script": "domain_script", "sensor": "domain_sensor", "media_player": "domain_media_player"
    }
    reason_key = domain_map.get(domain, "domain_default")
    reason_text, weight = REASON_WEIGHTS[reason_key]
    if weight > 1:
        entity_weight += weight -1
        entity_reasons.append(reason_text)

    # Device Class
    device_class = attributes.get("device_class")
    if device_class:
        dc_map = {
            "motion": "device_class_motion", "door": "device_class_door", "window": "device_class_window",
            "smoke": "device_class_smoke", "safety": "device_class_smoke", "lock": "device_class_lock",
            "presence": "device_class_presence", "occupancy": "device_class_presence", "power": "device_class_power",
            "energy": "device_class_power", "temperature": "device_class_temperature", "humidity": "device_class_humidity",
            "battery": "device_class_battery"
        }
        reason_key = dc_map.get(device_class)
        if reason_key:
            reason_text, bonus = REASON_WEIGHTS[reason_key]
            entity_weight += bonus
            entity_reasons.append(f"{reason_text} (+{bonus})")

    # Keywords
    name = attributes.get("friendly_name", "").lower()
    entity_id_lower = entity_id.lower()
    keyword_map = {
        ("main", "master"): "keyword_main",
        ("living", "kitchen"): "keyword_living_kitchen",
        ("alarm", "security", "front_door"): "keyword_security",
        ("camera", "motion", "presence"): "keyword_monitoring",
        ("temperature", "humidity", "energy"): "keyword_environment"
    }
    for keywords, reason_key in keyword_map.items():
        if any(k in name or k in entity_id_lower for k in keywords):
            reason_text, bonus = REASON_WEIGHTS[reason_key]
            entity_weight += bonus
            entity_reasons.append(f"{reason_text} (+{bonus})")

    # Attributes
    for attr_key, attr_value in attributes.items():
        attr_weight = 1
        attr_reasons = []
        if attr_key in ["battery_level", "temperature", "humidity", "power", "last_triggered", "on"]:
            reason_text, bonus = REASON_WEIGHTS["attr_common"]
            attr_weight += bonus
            attr_reasons.append(reason_text)
        if attr_key == "battery_level" and isinstance(attr_value, (int, float)) and attr_value < 20:
            reason_text, bonus = REASON_WEIGHTS["attr_low_battery"]
            attr_weight += bonus
            attr_reasons.append(f"{reason_text}: {attr_value}%")
        if attr_key == "on" and attr_value is True:
            reason_text, bonus = REASON_WEIGHTS["attr_active"]
            attr_weight += bonus
            attr_reasons.append(reason_text)
        if isinstance(attr_value, (int, float)) and attr_value > 100 and "energy" in attr_key:
            reason_text, bonus = REASON_WEIGHTS["attr_high_value"]
            attr_weight += bonus
            attr_reasons.append(f"{reason_text}: {attr_value}")
        
        attr_weight = max(1, min(5, attr_weight))
        if attr_weight > 1:
            entity_weight += (attr_weight - 1) * 0.5
        
        attribute_details[attr_key] = {
            "weight": attr_weight,
            "reason": ", ".join(attr_reasons) or "Default"
        }

    entity_weight = max(1, min(5, round(entity_weight)))
    
    return {
        "entity_id": entity_id,
        "overall_weight": entity_weight,
        "overall_reason": ", ".join(entity_reasons) or "Default",
        "attribute_details": attribute_details
    }
