# HASS AI Features

This document outlines the current and planned features for the HASS AI integration.

## Current Features

### V1: Entity Intelligence Analysis

- **Service**: `hass_ai.analyze_entities`
- **Description**: This is the core feature of the integration. It provides a mechanism to analyze and rank all entities within Home Assistant to determine their relative importance for smart home control.
- **How it works**:
  - The service iterates through all entities (lights, switches, sensors, etc.).
  - It applies a weighting algorithm that considers:
    - **Domain**: The entity type (e.g., `light`, `lock`, `climate`).
    - **Device Class**: Provides context (e.g., a `binary_sensor` can be a `door`, `window`, or `motion` sensor).
    - **Unit of Measurement**: Helps identify the purpose of a sensor (e.g., `W` for power, `°C` for temperature).
    - **Keywords**: Looks for terms like `main`, `master`, `alarm`, or `test` in the entity ID and friendly name to adjust the score.
  - The final score is normalized to a value between 1 (not important) and 5 (critical).
- **Output**:
  - The results are saved to a JSON file located at `<config>/.storage/hass_ai_intelligence.json`.
  - Each entity includes a `weight` and a `reason` explaining how the score was determined.

## Planned Features

- **Automated Automation Generation**: Use the intelligence layer to suggest or automatically create automations for common scenarios (e.g., "turn off all important lights when the alarm is armed").
- **Natural Language Control**: Integrate with voice assistants to allow for more natural commands (e.g., "secure the house" would know to lock doors and check windows).
- **Dynamic Dashboards**: Automatically create Lovelace views that highlight the most important entities.