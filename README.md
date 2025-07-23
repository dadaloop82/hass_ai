# HASS AI - Your Smart Home's Brain

**HASS AI** is a powerful, interactive tool that gives you complete control over how Home Assistant understands your devices. It acts as an intelligence layer, allowing you to teach your system which entities are important and which should be ignored.

This is achieved through a dedicated control panel where you can see, tune, and manage an AI-generated model of your home.

## The Core Philosophy

An AI is only as smart as the data it has. HASS AI is built on three core principles:

1.  **AI Proposes, You Decide**: The system performs an initial analysis to give you a smart starting point, evaluating every entity based on its type, name, and function. 
2.  **Full Transparency**: No more black boxes. You see exactly why each entity received its score.
3.  **Total User Control**: You have the final say. Through an interactive panel, you can override any AI suggestion, disable entities you don't care about, and fine-tune the weights to perfectly match your home's unique needs.

## How It Works

1.  **Installation**: After installing, you will find a new **HASS AI** panel in your Home Assistant sidebar.
2.  **Initial Scan**: Navigate to the panel and click "Start Scan". The system will analyze your home and populate a table with all your entities in real-time.
3.  **Tuning**: Review the table. For each entity, you can:
    - **Adjust the Importance (Weight)**: Use a simple dropdown to change the AI-assigned weight from 1 (unimportant) to 5 (critical).
    - **Enable/Disable**: Use a toggle to completely exclude an entity from being used by the AI.
4.  **Automatic Saving**: Your changes are saved automatically and persist across restarts.

Once tuned, this intelligence model can be used by other automations or services (future feature) to perform truly smart actions.

## Getting Started

1.  Install the HASS AI integration via HACS and restart Home Assistant.
2.  Add the "HASS AI" integration from the **Settings > Devices & Services** page.
3.  A new **HASS AI** item will appear in your sidebar. Click it to open the control panel.
4.  Click the **"Start New Scan"** button to perform the initial analysis.
5.  Customize the weights and enable/disable entities to fit your needs.