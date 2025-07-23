class HassAiPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          padding: 16px;
        }
      </style>
      <h1>HASS AI Control Panel</h1>
      <p>Welcome to the future of your smart home's intelligence. The interactive table will be displayed here.</p>
      <button id="scan-button">Start Scan</button>
      <div id="results"></div>
    `;

    this.shadowRoot.getElementById('scan-button').addEventListener('click', () => {
        // Logic to call the backend API will go here
        this.shadowRoot.getElementById('results').innerHTML = '<p>Scan started... (This is a placeholder)</p>';
    });
  }
}

customElements.define('hass-ai-panel', HassAiPanel);
