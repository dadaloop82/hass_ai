# HASS AI Features

## V0.2.0: Integration with Home Assistant Assist

This version represents a complete architectural shift to a more stable, flexible, and powerful integration with Home Assistant's native conversation agent (Assist).

- **Removed Direct Dependencies**: The integration no longer requires `openai` or `google-generativeai` as direct dependencies. This resolves all installation conflicts.
- **Simplified Configuration**: The configuration flow has been removed. The integration no longer requires API keys. It relies on the central Assist configuration in Home Assistant.
- **New `hass_ai.prompt` Service**: This is the new primary feature. It takes a text prompt, injects context from the entity intelligence analysis, and forwards it to the `conversation.process` service.
- **Automatic Entity Analysis**: The analysis of entity importance is now performed automatically on Home Assistant startup.
- **Removed `options_flow` and `coordinator`**: These are no longer needed in the new, simpler architecture.
