# HASS AI Features

## V0.4.0: The Interactive Control Panel

This version introduces the core user experience: a dedicated frontend panel for managing your home's AI model.

- **Dedicated Frontend Panel**: The integration now has its own page in the Home Assistant sidebar, built with modern web components.
- **Websocket API**: A robust backend API using websockets allows for real-time communication between the panel and Home Assistant.
- **Live Entity Scanning**: Users can initiate a scan from the frontend and see the results populate the table in real-time without waiting for the full scan to complete.
- **Interactive Controls**: The panel provides switches and dropdowns to enable/disable entities and override their AI-assigned weights.
- **Persistent Storage**: All user overrides are saved to a single JSON file in the `.storage` directory, ensuring settings are kept across restarts.
- **Simplified Backend**: The core Python code is now cleaner, focused on providing the API and the initial analysis, making it more stable and maintainable.
