# HASS AI - Home Assistant Artificial Intelligence

**HASS AI** is a custom integration for Home Assistant that provides a visual, interactive interface to manage the importance and inclusion of your entities for AI-driven automations.

Instead of being a black box, HASS AI creates a full control panel within Home Assistant, allowing you to see, control, and fine-tune how your smart home is understood by artificial intelligence.

## Features

- **Automatic Entity Analysis**: On first startup, the integration scans all your Home Assistant entities and assigns a baseline "importance" score (from 1 to 5) and a reason for that score.
- **Visual Control Panel**: For every entity in your system, the integration creates:
  - A **Number slider** (`number.hass_ai_..._weight`) to see and adjust the importance weight.
  - A **Switch** (`switch.hass_ai_..._enabled`) to include or ignore the entity in any AI logic.
- **Full Transparency**: You can see why a certain weight was assigned and override it at any time.
- **Persistent User Control**: Your overrides for weights and enabled/disabled status are saved and persist across restarts.
- **No More Black Boxes**: You have the final say on how your home is perceived by AI.

## Getting Started

1.  Install the HASS AI integration via HACS.
2.  Restart Home Assistant.
3.  Add the "HASS AI" integration from the **Settings > Devices & Services** page.
4.  After a few moments, go to the integration's page. You will see it populated with number and switch entities, one for each of your devices.
5.  Explore the entities, adjust their weights, and disable any you wish to ignore. Your smart home's intelligence model is now ready and customized by you!
