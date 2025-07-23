# HASS AI - Home Assistant Artificial Intelligence

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

Bring the power of Artificial Intelligence to your Home Assistant instance. This integration analyzes your entities, identifies what's important, and provides a foundation for building powerful, context-aware automations.

## Features

- **AI-Powered Entity Analysis**: Automatically identifies important entities and attributes for home automation.
- **Flexible AI Provider**: Choose between OpenAI (ChatGPT) and Google (Gemini) to power the analysis.
- **Interactive Configuration**: A user-friendly configuration flow to set up the integration, select entities, and view AI-driven insights.
- **HACS Compatible**: Easy installation and updates via the Home Assistant Community Store (HACS).

## Getting Started

1.  **Installation**: Add this repository to HACS or manually copy the `custom_components/hass_ai` directory to your Home Assistant configuration.
2.  **Configuration**: Go to **Settings > Devices & Services**, click **Add Integration**, and search for **HASS AI**.
3.  **Setup**: Follow the on-screen instructions to select your AI provider, enter your API key, and start the initial entity screening.

## How It Works

The integration fetches all your Home Assistant entities and sends them to the selected AI for analysis. The AI's task is to determine which entities and their specific attributes are most relevant for automation. The results are then stored in the integration's configuration, ready to be used by your automations or other services.