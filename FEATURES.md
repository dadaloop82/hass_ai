# HASS AI Features

## V0.5.1: The Interactive Control Panel & Enhanced Intelligence

This version introduces the core user experience: a dedicated frontend panel for managing your home's AI model, alongside significant enhancements to the intelligence gathering and presentation.

- **Dedicated Frontend Panel**: The integration now has its own comprehensive page in the Home Assistant sidebar, built with modern web components for a seamless user experience.
- **Websocket API**: A robust backend API using websockets allows for real-time, efficient communication between the panel and Home Assistant, ensuring a responsive interface.
- **Live Entity Scanning with Detailed Insights**: Users can initiate a scan from the frontend and see the results populate a dynamic table in real-time. This includes not only the entity ID and name but also its calculated importance (weight) and a clear, concise reason for that importance.
- **Interactive Controls for Fine-Tuning**: The panel provides intuitive switches and dropdowns to enable/disable entities and their specific properties, and to override their AI-assigned weights. This gives users granular control over the intelligence model.
- **Persistent Storage for User Overrides**: All user overrides and custom configurations are saved automatically to a single JSON file in the `.storage` directory, ensuring settings are kept across Home Assistant restarts and updates.
- **Simplified and Robust Backend**: The core Python code has been refactored for clarity and stability, focusing on providing a reliable API and an extensible framework for initial entity analysis.
- **Future-Ready Architecture**: Designed to support future enhancements, including scheduled scans, advanced property-level analysis, and integration with other Home Assistant automations and AI models.