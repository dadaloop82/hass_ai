# HASS AI - Home Assistant Artificial Intelligence

**HASS AI** is a custom integration for Home Assistant that acts as an intelligence layer for your built-in conversation agent (Assist).

It works by first analyzing all your entities to understand their purpose and importance. Then, it provides a service that injects this context into your prompts before sending them to the conversation agent you have already configured in Home Assistant.

This allows for more powerful and context-aware commands, regardless of whether you use OpenAI, Google, or another provider.

## Features

- **Automatic Entity Analysis**: On startup, the integration scans all your entities and assigns an "importance" score (from 1 to 5).
- **Seamless Integration with Assist**: Uses the `conversation.process` service to interact with the AI provider you have configured globally in Home Assistant.
- **Intelligent Prompt Service**: Provides a `hass_ai.prompt` service that enriches your commands with crucial context about your home.
- **Zero Configuration**: No API keys to manage. Just install and use.

## How It Works

1.  **Analysis**: On startup, HASS AI creates an "intelligence" file in your `.storage` directory, mapping out your home's entities and their importance.
2.  **Prompting**: When you call the `hass_ai.prompt` service with a command like "Turn off the main lights," the integration enhances the prompt to something like: "Based on this list of important lights: [light.living_room_main, ...], please process the request: Turn off the main lights."
3.  **Execution**: This enhanced prompt is sent to Home Assistant's native conversation agent, which then handles the command with a much better understanding of your intent.

## Getting Started

1.  Ensure you have a conversation agent (like OpenAI, Google Generative AI, etc.) configured in Home Assistant under **Settings > Devices & Services > Assist**.
2.  Install the HASS AI integration via HACS.
3.  Restart Home Assistant.
4.  The integration is ready. You can now use the `hass_ai.prompt` service in your automations and scripts.