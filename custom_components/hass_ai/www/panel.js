const LitElement = Object.getPrototypeOf(customElements.get("ha-panel-lovelace"));
const html = LitElement.prototype.html;
const css = LitElement.prototype.css;

class HassAiPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      route: { type: Object },
      panel: { type: Object },
      entities: { state: true },
      loading: { state: true },
      language: { state: true },
      agentInfo: { state: true },
    };
  }

  constructor() {
    super();
    this.entities = {};
    this.loading = false;
    this.overrides = {};
    this.saveTimeout = null;
    this.language = 'en'; // Default language
  }

  connectedCallback() {
    super.connectedCallback();
    this.language = this.hass.language || 'en';
    this._loadOverrides();
  }

  async _loadOverrides() {
    this.overrides = await this.hass.callWS({ type: "hass_ai/load_overrides" });
  }

  async _runScan() {
    this.loading = true;
    this.entities = {};

    await this.hass.connection.subscribeMessage(
      (message) => this._handleScanUpdate(message),
      { type: "hass_ai/scan_entities" }
    );
  }


  _handleScanUpdate(message) {
    if (message.type === "entity_result") {
      const entity = message.result;
      this.entities[entity.entity_id] = entity;
      this.requestUpdate("entities");
    }
    if (message.type === "scan_complete") {
      this.loading = false;
    }
  }

  _handleToggle(ev) {
    const entityId = ev.target.dataset.entityId;
    const checked = ev.target.checked;
    if (!this.overrides[entityId]) {
      this.overrides[entityId] = {};
    }
    this.overrides[entityId].enabled = checked;
    this._debouncedSave();
  }

  _handleWeightChange(ev) {
    const selectEl = ev.target;
    const entityId = selectEl.dataset.entityId;
    const selectedIndex = selectEl.selectedIndex;
    const weight = parseInt(selectEl.children[selectedIndex].getAttribute("value"), 10);

    if (!this.overrides[entityId]) {
      this.overrides[entityId] = {};
    }
    this.overrides[entityId].overall_weight = weight;
    this._debouncedSave();
  }

  _debouncedSave() {
    clearTimeout(this.saveTimeout);
    this.saveTimeout = setTimeout(() => {
      this.hass.callWS({ type: "hass_ai/save_overrides", overrides: this.overrides });
    }, 1000);
  }

  render() {
    const sortedEntities = Object.values(this.entities).sort((a, b) => {
      const aWeight = this.overrides[a.entity_id]?.overall_weight ?? a.overall_weight;
      const bWeight = this.overrides[b.entity_id]?.overall_weight ?? b.overall_weight;
      return bWeight - aWeight;
    });

    const t = this.language === 'it' ? {
      title: "Pannello di Controllo HASS AI",
      description: "Analizza le tue entità, insegna all'IA e personalizza i pesi per ottimizzare la tua domotica.",
      scan_button: "Avvia Nuova Scansione",
      scanning_button: "Scansione...",
      enabled: "Abilitato",
      entity: "Entità",
      ai_weight: "Peso IA",
      reason: "Motivazione AI",
      your_weight: "Tuo Peso",
      weight_legend: "(0=Ignora, 5=Essenziale)",
    } : {
      title: "HASS AI Control Panel",
      description: "Analyze your entities, teach the AI, and customize weights to optimize your smart home.",
      scan_button: "Start New Scan",
      scanning_button: "Scanning...",
      enabled: "Enabled",
      entity: "Entity",
      ai_weight: "AI Weight",
      reason: "AI Reason",
      your_weight: "Your Weight",
      weight_legend: "(0=Ignore, 5=Essential)",
    };

    return html`
      <ha-card .header=${t.title}>
        <div class="card-content">
          <p>${t.description}</p>
          <p class="warning-message">${this.hass.localize('component.hass_ai.panel.llm_warning')}</p>
          <mwc-button raised @click=${this._runScan} .disabled=${this.loading}>
            ${this.loading ? t.scanning_button : t.scan_button}
          </mwc-button>
        </div>

        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>${t.enabled}</th>
                <th>${t.entity}</th>
                <th>${t.ai_weight}</th>
                <th>${t.reason}</th>
                <th>${t.your_weight} <span class="legend">${t.weight_legend}</span></th>
              </tr>
            </thead>
            <tbody>
              ${sortedEntities.map(entity => html`
                <tr>
                  <td>
                    <ha-switch
                      .checked=${this.overrides[entity.entity_id]?.enabled ?? true}
                      data-entity-id=${entity.entity_id}
                      @change=${this._handleToggle}
                    ></ha-switch>
                  </td>
                  <td>${entity.name || entity.entity_id}</td>
                  <td><span class="weight-badge">${entity.overall_weight}</span></td>
                  <td>${entity.overall_reason}</td>
                  <td>
                    <mwc-select
                    .value=${String(this.overrides[entity.entity_id]?.overall_weight ?? entity.overall_weight)}
                    data-entity-id=${entity.entity_id}
                    @selectedIndexChanged=${this._handleWeightChange}
                  >
                    ${[0, 1, 2, 3, 4, 5].map(i => html`
                      <mwc-list-item value="${i}">${i}</mwc-list-item>
                    `)}
                  </mwc-select>
                  </td>
                </tr>
              `)}
            </tbody>
          </table>
        </div>
      </ha-card>

      <ha-card .header=${this.hass.localize('component.hass_ai.panel.ai_log_title')}>
        <div class="card-content log-scroll-container">
          ${this.renderLog()}
        </div>
      </ha-card>
    `;
  }

 renderLog() {
  return html`
    ${Object.values(this.entities).map(entity => html`
      <div class="log-entry">
        <strong>${this.hass.localize('component.hass_ai.panel.ai_log_entity')}: ${entity.entity_id}</strong>
        <pre>${this.hass.localize('component.hass_ai.panel.ai_log_prompt')}: ${entity.prompt}</pre>
        <pre>${this.hass.localize('component.hass_ai.panel.ai_log_response')}: ${entity.response_text}</pre>
      </div>
    `)}
  `;
}

  static get styles() {
    return css`
      .table-container {
        width: 100%;
        overflow: auto;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 16px;
      }
      th, td {
        padding: 12px 16px;
        border-bottom: 1px solid var(--divider-color);
        text-align: left;
        vertical-align: top;
      }
      th {
        font-weight: bold;
        background-color: var(--table-header-background-color, var(--primary-background-color));
      }
      mwc-select {
  width: 90px;
}
      .legend {
        font-size: 0.9em;
        font-weight: normal;
        color: var(--secondary-text-color);
      }
      .weight-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 12px;
        background-color: var(--primary-color);
        color: var(--text-primary-color);
        font-weight: bold;
      }
      .log-scroll-container {
        max-height: 200px; /* Adjust as needed */
        overflow-y: auto;
        border: 1px solid var(--divider-color);
        padding: 8px;
        background-color: var(--card-background-color);
      }
      .log-entry {
        margin-bottom: 10px;
        padding-bottom: 10px;
        border-bottom: 1px dashed var(--divider-color);
      }
      .log-entry:last-child {
        border-bottom: none;
        margin-bottom: 0;
        padding-bottom: 0;
      }
      .log-entry pre {
        white-space: pre-wrap;
        word-break: break-all;
        background-color: var(--code-background-color);
        padding: 5px;
        border-radius: 4px;
        font-size: 0.85em;
      }
    `;
  }
}

customElements.define("hass-ai-panel", HassAiPanel);
