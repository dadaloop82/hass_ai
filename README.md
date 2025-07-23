# HASS AI - Home Assistant Artificial Intelligence

**HASS AI** is a custom integration for Home Assistant designed to bring a new level of intelligence to your smart home. It analyzes your entities, understands their purpose, and provides a foundation for smarter, more automated control of your home.

## Features

- **Entity Intelligence Analysis**: Automatically scans all your Home Assistant entities and assigns an "importance" score (from 1 to 5) based on their domain, device class, naming, and other properties. This creates a semantic understanding of your home.
- **Service-Based Analysis**: Trigger the analysis at any time through the `hass_ai.analyze_entities` service call.
- **Persistent Storage**: The results of the analysis are saved in your Home Assistant storage, creating a persistent "brain" for your smart home.

## How It Works

The core of HASS AI is the `analyze_entities` service. When called, it iterates through all your devices and sensors, applying a dynamic weighting algorithm to determine which entities are most critical for intelligent control. The results, including the score and the reasoning behind it, are stored in a `.storage/hass_ai_intelligence.json` file.

This intelligence layer can then be used as a foundation for more advanced automations, dashboards, and voice control.

## Getting Started

1.  Install the integration.
2.  Restart Home Assistant.
3.  Go to **Developer Tools > Services** and call the `hass_ai.analyze_entities` service.
4.  The intelligence file will be created, and your HASS AI is ready to be used by other components or automations.
