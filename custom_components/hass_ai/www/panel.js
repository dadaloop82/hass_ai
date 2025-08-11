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
    this.scanProgress = {
      show: false,
      message: '',
      currentBatch: 0,
      totalBatches: 0,
      entitiesProcessed: 0,
      totalEntities: 0,
      isComplete: false,
      status: 'idle' // 'idle', 'requesting', 'processing', 'complete'
    };
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
    
    // Initialize progress tracking
    this.scanProgress = {
      show: true,
      message: '🚀 Avvio scansione...',
      currentBatch: 0,
      totalBatches: 0,
      entitiesProcessed: 0,
      totalEntities: 0,
      isComplete: false,
      status: 'idle'
    };
    this.requestUpdate();

    await this.hass.connection.subscribeMessage(
      (message) => this._handleScanUpdate(message),
      { type: "hass_ai/scan_entities" }
    );
  }


  _handleScanUpdate(message) {
    if (message.type === "entity_result") {
      const entity = message.result;
      this.entities[entity.entity_id] = entity;
      
      // Update entities processed count
      this.scanProgress.entitiesProcessed = Object.keys(this.entities).length;
      this.requestUpdate("entities");
    }
    if (message.type === "scan_progress") {
      // Update detailed progress info
      this.scanProgress = {
        ...this.scanProgress,
        show: true,
        message: message.data.message,
        currentBatch: message.data.batch_number,
        status: message.data.message.includes('📤') ? 'requesting' : 'processing'
      };
      this.requestUpdate();
    }
    if (message.type === "batch_info") {
      // Update batch progress info and calculate totals
      this.scanProgress = {
        ...this.scanProgress,
        currentBatch: message.data.batch_number,
        batchSize: message.data.batch_size,
        entitiesInBatch: message.data.entities_in_batch,
        remainingEntities: message.data.remaining_entities,
        retryAttempt: message.data.retry_attempt,
        totalEntities: message.data.entities_in_batch + message.data.remaining_entities,
        show: true
      };
      this.requestUpdate();
    }
    if (message.type === "batch_size_reduced") {
      // Show batch size reduction notification
      this._showBatchReductionNotification(message.data);
    }
    if (message.type === "token_limit_exceeded") {
      this.loading = false;
      
      // Show token limit error dialog
      this._showTokenLimitDialog(message.data);
    }
    if (message.type === "scan_complete") {
      this.loading = false;
      this.scanProgress = {
        ...this.scanProgress,
        show: true,
        isComplete: true,
        status: 'complete',
        message: `🎉 Scansione completata! Analizzate ${Object.keys(this.entities).length} entità`
      };
      
      // Hide completion message after 5 seconds
      setTimeout(() => {
        this.scanProgress.show = false;
        this.requestUpdate();
      }, 5000);
      
      this.requestUpdate();
    }
  }

  _showBatchReductionNotification(data) {
    // Use a simpler approach for notifications
    console.log(`🔄 Batch Size Reduced: ${data.old_size} → ${data.new_size} (retry ${data.retry_attempt})`);
    
    // Create a simple toast notification
    const toast = document.createElement('div');
    toast.textContent = `🔄 Batch size reduced: ${data.old_size} → ${data.new_size} entities (retry ${data.retry_attempt})`;
    toast.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #ff9800;
      color: white;
      padding: 12px 16px;
      border-radius: 6px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.2);
      z-index: 9999;
      font-size: 14px;
      max-width: 300px;
      transform: translateX(100%);
      transition: transform 0.3s ease-out;
    `;
    
    document.body.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
      toast.style.transform = 'translateX(0)';
    }, 100);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => {
        if (toast.parentNode) {
          toast.remove();
        }
      }, 300);
    }, 4000);
  }

  _showTokenLimitDialog(data) {
    // Create a simple alert-style dialog instead of complex DOM manipulation
    const message = `🚨 Token Limit Exceeded

Scan stopped at batch ${data.batch}

${data.message}

AI Response:
${data.response}

