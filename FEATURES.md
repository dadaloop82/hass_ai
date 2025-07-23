# Features

## Core Features

- **AI Provider Selection**: Configure the integration to use either OpenAI (ChatGPT) or Google (Gemini) as the AI backend.
- **API Key Configuration**: Securely store your AI provider's API key.
- **Entity Screening Flow**: A multi-step configuration process to guide the user through the setup.
- **Real-time Entity Discovery**: Automatically fetches all available entities from your Home Assistant instance.
- **User-driven Entity Selection**: Allows the user to select which entities should be included in the AI analysis.
- **AI-Powered Analysis**: Sends the selected entities and their attributes to the chosen AI for categorization.
- **Intelligent Prompt Engineering**: Constructs a detailed prompt asking the AI to identify entities and attributes relevant for home automation.
- **Coordinator-based Architecture**: Manages state and API calls centrally for a robust and scalable integration.

## Planned Features

- **AI Response Processing**: Parse the AI's response and store the categorized data.
- **Results Visualization**: Display the AI-analyzed results in a user-friendly format.
- **Manual Override**: Allow users to edit and save the AI's suggestions.
- **Service Exposure**: Expose the categorized entity data as a service for use in automations.
