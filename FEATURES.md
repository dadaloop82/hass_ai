# HASS AI Features

## V0.3.0: The Interactive Control Panel

This version represents a fundamental shift in philosophy, moving from a "black box" service to a fully transparent and interactive control panel for your home's AI model.

- **New Entity-Based Architecture**: The integration now creates `number` and `switch` entities for every device in your Home Assistant instance.
- **Weight Control Sliders**: Each `number.hass_ai_..._weight` entity allows you to see and manually override the AI-assigned importance score (1-5).
- **Enable/Disable Switches**: Each `switch.hass_ai_..._enabled` entity allows you to completely exclude a device from being considered by the AI.
- **Full Persistence**: All user overrides are saved to Home Assistant's storage and persist across restarts.
- **Removed Services**: The old `prompt` and `analyze_entities` services have been removed in favor of this new, direct-control architecture.
- **Simplified Core**: The core logic is now focused on creating and managing these control entities, making the integration more stable and predictable.