💡 Quick Solutions:
• Reduce batch size in HASS AI settings (try 5-8 entities)
• Increase max_tokens in your conversation agent
• Use a different conversation agent with higher limits`;

    // Use browser alert for now (more reliable)
    alert(message);
    
    // Also log to console for debugging
    console.log('HASS AI Token Limit:', data);
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

    // Translations based on browser language or HA language
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    const t = isItalian ? {
      title: "Pannello di Controllo HASS AI",
      description: "Analizza le tue entità, insegna all'IA e personalizza i pesi per ottimizzare la tua domotica. L'AI provider è configurato nelle impostazioni dell'integrazione.",
      scan_button: "Avvia Nuova Scansione",
      scanning_button: "Scansione in corso...",
      enabled: "Abilitato",
      entity: "Entità",
      ai_weight: "Peso IA",
      reason: "Motivazione AI",
      your_weight: "Tuo Peso",
      weight_legend: "(0=Ignora, 5=Critico)"
    } : {
      title: "HASS AI Control Panel",
      description: "Analyze your entities, teach the AI, and customize weights to optimize your smart home. AI provider is configured in integration settings.",
      scan_button: "Start New Scan",
      scanning_button: "Scanning...",
      enabled: "Enabled",
      entity: "Entity",
      ai_weight: "AI Weight",
      reason: "AI Reason",
      your_weight: "Your Weight",
      weight_legend: "(0=Ignore, 5=Critical)"
    };

    return html`
      <ha-card .header=${t.title}>
        <div class="card-content">
          <p>${t.description}</p>
          <ha-button raised @click=${this._runScan} .disabled=${this.loading}>
            ${this.loading ? t.scanning_button : t.scan_button}
          </ha-button>
          
          ${this.scanProgress.show ? html`
            <div class="progress-section">
              <div class="progress-message">
                ${this.scanProgress.message}
              </div>
              
              ${this.scanProgress.totalEntities > 0 ? html`
                <div class="progress-bar-container">
                  <div class="progress-bar">
                    <div class="progress-fill" 
                         style="width: ${Math.round((this.scanProgress.entitiesProcessed / this.scanProgress.totalEntities) * 100)}%">
                    </div>
                  </div>
                  <div class="progress-text">
                    ${this.scanProgress.entitiesProcessed} / ${this.scanProgress.totalEntities} entità
                    ${this.scanProgress.currentBatch > 0 ? `(Batch ${this.scanProgress.currentBatch})` : ''}
                  </div>
                </div>
              ` : ''}
              
              ${this.scanProgress.status === 'requesting' ? html`
                <div class="status-indicator">🔄 Invio richiesta...</div>
              ` : ''}
              
              ${this.scanProgress.status === 'processing' ? html`
                <div class="status-indicator">⚙️ Elaborazione risposta...</div>
              ` : ''}
              
              ${this.scanProgress.isComplete ? html`
                <div class="completion-message">
                  <strong>✅ Scansione terminata!</strong><br>
                  Ecco i risultati dell'analisi delle tue entità:
                </div>
              ` : ''}
            </div>
          ` : ''}
        </div>

        ${Object.keys(this.entities).length > 0 ? html`
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
                    <td>
                      <div class="entity-info">
                        <strong>${entity.entity_id}</strong>
                        <br><small>${entity.name || entity.entity_id.split('.')[1]}</small>
                      </div>
                    </td>
                    <td><span class="weight-badge weight-${entity.overall_weight}">${entity.overall_weight}</span></td>
                    <td><span class="reason-text">${entity.overall_reason}</span></td>
                    <td>
                      <ha-select
                        .value=${String(this.overrides[entity.entity_id]?.overall_weight ?? entity.overall_weight)}
                        data-entity-id=${entity.entity_id}
                        @selectionChanged=${this._handleWeightChange}
                      >
                        ${[0, 1, 2, 3, 4, 5].map(i => html`
                          <ha-list-item value="${i}">${i}</ha-list-item>
                        `)}
                      </ha-select>
                    </td>
                  </tr>
                `)}
              </tbody>
            </table>
          </div>
        ` : ''}
      </ha-card>
    `;
  }

  renderLog(t) {
    const hasEntries = Object.keys(this.entities).length > 0;
    
    if (!hasEntries) {
      return html`<p class="no-data">${t.no_scan}</p>`;
    }

  static get styles() {
    return css`
      @keyframes slideIn {
        from {
          transform: translateX(100%);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }
      
      .progress-section {
        background-color: var(--info-background-color, rgba(33, 150, 243, 0.1));
        border-radius: 8px;
        padding: 16px;
        margin: 16px 0;
        border-left: 4px solid var(--info-color, #2196f3);
      }
      
      .progress-message {
        font-size: 16px;
        font-weight: 500;
        color: var(--primary-text-color);
        margin-bottom: 12px;
      }
      
      .progress-bar-container {
        margin: 12px 0;
      }
      
      .progress-bar {
        width: 100%;
        height: 8px;
        background-color: var(--divider-color, #e0e0e0);
        border-radius: 4px;
        overflow: hidden;
        margin-bottom: 8px;
      }
      
      .progress-fill {
        height: 100%;
        background-color: var(--info-color, #2196f3);
        transition: width 0.3s ease;
        border-radius: 4px;
      }
      
      .progress-text {
        font-size: 14px;
        color: var(--secondary-text-color);
        text-align: center;
      }
      
      .status-indicator {
        font-size: 14px;
        color: var(--info-color, #2196f3);
        margin-top: 8px;
        animation: pulse 2s infinite;
      }
      
      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
      }
      
      .completion-message {
        background-color: var(--success-color, #4caf50);
        color: white;
        padding: 12px;
        border-radius: 6px;
        margin-top: 12px;
        text-align: center;
      }
      
      .warning-message {
        color: var(--warning-color, #ff9800);
        font-style: italic;
        margin: 8px 0;
        padding: 12px;
        background-color: var(--warning-background-color, rgba(255, 152, 0, 0.1));
        border-radius: 4px;
        border-left: 4px solid var(--warning-color, #ff9800);
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .table-container {
        width: 100%;
        overflow: auto;
        margin-top: 16px;
      }
      table {
        width: 100%;
        border-collapse: collapse;
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
        position: sticky;
        top: 0;
        z-index: 1;
      }
      .entity-info strong {
        font-family: monospace;
        font-size: 0.9em;
      }
      .entity-info small {
        color: var(--secondary-text-color);
      }
      .reason-text {
        font-style: italic;
        color: var(--secondary-text-color);
      }
      ha-select {
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
        font-weight: bold;
        min-width: 20px;
        text-align: center;
        color: white;
      }
      .weight-0 { background-color: #9e9e9e; }  /* Grey - Ignore */
      .weight-1 { background-color: #f44336; }  /* Red - Very Low */
      .weight-2 { background-color: #ff9800; }  /* Orange - Low */
      .weight-3 { background-color: #ffc107; }  /* Amber - Medium */
      .weight-4 { background-color: #4caf50; }  /* Green - High */
      .weight-5 { background-color: #2196f3; }  /* Blue - Critical */
      .log-scroll-container {
        max-height: 400px;
        overflow-y: auto;
        border: 1px solid var(--divider-color);
        padding: 8px;
        background-color: var(--card-background-color);
      }
      .log-stats {
        background-color: var(--primary-background-color);
        padding: 8px;
        border-radius: 4px;
        margin-bottom: 12px;
      }
      .log-entry {
        margin-bottom: 12px;
        padding: 8px;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        background-color: var(--card-background-color);
      }
      .log-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
      }
      .log-header code {
        background-color: var(--code-background-color, #f5f5f5);
        padding: 2px 4px;
        border-radius: 2px;
        font-family: monospace;
      }
      .log-reason {
        margin: 4px 0;
        color: var(--secondary-text-color);
      }
      .log-meta {
        margin-top: 4px;
        color: var(--disabled-text-color);
        font-size: 0.85em;
      }
      .log-truncated {
        text-align: center;
        padding: 8px;
        color: var(--secondary-text-color);
        font-style: italic;
      }
      .no-data {
        text-align: center;
        color: var(--secondary-text-color);
        font-style: italic;
        padding: 20px;
      }
      ha-card {
        margin-bottom: 16px;
      }
      ha-button {
        margin: 8px 0;
      }
      ha-icon {
        --mdc-icon-size: 20px;
      }
      .debug-section {
        margin-top: 24px;
        padding: 16px;
        border: 1px solid var(--primary-color);
        border-radius: 8px;
        background: var(--card-background-color);
        font-family: monospace;
      }
      .debug-section h3 {
        margin: 0 0 12px 0;
        color: var(--primary-color);
      }
      .debug-provider {
        margin-bottom: 8px;
        font-weight: bold;
      }
      .debug-prompt, .debug-response {
        margin-bottom: 12px;
      }
      .debug-prompt pre, .debug-response pre {
        background: var(--primary-background-color);
        padding: 8px;
        border-radius: 4px;
        white-space: pre-wrap;
        word-wrap: break-word;
        max-height: 200px;
        overflow-y: auto;
        font-size: 12px;
      }
    `;
  }
}

customElements.define("hass-ai-panel", HassAiPanel);
