const LitElement = Object.getPrototypeOf(
  customElements.get("ha-panel-lovelace")
);
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
    };
  }

  constructor() {
    super();
    this.entities = {};
    this.loading = false;
    this.overrides = {};
    this.saveTimeout = null;
  }

  connectedCallback() {
    super.connectedCallback();
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
    const entityId = ev.target.dataset.entityId;
    const weight = parseInt(ev.target.value, 10);
    if (!this.overrides[entityId]) {
        this.overrides[entityId] = {};
    }
    this.overrides[entityId].weight = weight;
    this._debouncedSave();
  }

  _debouncedSave() {
      clearTimeout(this.saveTimeout);
      this.saveTimeout = setTimeout(() => {
          this.hass.callWS({ type: "hass_ai/save_overrides", overrides: this.overrides });
      }, 1000);
  }

  render() {
    const sortedEntities = Object.values(this.entities).sort((a, b) =>
      a.name.localeCompare(b.name)
    );

    return html`
      <ha-card header="HASS AI Entity Control Panel">
        <div class="card-content">
          <p>
            Here you can see the analysis of your entities. The AI provides a
            baseline weight, and you have the final say. Disable entities you
            want the AI to ignore, and adjust weights for those you want to
            prioritize differently.
          </p>
          <mwc-button raised @click=${this._runScan} .disabled=${this.loading}>
            ${this.loading ? "Scanning..." : "Start New Scan"}
          </mwc-button>
        </div>

        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Enabled</th>
                <th>Entity</th>
                <th>AI Weight</th>
                <th>Reason</th>
                <th>Your Weight</th>
              </tr>
            </thead>
            <tbody>
              ${sortedEntities.map(
                (entity) => html`
                  <tr>
                    <td>
                      <ha-switch
                        .checked=${this.overrides[entity.entity_id]?.enabled ?? true}
                        data-entity-id=${entity.entity_id}
                        @change=${this._handleToggle}
                      ></ha-switch>
                    </td>
                    <td>${entity.name}</td>
                    <td>${entity.weight}</td>
                    <td>${entity.reason}</td>
                    <td>
                      <ha-select
                        .value=${this.overrides[entity.entity_id]?.weight ?? entity.weight}
                        data-entity-id=${entity.entity_id}
                        @selected=${this._handleWeightChange}
                      >
                        <mwc-list-item value="1">1</mwc-list-item>
                        <mwc-list-item value="2">2</mwc-list-item>
                        <mwc-list-item value="3">3</mwc-list-item>
                        <mwc-list-item value="4">4</mwc-list-item>
                        <mwc-list-item value="5">5</mwc-list-item>
                      </ha-select>
                    </td>
                  </tr>
                `
              )}
            </tbody>
          </table>
        </div>
      </ha-card>
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
      }
      th, td {
        padding: 8px 12px;
        border-bottom: 1px solid var(--divider-color);
        text-align: left;
      }
      th {
        font-weight: bold;
      }
      ha-select {
        width: 80px;
      }
    `;
  }
}

customElements.define("hass-ai-panel", HassAiPanel);