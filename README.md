# HASS AI - Your Smart Home's Intelligent Assistant

**HASS AI** transforms your Home Assistant into a truly intelligent environment by providing a powerful, interactive tool to manage how your system understands and prioritizes your devices and entities. It acts as an advanced intelligence layer, allowing you to teach your Home Assistant which entities are most important, which properties to focus on, and which to disregard.

This is achieved through a dedicated, intuitive control panel within Home Assistant where you can visualize, fine-tune, and manage an AI-generated model of your home's digital landscape.

## The Core Philosophy

An AI is only as smart as the data it has. HASS AI is built on three core principles:

1.  **AI Proposes, You Decide**: The system performs an initial, intelligent analysis of all your Home Assistant entities, evaluating each based on its type, name, attributes, and historical data. This provides a smart, actionable starting point.
2.  **Full Transparency**: No more black boxes. You see exactly why each entity and its properties received their importance scores, with clear explanations and reasoning.
3.  **Total User Control**: You have the final say. Through an interactive panel, you can easily override any AI suggestion, disable entities or properties you don't care about, and fine-tune their weights to perfectly match your home's unique needs and your personal preferences.

## How It Works

1.  **Installation**: After installing the HASS AI integration, a new **HASS AI** panel will appear in your Home Assistant sidebar, providing a centralized hub for managing your smart home's intelligence.
2.  **Initial Scan & Real-time Analysis**: Navigate to the HASS AI panel. Upon initiating a scan, the system will analyze your home's entities in real-time, populating a dynamic table with detailed insights, importance scores, and reasons for each evaluation.
3.  **Intelligent Tuning**: Review the comprehensive table. For each entity and its properties, you can:
    - **Adjust the Importance (Weight)**: Use a simple dropdown or slider to change the AI-assigned weight from 1 (least important) to 5 (critical), influencing how other automations or AI models interact with it.
    - **Enable/Disable**: Use a toggle to completely exclude an entity or specific properties from being considered by the AI, ensuring focus on what truly matters.
4.  **Automatic Saving & Persistence**: All your adjustments and overrides are saved automatically and persist across Home Assistant restarts, ensuring your customized intelligence model is always active.

Once tuned, this refined intelligence model can be leveraged by other automations, scripts, and future integrations to perform truly smart, context-aware actions, optimizing your Home Assistant experience.

## Getting Started

### Step 1: Installation

1.  Install the HASS AI integration via HACS (Home Assistant Community Store).
2.  Restart Home Assistant to ensure all components are loaded correctly.

### Step 2: Initial Configuration

1.  Go to **Settings > Devices & Services** in Home Assistant.
2.  Click on **"Add Integration"** and search for "HASS AI".
3.  Follow the on-screen prompts. During this process, you will be asked to configure the **Scan Interval**.
    *   **Scan Interval**: This setting determines how frequently (in days) HASS AI will automatically perform a background scan of your entities to update its intelligence model. A value of `7` means it will scan once a week. You can set this between `1` and `30` days.

### Step 3: Accessing the HASS AI Panel

1.  After successful configuration, a new **HASS AI** item will automatically appear in your Home Assistant sidebar.
2.  Click on this item to open the HASS AI control panel.

### Step 4: Performing an Initial Scan and Tuning

1.  Within the HASS AI panel, click the **"Start New Scan"** button to perform an immediate analysis of your entities.
2.  Observe the real-time feedback as the system scans and populates the table with insights.
3.  Customize the weights and enable/disable entities and their properties directly within the panel to fit your specific needs and preferences. Your changes will be saved automatically.
