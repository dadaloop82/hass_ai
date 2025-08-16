// HASS AI Panel v1.9.38.1 - Updated 2025-08-16T21:00:00Z - ADDED INPUT_TEXT OPTION FOR ALERT DISPLAY
// Features: Auto-save correlations + Load correlations on startup + Progress tracking + ALERTS Category + Real-time Token Tracking + Enhanced Analysis + Alert Thresholds + Stop Operation + Intelligent Alert Notifications + Input Text Mode
// Force reload timestamp: 1723590000000
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
      minWeight: { state: true },
      searchTerm: { state: true },
      categoryFilter: { state: true },
      tokenStats: { state: true },
      alertThresholds: { state: true },
      isOperationActive: { state: true },
    };
  }

  constructor() {
    super();
    this.entities = {};
    this.loading = false;
    this.overrides = {};
    this.saveTimeout = null;
    this.language = 'en'; // Default language
    this.minWeight = 3; // Filter: minimum weight to show entities (default 3)
    this.searchTerm = ''; // Search filter
    this.categoryFilter = 'ALL'; // Category filter: ALL, DATA, CONTROL, ALERTS, ENHANCED, ENHANCED
    this.correlations = {}; // Store correlations for each entity
    this.isOperationActive = false; // Track if any operation is active
    this.currentOperation = null; // Track current operation type
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
    this.tokenStats = {
      totalTokens: 0,
      currentBatchTokens: 0,
      averageTokensPerEntity: 0,
      estimatedCost: 0 // Rough cost estimation
    };
    this.lastScanInfo = {
      timestamp: null,
      entityCount: 0
    };
    this.alertThresholds = {}; // User-customizable alert thresholds
    this.alertStatus = {
      monitoring_enabled: false,
      total_monitored: 0,
      active_alerts: {},
      notification_service: 'notify.notify',
      use_input_text: false,
      input_text_entity: 'input_text.hass_ai_alerts',
      input_text_exists: false
    };
    this.showAlertConfig = false; // Toggle alert configuration panel
  }

  connectedCallback() {
    super.connectedCallback();
    console.log('🚀 HASS AI Panel v1.9.37 loaded - Fixed entity categorization! All entities now get proper multiple categories instead of UNKNOWN');
    this.language = this.hass.language || 'en';
    this._loadMinWeightFilter();
    this._loadCategoryFilter();
    this._loadOverrides();
    this._loadAiResults();
    this._loadCorrelations();
    this._loadAlertThresholds();
    this._loadAlertStatus();
  }

  async _saveAiResults() {
    try {
      await this.hass.callWS({ 
        type: "hass_ai/save_ai_results", 
        results: this.entities,
        timestamp: new Date().toISOString(),
        total_entities: Object.keys(this.entities).length
      });
    } catch (error) {
      const isItalian = (this.hass.language || navigator.language).startsWith('it');
      console.error(isItalian ? 'Impossibile salvare i risultati AI:' : 'Failed to save AI results:', error);
    }
  }

  async _saveCorrelations() {
    try {
      await this.hass.callWS({ 
        type: "hass_ai/save_correlations", 
        correlations: this.correlations,
        timestamp: new Date().toISOString(),
        total_entities: Object.keys(this.correlations).length
      });
    } catch (error) {
      const isItalian = (this.hass.language || navigator.language).startsWith('it');
      console.error(isItalian ? 'Impossibile salvare le correlazioni:' : 'Failed to save correlations:', error);
    }
  }

  async _loadOverrides() {
    this.overrides = await this.hass.callWS({ type: "hass_ai/load_overrides" });
  }

  async _loadAlertThresholds() {
    try {
      const response = await this.hass.callWS({ type: "hass_ai/load_alert_thresholds" });
      this.alertThresholds = response.thresholds || {};
    } catch (error) {
      console.error('Failed to load alert thresholds:', error);
      this.alertThresholds = {};
    }
  }

  async _saveAlertThreshold(entityId, threshold) {
    try {
      await this.hass.callWS({ 
        type: "hass_ai/save_alert_threshold",
        entity_id: entityId,
        threshold: threshold
      });
      
      // Update local cache
      this.alertThresholds[entityId] = {
        level: threshold,
        customized: true,
        updated_at: new Date().toISOString()
      };
      
      this.requestUpdate();
    } catch (error) {
      console.error('Failed to save alert threshold:', error);
    }
  }

  _getAlertThreshold(entityId) {
    return this.alertThresholds[entityId] || {
      level: 'MEDIUM',
      customized: false
    };
  }

  async _loadAlertStatus() {
    try {
      const response = await this.hass.callWS({ type: "hass_ai/get_alert_status" });
      this.alertStatus = response;
      this.requestUpdate();
    } catch (error) {
      console.error('Failed to load alert status:', error);
    }
  }

  async _configureAlertService(config = {}) {
    try {
      const payload = {
        type: "hass_ai/configure_alert_service"
      };
      
      // Add configuration options
      if (config.notification_service) {
        payload.notification_service = config.notification_service;
      }
      if (config.use_input_text !== undefined) {
        payload.use_input_text = config.use_input_text;
      }
      if (config.input_text_entity) {
        payload.input_text_entity = config.input_text_entity;
      }
      if (config.entity_thresholds) {
        payload.entity_thresholds = config.entity_thresholds;
      }
      
      await this.hass.callWS(payload);
      
      // Update local status
      Object.assign(this.alertStatus, config);
      const isItalian = (this.hass.language || navigator.language).startsWith('it');
      this._showSimpleNotification(
        isItalian ? '🔔 Configurazione alert aggiornata con successo' : '🔔 Alert configuration updated successfully', 
        'success'
      );
      this.requestUpdate();
    } catch (error) {
      const isItalian = (this.hass.language || navigator.language).startsWith('it');
      console.error(isItalian ? 'Impossibile configurare il servizio alert:' : 'Failed to configure alert service:', error);
      this._showSimpleNotification(
        isItalian ? '❌ Impossibile configurare il servizio alert' : '❌ Failed to configure alert service', 
        'error'
      );
    }
  }

  _getAvailableNotificationServices() {
    // Get available notification services from Home Assistant
    const services = this.hass.services?.notify || {};
    const notificationServices = [];
    
    // Add default notify service
    notificationServices.push({
      id: 'notify.notify',
      name: 'Default Notification Service'
    });
    
    // Add specific notification services
    Object.keys(services).forEach(service => {
      if (service !== 'notify') {
        notificationServices.push({
          id: `notify.${service}`,
          name: service.charAt(0).toUpperCase() + service.slice(1)
        });
      }
    });
    
    return notificationServices;
  }

  _getAlertLevelConfig(level) {
    const configs = {
      'WARNING': {
        color: '#ff9800',
        icon: '⚠️',
        description: 'Warning - Monitor situation'
      },
      'ALERT': {
        color: '#f44336',
        icon: '🚨',
        description: 'Alert - Requires attention'
      },
      'CRITICAL': {
        color: '#d32f2f',
        icon: '🔥',
        description: 'Critical - Immediate action required'
      }
    };
    return configs[level] || configs['WARNING'];
  }

  _generateAlertMessageExample() {
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    
    // Trova entità reali per l'esempio
    const alertEntities = Object.entries(this.entities).filter(([entityId, entity]) => 
      entity.categories && entity.categories.includes('ALERTS')
    );
    
    if (alertEntities.length > 0) {
      // Usa entità reali per l'esempio
      const sampleEntity = alertEntities[0];
      const entityId = sampleEntity[0];
      const state = this.hass.states[entityId];
      const friendlyName = state?.attributes?.friendly_name || entityId;
      const currentValue = state?.state || 'N/A';
      const unit = state?.attributes?.unit_of_measurement || '';
      
      if (isItalian) {
        return `🚨 Ehi, c'è qualcosa che non va! Ho controllato ${friendlyName} e il valore attuale è ${currentValue}${unit}. 
        
Potrebbe essere il momento di dare un'occhiata... Non è urgentissimo, ma meglio non aspettare troppo! 😊

Comunque tranquillo, ti tengo d'occhio tutto io! 👀`;
      } else {
        return `🚨 Hey, something's up! I checked ${friendlyName} and the current value is ${currentValue}${unit}.
        
Might be time to take a look... Not super urgent, but better not wait too long! 😊

Don't worry though, I'm keeping an eye on everything for you! 👀`;
      }
    } else {
      // Esempio generico se non ci sono entità
      if (isItalian) {
        return `� Ehi, ho notato qualcosa di strano! La batteria del sensore in cucina è al 5% - forse è ora di cambiarla? 🔋
        
E poi... la temperatura in salotto è a 32°C, fa un po' caldino, no? 🌡️

Niente di drammatico, ma meglio dare un'occhiata quando hai un minuto! 😉`;
      } else {
        return `🚨 Hey, I spotted something! The kitchen sensor battery is at 5% - maybe time for a change? 🔋
        
Also... living room temperature is at 32°C, getting a bit toasty, isn't it? 🌡️

Nothing dramatic, but worth checking when you have a minute! 😉`;
      }
    }
  }

  _getAlertThresholdConfig(level) {
    const configs = {
      'MEDIUM': {
        color: '#FFA500',
        icon: 'mdi:alert-circle-outline',
        description: 'Medium priority alert'
      },
      'SEVERE': {
        color: '#FF6B6B',
        icon: 'mdi:alert',
        description: 'Severe alert - requires attention'
      },
      'CRITICAL': {
        color: '#DC143C',
        icon: 'mdi:alert-octagon',
        description: 'Critical alert - immediate action required'
      }
    };
    return configs[level] || configs['MEDIUM'];
  }

  async _toggleAlertMode(useInputText) {
    await this._configureAlertService({
      use_input_text: useInputText
    });
    
    // Reload status to update UI
    await this._loadAlertStatus();
  }

  async _toggleAlertMonitoring() {
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    try {
      await this._configureAlertService({
        monitoring_enabled: !this.alertStatus.monitoring_enabled
      });
      
      const status = this.alertStatus.monitoring_enabled ? 
        (isItalian ? 'attivato' : 'enabled') : 
        (isItalian ? 'disattivato' : 'disabled');
      
      this._showSimpleNotification(
        isItalian ? `🔔 Monitoraggio alert ${status}` : `🔔 Alert monitoring ${status}`, 
        'success'
      );
      
      // Reload status to update UI
      await this._loadAlertStatus();
    } catch (error) {
      console.error(isItalian ? 'Errore nel toggle monitoraggio:' : 'Error toggling monitoring:', error);
      this._showSimpleNotification(
        isItalian ? '❌ Errore nel cambiare stato monitoraggio' : '❌ Error changing monitoring status', 
        'error'
      );
    }
  }

  async _createInputTextEntity() {
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    try {
      // Crea l'entità input_text tramite Home Assistant
      await this.hass.callService('input_text', 'reload');
      
      // Prova a creare l'entità usando l'helper input_text
      const entityConfig = {
        name: 'HASS AI Alerts',
        min: 0,
        max: 1000,
        icon: 'mdi:alert-circle',
        initial: isItalian ? 'Nessun alert attivo' : 'No active alerts'
      };
      
      // Usa il servizio per creare l'helper (se disponibile)
      try {
        await this.hass.callService('input_text', 'set_value', {
          entity_id: 'input_text.hass_ai_alerts',
          value: entityConfig.initial
        });
        
        // Se il servizio funziona, l'entità esiste già
        this._showSimpleNotification(
          isItalian ? '✅ Entità input_text già esistente!' : '✅ Input_text entity already exists!', 
          'success'
        );
      } catch (setError) {
        // L'entità non esiste, proviamo a crearla tramite storage
        try {
          await this.hass.callWS({
            type: 'config/input_text/create',
            name: 'HASS AI Alerts',
            icon: 'mdi:alert-circle',
            min: 0,
            max: 1000,
            initial: entityConfig.initial
          });
          
          this._showSimpleNotification(
            isItalian ? '✅ Entità input_text creata con successo!' : '✅ Input_text entity created successfully!', 
            'success'
          );
          
          // Configura automaticamente l'entità creata
          await this._configureAlertService({
            input_text_entity: 'input_text.hass_ai_alerts',
            use_input_text: true
          });
          
        } catch (createError) {
          console.error('Failed to create input_text entity:', createError);
          this._showSimpleNotification(
            isItalian ? '⚠️ Non posso creare l\'entità automaticamente. Usa la configurazione manuale.' : '⚠️ Cannot create entity automatically. Use manual configuration.', 
            'warning'
          );
        }
      }
      
      // Ricarica lo status per aggiornare l'UI
      setTimeout(() => this._loadAlertStatus(), 1000);
      
    } catch (error) {
      console.error('Error in createInputTextEntity:', error);
      this._showSimpleNotification(
        isItalian ? '❌ Errore nella creazione dell\'entità' : '❌ Error creating entity', 
        'error'
      );
    }
  }

  async _updateInputTextEntity(entityId) {
    await this._configureAlertService({
      input_text_entity: entityId
    });
    
    // Reload status to check if entity exists
    await this._loadAlertStatus();
  }

  async _clearInputTextValue() {
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    if (!this.alertStatus.input_text_entity) return;
    
    try {
      await this.hass.callService('input_text', 'set_value', {
        entity_id: this.alertStatus.input_text_entity,
        value: isItalian ? 'Nessun alert attivo' : 'No active alerts'
      });
      
      this._showMessage(
        isItalian ? '✅ Alert cancellato' : '✅ Alert cleared',
        'success'
      );
      
      // Force update of the UI
      this.requestUpdate();
    } catch (error) {
      console.error('Error clearing input_text value:', error);
      this._showMessage(
        isItalian ? '❌ Errore nella cancellazione' : '❌ Error clearing alert',
        'error'
      );
    }
  }

  async _loadCorrelations() {
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    try {
      const correlations = await this.hass.callWS({ type: "hass_ai/load_correlations" });
      if (correlations && Object.keys(correlations).length > 0) {
        this.correlations = correlations;
        console.log(isItalian ? 
          `📂 Caricate ${Object.keys(correlations).length} correlazioni salvate` : 
          `📂 Loaded ${Object.keys(correlations).length} saved correlations`
        );
        this.requestUpdate();
      }
    } catch (error) {
      console.error(isItalian ? 'Errore durante il caricamento delle correlazioni:' : 'Failed to load correlations:', error);
    }
  }

  async _loadAiResults() {
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    try {
      const response = await this.hass.callWS({ type: "hass_ai/load_ai_results" });
      
      // Check if response contains metadata
      if (response && typeof response === 'object') {
        // If it's the new format with metadata
        if (response.results) {
          this.entities = response.results;
          this.lastScanInfo = {
            timestamp: response.last_scan_timestamp,
            entityCount: response.total_entities || Object.keys(response.results).length
          };
        } else {
          // Old format - just the results
          this.entities = response;
          this.lastScanInfo = {
            timestamp: null,
            entityCount: Object.keys(response).length
          };
        }
        
        if (Object.keys(this.entities).length > 0) {
          // Migrate old format categories to new array format
          Object.keys(this.entities).forEach(entityId => {
            const entity = this.entities[entityId];
            if (entity.category && typeof entity.category === 'string') {
              // Convert single category string to array
              entity.category = [entity.category];
              console.log(`🔄 Migrated ${entityId} category to array format`);
            } else if (!entity.category || !Array.isArray(entity.category)) {
              // Ensure all entities have array categories
              entity.category = ['DATA'];
              console.log(`🔄 Set default category for ${entityId}`);
            }
          });
          
          console.log(`📂 ${isItalian ? 'Caricati' : 'Loaded'} ${Object.keys(this.entities).length} ${isItalian ? 'risultati di analisi AI salvati' : 'saved AI analysis results'}`);
          this.requestUpdate();
          
          // Update alert monitoring with current filter settings
          await this._updateFilteredAlerts();
        }
      }
    } catch (error) {
      console.log(isItalian ? 'Nessun risultato AI precedente trovato:' : 'No previous AI results found:', error);
    }
  }

  async _loadMinWeightFilter() {
    // Load minimum weight filter from localStorage
    const saved = localStorage.getItem('hass_ai_min_weight');
    this.minWeight = saved ? parseInt(saved) : 3; // Default to 3
  }

  async _loadCategoryFilter() {
    // Load category filter from localStorage
    const saved = localStorage.getItem('hass_ai_category_filter');
    this.categoryFilter = saved || 'ALL'; // Default to ALL
  }

  async _saveMinWeightFilter(value) {
    // Save minimum weight filter to localStorage
    this.minWeight = parseInt(value);
    localStorage.setItem('hass_ai_min_weight', this.minWeight.toString());
    this.requestUpdate();
    
    // Update alert monitoring with filtered entities in real-time
    await this._updateFilteredAlerts();
  }

  async _saveCategoryFilter(value) {
    // Save category filter to localStorage
    this.categoryFilter = value;
    localStorage.setItem('hass_ai_category_filter', this.categoryFilter);
    this.requestUpdate();
    
    // Update alert monitoring with filtered entities in real-time
    await this._updateFilteredAlerts();
  }

  _getFilteredEntities() {
    // Filter entities by minimum weight, search term, and category
    return Object.entries(this.entities).filter(([entityId, entity]) => {
      const weight = this.overrides[entityId]?.overall_weight ?? entity.overall_weight;
      const matchesWeight = weight >= this.minWeight;
      
      // Search in entity_id and name
      const matchesSearch = this.searchTerm === '' || 
        entityId.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        (entity.name && entity.name.toLowerCase().includes(this.searchTerm.toLowerCase()));
      
      // Category filter - handle both array and string categories
      const entityCategories = Array.isArray(entity.category) ? entity.category : [entity.category];
      const matchesCategory = this.categoryFilter === 'ALL' || entityCategories.includes(this.categoryFilter);
      
      return matchesWeight && matchesSearch && matchesCategory;
    }).map(([entityId, entity]) => entity); // Return just the entity objects, not tuples
  }

  async _updateFilteredAlerts() {
    // Update alert monitoring with currently filtered entities in real-time
    try {
      await this.hass.callWS({
        type: "hass_ai/update_filtered_alerts",
        min_weight: this.minWeight,
        category_filter: this.categoryFilter
      });
      
      // Reload alert status to reflect changes
      await this._loadAlertStatus();
      
    } catch (error) {
      console.error('Failed to update filtered alerts:', error);
    }
  }

  _isEntityUnavailable(entityId) {
    // Check if entity is unknown, unavailable, or has no meaningful state
    const entityState = this.hass.states[entityId];
    if (!entityState) return true;
    
    const unavailableStates = ['unknown', 'unavailable', 'none', '', null, undefined];
    return unavailableStates.includes(entityState.state) || 
           unavailableStates.includes(entityState.state?.toLowerCase());
  }

  _getUnevaluatedEntities() {
    // Get all current HA entities
    const allHAEntities = this.hass.states ? Object.keys(this.hass.states) : [];
    
    // Filter out hass_ai entities and system entities, and entities already evaluated
    return allHAEntities.filter(entityId => {
      const isSystemEntity = entityId.startsWith('hass_ai.') || 
                             entityId.includes('persistent_notification') ||
                             entityId.includes('system_log');
      const isAlreadyEvaluated = this.entities[entityId];
      
      return !isSystemEntity && !isAlreadyEvaluated;
    });
  }

  _getScanButtonText() {
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    const unevaluatedCount = this._getUnevaluatedEntities().length;
    
    if (this.loading || this.scanProgress.show) {
      return isItalian ? "Scansione in corso..." : "Scanning...";
    }
    
    if (unevaluatedCount > 0 && Object.keys(this.entities).length > 0) {
      return isItalian ? 
        `🔍 Scansiona ${unevaluatedCount} entità nuove` :
        `🔍 Scan ${unevaluatedCount} new entities`;
    }
    
    return isItalian ? 
      `🚀 Avvia Analisi Completa` : 
      `🚀 Start Complete Analysis`;
  }
  
  async _runScan() {
    this.loading = true;
    this.isOperationActive = true;
    this.currentOperation = (this.hass.language || navigator.language).startsWith('it') ? 'Scansione entità' : 'Entity scan';
    
    // Check if we should scan only new entities or all entities
    const unevaluatedEntities = this._getUnevaluatedEntities();
    const shouldScanOnlyNew = unevaluatedEntities.length > 0 && Object.keys(this.entities).length > 0;
    
    if (!shouldScanOnlyNew) {
      // Full scan - reset entities
      this.entities = {};
    }
    
    // Initialize progress tracking
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    this.scanProgress = {
      show: true,
      message: shouldScanOnlyNew ? 
        (isItalian ? '🔍 Scansione entità nuove...' : '🔍 Scanning new entities...') :
        (isItalian ? '🚀 Avvio scansione completa...' : '🚀 Starting full scan...'),
      currentBatch: 0,
      totalBatches: 0,
      entitiesProcessed: 0,
      totalEntities: 0,
      isComplete: false,
      status: 'idle'
    };
    
    // Reset token statistics for new scan
    this.tokenStats = {
      totalTokens: 0,
      currentBatchTokens: 0,
      averageTokensPerEntity: 0,
      estimatedCost: 0
    };
    
    this.requestUpdate();

    await this.hass.connection.subscribeMessage(
      (message) => this._handleScanUpdate(message),
      { 
        type: "hass_ai/scan_entities",
        language: this.hass.language || navigator.language || 'en',
        new_entities_only: shouldScanOnlyNew,
        existing_entities: shouldScanOnlyNew ? Object.keys(this.entities) : [],
        analysis_type: 'comprehensive'
      }
    );
  }

  async _findCorrelations() {
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    const filteredEntities = this._getFilteredEntities();
    
    if (filteredEntities.length === 0) {
      this._showSimpleNotification(
        isItalian ? '❌ Nessuna entità da analizzare con il filtro attuale' : '❌ No entities to analyze with current filter',
        'error'
      );
      return;
    }

    // Ask user confirmation with filter explanation
    const confirmed = confirm(
      isItalian ? 
        `🔍 Ricerca Correlazioni AI\n\n` +
        `Verranno analizzate ${filteredEntities.length} entità con peso ≥ ${this.minWeight}.\n\n` +
        `💡 Suggerimento: Usa il "Peso Minimo" nel filtro sopra per escludere entità di poco valore e concentrare l'analisi su quelle più importanti.\n\n` +
        `Nota: La ricerca testuale non influisce sulla selezione delle entità.\n\n` +
        `Continuare con l'analisi? (potrebbe richiedere alcuni minuti)` :
        `🔍 AI Correlation Analysis\n\n` +
        `Will analyze ${filteredEntities.length} entities with weight ≥ ${this.minWeight}.\n\n` +
        `💡 Tip: Use "Minimum Weight" filter above to exclude low-value entities and focus analysis on important ones.\n\n` +
        `Note: Text search doesn't affect entity selection.\n\n` +
        `Continue with analysis? (may take several minutes)`
    );
    
    if (!confirmed) return;

    this.loading = true;
    this.isOperationActive = true;
    this.currentOperation = isItalian ? 'Ricerca correlazioni' : 'Correlation analysis';
    this._showSimpleNotification(
      isItalian ? '🧠 Ricerca correlazioni in corso...' : '🧠 Finding correlations...',
      'info'
    );

    try {
      await this.hass.connection.subscribeMessage(
        (message) => this._handleCorrelationUpdate(message),
        { 
          type: "hass_ai/find_correlations",
          entities: filteredEntities.map(e => ({
            entity_id: e.entity_id,
            ai_weight: this.overrides[e.entity_id]?.overall_weight ?? e.overall_weight,
            reason: e.overall_reason,
            category: e.category
          })),
          language: this.hass.language || navigator.language || 'en'
        }
      );
    } catch (error) {
      this.loading = false;
      this.isOperationActive = false;
      this.currentOperation = null;
      this._showSimpleNotification(
        isItalian ? '❌ Errore durante la ricerca correlazioni' : '❌ Error finding correlations',
        'error'
      );
    }
  }

  async _stopOperation() {
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    
    if (!this.isOperationActive) {
      this._showSimpleNotification(
        isItalian ? '⚠️ Nessuna operazione in corso' : '⚠️ No operation in progress',
        'warning'
      );
      return;
    }

    const confirmed = confirm(
      isItalian ? 
        `🛑 Fermare l'operazione in corso?\n\n` +
        `Operazione attuale: ${this.currentOperation || 'Sconosciuta'}\n\n` +
        `L'operazione verrà interrotta immediatamente. I dati già elaborati verranno conservati.` :
        `🛑 Stop current operation?\n\n` +
        `Current operation: ${this.currentOperation || 'Unknown'}\n\n` +
        `The operation will be stopped immediately. Already processed data will be kept.`
    );
    
    if (!confirmed) return;

    try {
      // Send stop command to backend
      await this.hass.callWS({
        type: "hass_ai/stop_operation"
      });
      
      // Reset frontend state
      this._resetOperationState();
      
      this._showSimpleNotification(
        isItalian ? '🛑 Operazione interrotta' : '🛑 Operation stopped',
        'info'
      );
    } catch (error) {
      console.error('Error stopping operation:', error);
      this._showSimpleNotification(
        isItalian ? '❌ Errore durante l\'interruzione dell\'operazione' : '❌ Error stopping operation',
        'error'
      );
    }
  }

  _resetOperationState() {
    this.isOperationActive = false;
    this.currentOperation = null;
    this.loading = false;
    this.scanProgress = {
      show: false,
      message: '',
      currentBatch: 0,
      totalBatches: 0,
      entitiesProcessed: 0,
      totalEntities: 0,
      isComplete: false,
      status: 'idle'
    };
    this.requestUpdate();
  }

  _handleCorrelationUpdate(message) {
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    
    if (message.type === "correlation_progress") {
      // Update correlation progress
      this.scanProgress = {
        ...this.scanProgress,
        show: true,
        message: message.data.message,
        currentBatch: message.data.current,
        totalEntities: message.data.total,
        entitiesProcessed: message.data.current,
        status: 'processing'
      };
      this.requestUpdate();
    }
    
    if (message.type === "correlation_result") {
      const { entity_id, correlations } = message.result;
      this.correlations[entity_id] = correlations;
      
      // Auto-save correlations as they come in
      this._saveCorrelations();
      
      this.requestUpdate();
    }
    
    if (message.type === "correlation_complete") {
      this.loading = false;
      this.isOperationActive = false;
      this.currentOperation = null;
      this.scanProgress = {
        ...this.scanProgress,
        show: false,
        isComplete: true,
        status: 'complete'
      };
      this._showSimpleNotification(
        message.data?.message || (isItalian ? '✅ Ricerca correlazioni completata!' : '✅ Correlation analysis completed!'),
        'success'
      );
      this.requestUpdate();
    }

    if (message.type === "correlation_error") {
      this.loading = false;
      this.isOperationActive = false;
      this.currentOperation = null;
      this.scanProgress = {
        ...this.scanProgress,
        show: false,
        status: 'error'
      };
      this._showSimpleNotification(
        isItalian ? '❌ Errore durante l\'analisi correlazioni' : '❌ Error during correlation analysis',
        'error'
      );
    }
  }


  _handleScanUpdate(message) {
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    
    if (message.type === "entity_result") {
      const entity = message.result;
      const isNewEntity = !this.entities[entity.entity_id];
      this.entities[entity.entity_id] = entity;
      
      // Update entities processed count
      this.scanProgress.entitiesProcessed = Object.keys(this.entities).length;
      this.requestUpdate("entities");
      
      // Auto-save results as they come in
      this._saveAiResults();
      
      // Add flash effect for new entities
      if (isNewEntity) {
        setTimeout(() => {
          const entityRow = document.querySelector(`tr[data-entity-id="${entity.entity_id}"]`);
          if (entityRow) {
            entityRow.classList.add('flash-new');
            setTimeout(() => {
              entityRow.classList.remove('flash-new');
            }, 1000);
          }
        }, 100);
      }
    }
    if (message.type === "scan_progress") {
      // Update detailed progress info
      this.scanProgress = {
        ...this.scanProgress,
        show: true,
        message: message.data.message,
        currentBatch: message.data.batch_number,
        entitiesCount: message.data.entities_count,
        compactMode: message.data.compact_mode || false,
        promptSize: message.data.prompt_size || 0,
        responseSize: message.data.response_size || 0,
        status: message.data.message.includes('📤') ? 'requesting' : 'processing'
      };
      
      // Update token statistics if available
      if (message.data.prompt_size) {
        this.tokenStats = {
          ...this.tokenStats,
          currentBatchTokens: Math.ceil(message.data.prompt_size / 4), // Estimate tokens
          promptChars: (this.tokenStats.promptChars || 0) + message.data.prompt_size, // Accumulate prompt chars
        };
      }
      if (message.data.response_size) {
        this.tokenStats = {
          ...this.tokenStats,
          currentBatchTokens: (this.tokenStats.currentBatchTokens || 0) + Math.ceil(message.data.response_size / 4),
          responseChars: (this.tokenStats.responseChars || 0) + message.data.response_size, // Accumulate response chars
        };
        
        // Update total tokens - ensure we have valid numbers
        const promptTokens = this.tokenStats.promptChars || 0;
        const responseTokens = this.tokenStats.responseChars || 0;
        this.tokenStats.totalTokens = Math.ceil((promptTokens + responseTokens) / 4);
        
        // Update average if we have processed entities
        const processedEntities = Math.max(this.scanProgress.entitiesProcessed || 1, 1);
        this.tokenStats.averageTokensPerEntity = Math.round((this.tokenStats.totalTokens / processedEntities) * 10) / 10;
        
        // Rough cost estimation (assuming GPT-4 pricing: $0.03/1K tokens)
        this.tokenStats.estimatedCost = Math.round(this.tokenStats.totalTokens * 0.00003 * 1000) / 1000;
      }
      
      this.requestUpdate();
    }
    if (message.type === "batch_info") {
      // Update batch progress info - improved calculation
      const currentProgress = this.scanProgress.entitiesProcessed || 0;
      const remaining = message.data.remaining_entities || 0;
      const totalCalculated = message.data.total_entities || (currentProgress + remaining + message.data.entities_in_batch);
      
      this.scanProgress = {
        ...this.scanProgress,
        currentBatch: message.data.batch_number,
        batchSize: message.data.batch_size,
        entitiesInBatch: message.data.entities_in_batch,
        remainingEntities: remaining,
        retryAttempt: message.data.retry_attempt,
        compactMode: message.data.compact_mode || false,
        entitiesProcessed: message.data.processed_entities || currentProgress,
        totalEntities: totalCalculated,
        show: true
      };
      this.requestUpdate();
    }
    if (message.type === "batch_size_reduced") {
      // Show batch size reduction notification
      this._showBatchReductionNotification(message.data);
    }
    if (message.type === "batch_compact_mode") {
      // Show compact mode activation notification
      this._showSimpleNotification(
        `🔄 ${message.data.reason}`,
        'info'
      );
    }
    if (message.type === "token_limit_exceeded") {
      this.loading = false;
      this.scanProgress = {
        ...this.scanProgress,
        show: false, // Hide progress on token limit
        isComplete: false,
        status: 'error'
      };
      
      // Handle automatically without popup - show enhanced notification
      const compactText = message.data.compact_mode ? ' (modalità compatta)' : '';
      this._showSimpleNotification(
        isItalian ? 
          `⚠️ Limite token raggiunto${compactText}. La scansione si è fermata al set ${message.data.batch}.` :
          `⚠️ Token limit reached${compactText}. Scan stopped at set ${message.data.batch}.`,
        'warning'
      );
      this.requestUpdate();
    }
    if (message.type === "scan_complete") {
      this.loading = false;
      this.isOperationActive = false;
      this.currentOperation = null;
      this.scanProgress = {
        ...this.scanProgress,
        show: false, // Hide progress immediately on completion
        isComplete: true,
        status: 'complete',
        message: isItalian ? 
          `🎉 Scansione completata! Analizzate ${Object.keys(this.entities).length} entità` :
          `🎉 Scan completed! Analyzed ${Object.keys(this.entities).length} entities`
      };
      
      // Update final token statistics if available
      if (message.data.token_stats) {
        this.tokenStats = {
          totalTokens: message.data.token_stats.total_tokens || this.tokenStats.totalTokens,
          averageTokensPerEntity: message.data.token_stats.average_tokens_per_entity || this.tokenStats.averageTokensPerEntity,
          estimatedCost: Math.round((message.data.token_stats.total_tokens || 0) * 0.00003 * 1000) / 1000,
          currentBatchTokens: 0, // Reset current batch
          promptChars: message.data.token_stats.prompt_chars || this.tokenStats.promptChars || 0,
          responseChars: message.data.token_stats.response_chars || this.tokenStats.responseChars || 0
        };
      }
      
      // Update last scan info
      this.lastScanInfo = {
        timestamp: new Date().toISOString(),
        entityCount: Object.keys(this.entities).length
      };
      
      // Final save of all results
      this._saveAiResults();
      
      // Show completion notification
      this._showCompletionNotification(Object.keys(this.entities).length);
      
      this.requestUpdate();
    }
  }

  _showSimpleNotification(message, type = 'info') {
    const colors = {
      'info': '#2196f3',
      'success': '#4caf50',
      'warning': '#ff9800',
      'error': '#f44336'
    };

    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: ${colors[type]};
      color: white;
      padding: 12px 16px;
      border-radius: 6px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.2);
      z-index: 9999;
      font-size: 14px;
      max-width: 350px;
      transform: translateY(100%);
      transition: transform 0.3s ease-out;
    `;
    
    document.body.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
      toast.style.transform = 'translateY(0)';
    }, 100);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
      toast.style.transform = 'translateY(100%)';
      setTimeout(() => {
        if (toast.parentNode) {
          toast.remove();
        }
      }, 300);
    }, 4000);
  }

  _showBatchReductionNotification(data) {
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    // Use localized message from backend if available
    const message = data.message || (isItalian ? 
      `🔄 Gruppo ridotto: ${data.old_size} → ${data.new_size} dispositivi (tentativo ${data.retry_attempt})` :
      `🔄 Group reduced: ${data.old_size} → ${data.new_size} devices (attempt ${data.retry_attempt})`);
    
    console.log(isItalian ? 
      `🔄 Dimensione Gruppo Ridotta: ${data.old_size} → ${data.new_size} (tentativo ${data.retry_attempt})` :
      `🔄 Batch Size Reduced: ${data.old_size} → ${data.new_size} (retry ${data.retry_attempt})`
    );
    
    // Create a simple toast notification
    const toast = document.createElement('div');
    toast.textContent = message;
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

  _showCompletionNotification(entityCount) {
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    
    // Create completion toast notification
    const toast = document.createElement('div');
    toast.textContent = isItalian ? 
      `🎉 Scansione completata! Analizzate ${entityCount} entità` :
      `🎉 Scan completed! Analyzed ${entityCount} entities`;
    toast.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #4caf50;
      color: white;
      padding: 16px 20px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      z-index: 9999;
      font-size: 16px;
      font-weight: 500;
      max-width: 350px;
      transform: translateX(100%);
      transition: transform 0.4s ease-out;
    `;
    
    document.body.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
      toast.style.transform = 'translateX(0)';
    }, 100);
    
    // Auto-remove after 6 seconds
    setTimeout(() => {
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => {
        if (toast.parentNode) {
          toast.remove();
        }
      }, 400);
    }, 6000);
  }

  _showTokenLimitNotification(data) {
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    // Use localized messages from backend
    const title = data.title || (isItalian ? "Token Limit Raggiunti" : "Token Limit Reached");
    const message = data.message || (isItalian ? 
      `Scansione fermata al gruppo ${data.batch}. Riprova con gruppi più piccoli.` :
      `Scan stopped at group ${data.batch}. Try again with smaller groups.`);
    
    // Create elegant token limit notification
    const toast = document.createElement('div');
    toast.innerHTML = `
      <div style="display: flex; align-items: center; gap: 12px;">
        <div style="font-size: 24px;">🚨</div>
        <div>
          <div style="font-weight: 600; margin-bottom: 4px;">${title}</div>
          <div style="font-size: 14px; opacity: 0.9;">${message}</div>
        </div>
      </div>
    `;
    toast.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #f44336;
      color: white;
      padding: 16px 20px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      z-index: 9999;
      font-size: 15px;
      max-width: 400px;
      transform: translateX(100%);
      transition: transform 0.4s ease-out;
      cursor: pointer;
    `;
    
    // Make it clickable to dismiss
    toast.addEventListener('click', () => {
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => {
        if (toast.parentNode) {
          toast.remove();
        }
      }, 400);
    });
    
    document.body.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
      toast.style.transform = 'translateX(0)';
    }, 100);
    
    // Auto-remove after 8 seconds (longer for error messages)
    setTimeout(() => {
      if (toast.parentNode) {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
          if (toast.parentNode) {
            toast.remove();
          }
        }, 400);
      }
    }, 8000);
    
    // Log details to console for debugging
    console.log(isItalian ? 
      '🚨 Dettagli HASS AI Token Limit:' : 
      '🚨 HASS AI Token Limit Details:', {
      batch: data.batch,
      message: data.message,
      response: data.response
    });
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
    // Get filtered entities based on minimum weight
    const filteredEntitiesArray = this._getFilteredEntities();
    
    const sortedEntities = filteredEntitiesArray
      .sort((a, b) => {
        const aWeight = this.overrides[a.entity_id]?.overall_weight ?? a.overall_weight;
        const bWeight = this.overrides[b.entity_id]?.overall_weight ?? b.overall_weight;
        return bWeight - aWeight;
      });

    // Translations based on browser language or HA language
    const isItalian = (this.hass.language || navigator.language).startsWith('it');
    const t = isItalian ? {
  title: "Pannello di Controllo HASS AI v1.9.37",
      description: "Analizza le tue entità, insegna all'IA e personalizza i pesi per ottimizzare la tua domotica. L'AI provider è configurato nelle impostazioni dell'integrazione.",
      scan_button: "Avvia Nuova Scansione",
      scanning_button: "Scansione in corso...",
      enabled: "Abilitato",
      entity: "Entità",
      type: "Tipo",
      ai_weight: "Peso IA",
      reason: "Motivazione AI",
      your_weight: "Tuo Peso",
      weight_legend: "(0=Ignora, 5=Critico)"
    } : {
      title: "HASS AI Control Panel v1.9.37",
      description: "Analyze your entities, teach the AI, and customize weights to optimize your smart home. AI provider is configured in integration settings.",
      scan_button: "Start New Scan",
      scanning_button: "Scanning...",
      enabled: "Enabled",
      entity: "Entity",
      type: "Type",
      ai_weight: "AI Weight",
      reason: "AI Reason",
      your_weight: "Your Weight",
      weight_legend: "(0=Ignore, 5=Critical)"
    };

    // Function to get category info with localization - now handles single categories better
    const getCategoryInfo = (category) => {
      // Handle single category (most common case now)
      switch (category) {
        case 'DATA':
          return { 
            icon: 'mdi:chart-line', 
            color: '#2196F3', 
            label: isItalian ? 'Dati' : 'Data' 
          };
        case 'CONTROL':
          return { 
            icon: 'mdi:tune', 
            color: '#4CAF50', 
            label: isItalian ? 'Controllo' : 'Control' 
          };
        case 'ALERTS':
          return { 
            icon: 'mdi:alert-circle', 
            color: '#FF9800', 
            label: isItalian ? 'Allerte' : 'Alerts' 
          };
        case 'SERVICE':
          return { 
            icon: 'mdi:cog', 
            color: '#9C27B0', 
            label: isItalian ? 'Servizio' : 'Service' 
          };
        default:
          return { 
            icon: 'mdi:help-circle', 
            color: '#9E9E9E', 
            label: isItalian ? 'Sconosciuto' : 'Unknown' 
          };
      }
    };

    return html`
      <ha-card .header=${t.title}>
        <div class="card-content">
          <p>${t.description}</p>
          
          <!-- Enhanced Progress Section -->
          ${this.scanProgress.show ? html`
            <div class="progress-section-fixed">
              <div class="progress-message">
                ${this.scanProgress.message}
                ${this.scanProgress.compactMode ? html`<span class="compact-indicator">📦 Compact</span>` : ''}
              </div>
              
              <div class="progress-bar-container">
                <div class="progress-bar">
                  <div class="progress-fill" 
                       style="width: ${this._calculateProgressPercentage()}%">
                  </div>
                </div>
                <div class="progress-text">
                  ${this._renderProgressText(isItalian)}
                </div>
                
                <div class="progress-details">
                  ${this.scanProgress.status === 'requesting' ? html`
                    <div class="status-indicator">${isItalian ? '🔄 Invio richiesta...' : '🔄 Sending request...'}</div>
                  ` : ''}
                  
                  ${this.scanProgress.status === 'processing' ? html`
                    <div class="status-indicator">${isItalian ? '⚙️ Elaborazione risposta...' : '⚙️ Processing response...'}</div>
                  ` : ''}
                  
                  ${this.scanProgress.retryAttempt > 0 ? html`
                    <div class="retry-indicator">${isItalian ? `� Tentativo ${this.scanProgress.retryAttempt}` : `� Retry ${this.scanProgress.retryAttempt}`}</div>
                  ` : ''}
                  
                </div>
                
                <!-- Token Statistics -->
                ${this.tokenStats.totalTokens > 0 || this.scanProgress.show ? html`
                  <div class="token-stats">
                    <div class="token-header">${isItalian ? '📊 Statistiche Token' : '📊 Token Statistics'}</div>
                    <div class="token-grid">
                      <div class="token-item">
                        <span class="token-label">${isItalian ? 'Token Totali' : 'Total Tokens'}</span>
                        <span class="token-value">${this.tokenStats.totalTokens.toLocaleString()}</span>
                      </div>
                      ${this.scanProgress.show && this.tokenStats.currentBatchTokens > 0 ? html`
                        <div class="token-item current-batch">
                          <span class="token-label">${isItalian ? 'Batch Corrente' : 'Current Batch'}</span>
                          <span class="token-value">+${this.tokenStats.currentBatchTokens.toLocaleString()}</span>
                        </div>
                      ` : ''}
                      <div class="token-item">
                        <span class="token-label">${isItalian ? 'Media/Entità' : 'Avg/Entity'}</span>
                        <span class="token-value">${this.tokenStats.averageTokensPerEntity || 0}</span>
                      </div>
                      <div class="token-item">
                        <span class="token-label">${isItalian ? 'Costo Stimato' : 'Est. Cost'}</span>
                        <span class="token-value">$${this.tokenStats.estimatedCost.toFixed(3)}</span>
                      </div>
                    </div>
                  </div>
                ` : ''}
              </div>
            </div>
          ` : ''}
          
          <div class="main-controls-container">
            <div class="analysis-steps">
              <!-- Analysis Type Selection -->
              <div class="step-item ${Object.keys(this.entities).length === 0 ? 'active' : 'completed'}">
                <span class="step-number">1</span>
                <ha-button 
                  raised 
                  @click=${this._runScan} 
                  .disabled=${this.loading || (this.scanProgress.show && !this.scanProgress.isComplete)}
                  class="step-button"
                >
                  ${this._getScanButtonText()}
                </ha-button>
              </div>
              
              <div class="step-arrow ${Object.keys(this.entities).length > 0 ? 'visible' : ''}">→</div>
              
              <div class="step-item ${Object.keys(this.entities).length > 0 ? 'active' : 'disabled'}">
                <span class="step-number">2</span>
                <ha-button 
                  outlined 
                  @click=${this._findCorrelations} 
                  .disabled=${this.loading || this.scanProgress.show || Object.keys(this.entities).length === 0}
                  class="step-button correlations-btn"
                >
                  ${isItalian ? '🔍 Cerca Correlazioni' : '🔍 Find Correlations'}
                </ha-button>
              </div>
              
              ${this.isOperationActive ? html`
                <div class="step-item stop-operation">
                  <ha-button 
                    raised
                    @click=${this._stopOperation} 
                    class="step-button stop-btn"
                  >
                    ${isItalian ? '🛑 Ferma' : '🛑 Stop'}
                  </ha-button>
                </div>
              ` : ''}
            </div>
            
            ${this.lastScanInfo.entityCount > 0 ? html`
              <div class="last-scan-info">
                <div class="scan-stats">
                  ${isItalian ? '📊 Ultima scansione:' : '📊 Last scan:'} ${this.lastScanInfo.entityCount} ${isItalian ? 'entità' : 'entities'}
                  ${this.lastScanInfo.timestamp ? html`
                    <br><small>🕐 ${new Date(this.lastScanInfo.timestamp).toLocaleString()}</small>
                  ` : ''}
                </div>
              </div>
            ` : ''}
          </div>
          
          <!-- Alert Configuration Panel -->
          ${Object.keys(this.entities).length > 0 ? html`
            <div class="alert-config-section">
              <ha-button 
                outlined 
                @click=${() => { this.showAlertConfig = !this.showAlertConfig; this.requestUpdate(); }}
                class="alert-config-btn"
              >
                ${isItalian ? '🔔 Configura Notifiche Alert' : '🔔 Configure Alert Notifications'}
                <ha-icon icon=${this.showAlertConfig ? "mdi:chevron-up" : "mdi:chevron-down"}></ha-icon>
              </ha-button>
              
              ${this.showAlertConfig ? this._renderAlertConfigPanel(isItalian) : ''}
            </div>
          ` : ''}
        </div>

        <!-- Smart Filter Panel - Only show after scan completed -->
        ${Object.keys(this.entities).length > 0 ? html`
          <!-- Compact Filter Controls above table -->
          <div class="table-filter-controls">
            <div class="filter-left">
              <input 
                type="text" 
                placeholder="${isItalian ? 'Cerca entità...' : 'Search entities...'}"
                .value=${this.searchTerm}
                @input=${(e) => { this.searchTerm = e.target.value; this.requestUpdate(); }}
                class="search-input compact"
              />
              ${this.searchTerm ? html`
                <ha-icon 
                  icon="mdi:close" 
                  @click=${() => { this.searchTerm = ''; this.requestUpdate(); }}
                  class="clear-search"
                ></ha-icon>
              ` : ''}
            </div>
            <div class="filter-right">
              <select 
                .value=${this.categoryFilter}
                @change=${(e) => this._saveCategoryFilter(e.target.value)}
                class="category-select compact"
              >
                <option value="ALL">${isItalian ? 'Tutte le categorie' : 'All categories'}</option>
                <option value="DATA">${isItalian ? 'Dati' : 'Data'}</option>
                <option value="CONTROL">${isItalian ? 'Controllo' : 'Control'}</option>
                <option value="ALERTS">${isItalian ? 'Allerte' : 'Alerts'}</option>
                <option value="SERVICE">${isItalian ? 'Servizio' : 'Service'}</option>
                <option value="ENHANCED">${isItalian ? 'Miglioramenti' : 'Enhanced'}</option>
              </select>
              <input 
                type="range" 
                min="0" 
                max="5" 
                step="1" 
                .value=${this.minWeight}
                @input=${(e) => this._saveMinWeightFilter(e.target.value)}
                class="weight-slider compact"
                title="${isItalian ? 'Peso minimo' : 'Minimum weight'}: ${this.minWeight}"
              />
              <span class="weight-display">${this.minWeight}</span>
              ${Object.keys(this.entities).length > 0 ? html`
                <mwc-button 
                  outlined
                  @click=${(e) => this._confirmResetAll(e)}
                  class="reset-button compact"
                  ?disabled=${this.loading}
                >
                  🗑️
                </mwc-button>
              ` : ''}
            </div>
          </div>
        ` : ''}

        <!-- Unevaluated Entities Section -->
        ${(() => {
          const unevaluatedEntities = this._getUnevaluatedEntities();
          return unevaluatedEntities.length > 0 ? html`
            <div class="unevaluated-compact">
              <ha-icon icon="mdi:alert-circle"></ha-icon>
              <span>${isItalian ? `⚠️ ${unevaluatedEntities.length} entità non valutate` : `⚠️ ${unevaluatedEntities.length} unevaluated entities`}</span>
            </div>
          ` : '';
        })()}

        <!-- Scrollable Results Section -->
        ${Object.keys(this.entities).length > 0 ? html`
          <div class="results-container ${this.scanProgress.show ? 'with-progress' : ''}">
            <div class="table-container">
              <table>
                <thead>
                  <tr>
                    <th>${t.enabled}</th>
                    <th>${t.entity}</th>
                    <th>${t.type}</th>
                    <th>${t.ai_weight}</th>
                    <th>${t.reason}</th>
                    <th>${t.your_weight} <span class="legend">${t.weight_legend}</span></th>
                  </tr>
                </thead>
                <tbody>
                  ${sortedEntities.map(entity => {
                    const categoryInfo = getCategoryInfo(entity.category);
                    const isUnavailable = this._isEntityUnavailable(entity.entity_id);
                    return html`
                    <tr data-entity-id="${entity.entity_id}" class="${isUnavailable ? 'entity-unavailable' : ''}">
                      <td>
                        <ha-switch
                          .checked=${this.overrides[entity.entity_id]?.enabled ?? true}
                          data-entity-id=${entity.entity_id}
                          @change=${this._handleToggle}
                          .disabled=${isUnavailable}
                        ></ha-switch>
                      </td>
                      <td>
                        <div class="entity-info ${isUnavailable ? 'unavailable' : ''}">
                          <strong>${entity.entity_id}</strong>
                          <br><small>${entity.name || entity.entity_id.split('.')[1]}</small>
                        </div>
                      </td>
                      <td>
                        <div class="category-badges">
                          ${Array.isArray(entity.category) ? 
                            entity.category.map(cat => {
                              const catInfo = getCategoryInfo(cat);
                              return html`
                                <div class="category-badge" style="color: ${catInfo.color}">
                                  <ha-icon icon="${catInfo.icon}"></ha-icon>
                                  <span>${catInfo.label}</span>
                                </div>
                              `;
                            }) :
                            html`
                              <div class="category-badge" style="color: ${categoryInfo.color}">
                                <ha-icon icon="${categoryInfo.icon}"></ha-icon>
                                <span>${categoryInfo.label}</span>
                              </div>
                            `
                          }
                        </div>
                      </td>
                      <td><span class="weight-badge weight-${entity.overall_weight}">${entity.overall_weight}</span></td>
                      <td>
                        <div class="reason-section">
                          <div class="reason-text">${entity.overall_reason}</div>
                          
                          ${this.correlations[entity.entity_id] && this.correlations[entity.entity_id].length > 0 ? html`
                            <div class="correlations-section">
                              <strong>${isItalian ? '🔗 Correlazioni:' : '🔗 Correlations:'}</strong>
                              <ul class="correlations-list">
                                ${this.correlations[entity.entity_id].map(corr => html`
                                  <li class="correlation-item">
                                    <span class="correlation-entity">${corr.entity_id}</span>
                                    <span class="correlation-type ${corr.correlation_type}">${corr.correlation_type}</span>
                                    <span class="correlation-strength strength-${corr.strength}">★${corr.strength}</span>
                                    <small class="correlation-reason">${corr.reason}</small>
                                  </li>
                                `)}
                              </ul>
                            </div>
                          ` : ''}
                          
                          ${entity.analysis_details ? html`
                            <details class="analysis-details">
                              <summary>${isItalian ? '📋 Dettagli Analisi' : '📋 Analysis Details'}</summary>
                              <div class="analysis-content">
                                <div><strong>${isItalian ? 'Dominio:' : 'Domain:'}</strong> ${entity.analysis_details.domain || entity.entity_id.split('.')[0]}</div>
                                <div><strong>${isItalian ? 'Stato Attuale:' : 'Current State:'}</strong> ${entity.analysis_details.state || (isItalian ? 'N/D' : 'N/A')}</div>
                                <div><strong>${isItalian ? 'Tipo Gestione:' : 'Management Type:'}</strong> 
                                  <span class="management-type ${entity.management_type || 'unknown'}">
                                    ${entity.management_type === 'user' ? 
                                      (isItalian ? '👤 Gestita dall\'utente' : '👤 User-managed') : 
                                      entity.management_type === 'service' ? 
                                        (isItalian ? '🔧 Gestita da servizio' : '🔧 Service-managed') :
                                        (isItalian ? '❓ Non determinato' : '❓ Undetermined')
                                    }
                                  </span>
                                </div>
                                
                                ${(Array.isArray(entity.category) ? entity.category.includes('ALERTS') : entity.category === 'ALERTS') ? html`
                                  <div class="alert-threshold-section">
                                    <strong>${isItalian ? '🚨 Soglia Allerta:' : '🚨 Alert Threshold:'}</strong>
                                    <div class="alert-threshold-controls">
                                      <ha-select
                                        .value=${this._getAlertThreshold(entity.entity_id).level}
                                        @selectionChanged=${(e) => this._saveAlertThreshold(entity.entity_id, e.target.value)}
                                        class="alert-threshold-select"
                                      >
                                        <ha-list-item value="MEDIUM">
                                          <div class="alert-threshold-option">
                                            <ha-icon icon="mdi:alert-circle-outline" style="color: #FFA500;"></ha-icon>
                                            <span>${isItalian ? 'Media' : 'Medium'}</span>
                                          </div>
                                        </ha-list-item>
                                        <ha-list-item value="SEVERE">
                                          <div class="alert-threshold-option">
                                            <ha-icon icon="mdi:alert" style="color: #FF6B6B;"></ha-icon>
                                            <span>${isItalian ? 'Grave' : 'Severe'}</span>
                                          </div>
                                        </ha-list-item>
                                        <ha-list-item value="CRITICAL">
                                          <div class="alert-threshold-option">
                                            <ha-icon icon="mdi:alert-octagon" style="color: #DC143C;"></ha-icon>
                                            <span>${isItalian ? 'Critica' : 'Critical'}</span>
                                          </div>
                                        </ha-list-item>
                                      </ha-select>
                                      <small class="alert-threshold-description">
                                        ${this._getAlertThresholdConfig(this._getAlertThreshold(entity.entity_id).level).description}
                                        ${this._getAlertThreshold(entity.entity_id).customized ? 
                                          html`<span class="customized-badge">${isItalian ? '(personalizzata)' : '(customized)'}</span>` : ''
                                        }
                                      </small>
                                    </div>
                                  </div>
                                ` : ''}
                                
                                ${entity.auto_thresholds && entity.auto_thresholds.thresholds ? html`
                                  <div class="auto-thresholds-section">
                                    <strong>${isItalian ? '🤖 Soglie Automatiche Suggerite:' : '🤖 Auto-Generated Thresholds:'}</strong>
                                    <div class="auto-thresholds-list">
                                      ${Object.entries(entity.auto_thresholds.thresholds).map(([level, threshold]) => html`
                                        <div class="auto-threshold-item">
                                          <span class="threshold-level threshold-${level.toLowerCase()}">
                                            ${level === 'LOW' ? '⚠️' : level === 'MEDIUM' ? '🔶' : '🔴'} ${level}
                                          </span>
                                          <span class="threshold-condition">${threshold.condition}</span>
                                          <span class="threshold-description">${threshold.description}</span>
                                        </div>
                                      `)}
                                      <div class="auto-threshold-info">
                                        <small>${isItalian ? 
                                          `💡 Tipo: ${entity.auto_thresholds.entity_type || 'non determinato'}` :
                                          `💡 Type: ${entity.auto_thresholds.entity_type || 'undetermined'}`
                                        }</small>
                                      </div>
                                    </div>
                                  </div>
                                ` : ''}
                                
                                <div><strong>${isItalian ? 'Attributi con Peso:' : 'Weighted Attributes:'}</strong></div>
                                <ul class="attributes-list">
                                  ${Object.entries(entity.analysis_details.attributes || {}).map(([key, value]) => {
                                    const weight = entity.attribute_weights && entity.attribute_weights[key] ? 
                                      ` (${isItalian ? 'peso' : 'weight'}: ${entity.attribute_weights[key]})` : '';
                                    return html`
                                      <li><code>${key}</code>: ${JSON.stringify(value)}${weight}</li>
                                    `;
                                  })}
                                </ul>
                              </div>
                            </details>
                          ` : ''}
                        </div>
                      </td>
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
                    `;
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ` : ''}
      </ha-card>
    `;
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
      
      .progress-section-fixed {
        position: sticky;
        top: 0;
        z-index: 10;
        background-color: var(--card-background-color);
        border-bottom: 2px solid var(--info-color, #2196f3);
        padding: 16px;
        margin: 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      }
      
      .results-container {
        max-height: 70vh;
        overflow-y: auto;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        margin-top: 0;
      }
      
      .results-container.with-progress {
        max-height: 75vh;
        min-height: 60vh;
      }
      
      .flash-new {
        animation: flashHighlight 1s ease-out;
        background-color: var(--success-color, #4caf50) !important;
      }
      
      @keyframes flashHighlight {
        0% { 
          background-color: var(--success-color, #4caf50);
          transform: scale(1.02);
        }
        50% { 
          background-color: rgba(76, 175, 80, 0.3);
          transform: scale(1.01);
        }
        100% { 
          background-color: transparent;
          transform: scale(1);
        }
      }
      
      .reason-section {
        max-width: 300px;
      }
      
      .analysis-details {
        margin-top: 8px;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        padding: 4px;
      }
      
      .analysis-details summary {
        cursor: pointer;
        font-size: 12px;
        color: var(--info-color, #2196f3);
        padding: 4px;
        border-radius: 3px;
      }
      
      .analysis-details summary:hover {
        background-color: var(--primary-background-color);
      }
      
      .analysis-content {
        padding: 8px;
        font-size: 11px;
        background-color: var(--primary-background-color);
        border-radius: 3px;
        margin-top: 4px;
      }
      
      .analysis-content div {
        margin-bottom: 4px;
      }
      
      .attributes-list {
        margin: 4px 0 0 16px;
        padding: 0;
      }
      
      .attributes-list li {
        margin-bottom: 2px;
        font-family: monospace;
        font-size: 10px;
      }
      
      .attributes-list code {
        background-color: var(--code-background-color, #f5f5f5);
        padding: 1px 3px;
        border-radius: 2px;
        color: var(--info-color, #2196f3);
      }
      
      .management-type {
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 11px;
        font-weight: 500;
      }
      
      .management-type.user {
        background-color: rgba(76, 175, 80, 0.1);
        color: #4caf50;
      }
      
      .management-type.service {
        background-color: rgba(255, 152, 0, 0.1);
        color: #ff9800;
      }
      
      .management-type.unknown {
        background-color: rgba(158, 158, 158, 0.1);
        color: #9e9e9e;
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
      
      .last-scan-info {
        background-color: var(--card-background-color, #ffffff);
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 6px;
        padding: 12px;
        margin: 16px 0;
        font-size: 14px;
        color: var(--secondary-text-color);
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
        font-size: 0.85em;
        color: var(--secondary-text-color);
        line-height: 1.3;
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
      
      .category-badges {
        display: flex;
        flex-direction: column;
        gap: 2px;
        align-items: flex-start;
      }
      
      .category-badge {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        font-weight: 500;
        white-space: nowrap;
        padding: 2px 6px;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
      }
      
      .category-badge ha-icon {
        --mdi-icon-size: 16px;
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
      
      /* Smart Filter Panel Styles */
      .smart-filter-panel {
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        margin: 16px;
        padding: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      }
      
      .filter-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
        font-size: 1.1em;
        margin-bottom: 12px;
        color: var(--primary-text-color);
      }
      
      .filter-controls {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      
      .filter-row {
        display: flex;
        align-items: center;
        gap: 12px;
        justify-content: space-between;
      }
      
      .filter-row label {
        font-weight: 500;
        min-width: 120px;
        color: var(--primary-text-color);
      }
      
      .weight-slider {
        flex: 1;
        height: 6px;
        border-radius: 3px;
        background: var(--divider-color);
        outline: none;
        -webkit-appearance: none;
        appearance: none;
      }
      
      .weight-slider::-webkit-slider-thumb {
        appearance: none;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: var(--primary-color);
        cursor: pointer;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
      }
      
      .weight-slider::-moz-range-thumb {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: var(--primary-color);
        cursor: pointer;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
      }
      
      .weight-value {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 30px;
        height: 30px;
        background: var(--primary-color);
        color: white;
        border-radius: 50%;
        font-weight: 600;
        font-size: 14px;
      }
      
      .category-select {
        padding: 8px 12px;
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-family: inherit;
        font-size: 14px;
        min-width: 120px;
        cursor: pointer;
      }
      
      .category-select:focus {
        outline: none;
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px rgba(var(--rgb-primary-color), 0.2);
      }
      
      .filter-stats {
        padding: 8px 12px;
        background: var(--secondary-background-color);
        border-radius: 6px;
        font-size: 0.9em;
        color: var(--secondary-text-color);
        text-align: center;
      }
      
      .filter-stats strong {
        color: var(--primary-text-color);
        font-weight: 600;
      }
      
      .reset-section {
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid var(--divider-color);
        text-align: center;
      }
      
      .reset-button {
        --mdc-theme-primary: var(--error-color);
        --mdc-theme-on-primary: white;
        --ha-button-border-radius: 20px;
        min-width: 200px;
      }
      
      .reset-button:hover {
        background-color: var(--error-color);
        color: white;
      }
      
      /* Search Input Styles */
      .search-input {
        flex: 1;
        padding: 8px 12px;
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 14px;
        outline: none;
      }
      
      .search-input:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px rgba(var(--rgb-primary-color), 0.1);
      }
      
      .clear-search {
        cursor: pointer;
        color: var(--secondary-text-color);
        padding: 4px;
        margin-left: 8px;
        border-radius: 50%;
        transition: background-color 0.2s;
      }
      
      .clear-search:hover {
        background-color: var(--divider-color);
      }
      
      /* Unevaluated Entities Panel */
      .unevaluated-panel {
        background: linear-gradient(135deg, var(--warning-color, #ff9800), rgba(255, 152, 0, 0.1));
        border: 1px solid var(--warning-color, #ff9800);
        border-radius: 8px;
        margin: 16px;
        padding: 16px;
        box-shadow: 0 2px 4px rgba(255, 152, 0, 0.2);
      }
      
      /* Analysis Steps styling */
      .analysis-steps {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 16px;
        padding: 16px;
        background: var(--card-background-color);
        border-radius: 8px;
        border: 1px solid var(--divider-color);
      }
      
      .step-item {
        display: flex;
        align-items: center;
        gap: 8px;
        opacity: 0.6;
        transition: opacity 0.3s;
      }
      
      .step-item.active {
        opacity: 1;
      }
      
      .step-item.completed {
        opacity: 1;
      }
      
      .step-item.completed .step-number {
        background: var(--success-color, #4caf50);
        color: white;
      }
      
      .step-number {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: var(--primary-color);
        color: white;
        font-weight: 500;
        font-size: 12px;
      }
      
      .step-arrow {
        font-size: 18px;
        color: var(--primary-color);
        opacity: 0;
        transition: opacity 0.3s;
      }
      
      .step-arrow.visible {
        opacity: 1;
      }
      
      .step-button {
        margin: 0;
      }
      
      .stop-btn {
        --mdc-theme-primary: #f44336;
        --mdc-theme-on-primary: white;
        --mdc-button-raised-box-shadow: 0 2px 4px rgba(244, 67, 54, 0.2);
      }
      
      .stop-operation {
        margin-left: 12px;
        animation: pulse 1.5s infinite;
      }
      
      @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
      }
      
      /* Analysis Type Selection Styles */
      .analysis-type-selection {
        margin-bottom: 16px;
        padding: 16px;
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 8px;
      }
      
      .analysis-type-header {
        margin-bottom: 12px;
        font-weight: 600;
        color: var(--primary-text-color);
      }
      
      .analysis-type-buttons {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 12px;
      }
      
      .analysis-type-btn {
        --mdc-theme-primary: var(--primary-color);
        --mdc-theme-on-primary: var(--text-primary-color);
        flex: 1;
        min-width: 120px;
      }
      
      .analysis-type-description {
        padding: 8px 12px;
        background: rgba(var(--rgb-primary-color), 0.1);
        border-radius: 4px;
        font-size: 0.9em;
        color: var(--primary-text-color);
        line-height: 1.4;
      }
      
      /* Alert Threshold Styles */
      .alert-threshold-section {
        margin: 16px 0;
        padding: 12px;
        background: rgba(255, 152, 0, 0.1);
        border-left: 3px solid var(--warning-color);
        border-radius: 4px;
      }
      
      .alert-threshold-controls {
        margin-top: 8px;
      }
      
      .alert-threshold-select {
        width: 100%;
        margin-bottom: 8px;
      }
      
      .alert-threshold-option {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      
      .alert-threshold-description {
        display: block;
        color: var(--secondary-text-color);
        font-style: italic;
      }
      
      .customized-badge {
        color: var(--primary-color);
        font-weight: 600;
      }
      
      /* Auto-thresholds styles */
      .auto-thresholds-section {
        margin-top: 8px;
        padding: 8px;
        border: 1px dashed var(--divider-color);
        border-radius: 4px;
        background: rgba(var(--rgb-primary-color), 0.05);
      }
      
      .auto-thresholds-list {
        margin-top: 4px;
      }
      
      .auto-threshold-item {
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 4px 0;
        padding: 4px;
        background: var(--card-background-color);
        border-radius: 3px;
        font-size: 0.85em;
      }
      
      .threshold-level {
        font-weight: 600;
        min-width: 60px;
        text-align: center;
        padding: 2px 6px;
        border-radius: 3px;
      }
      
      .threshold-low { background: rgba(255, 165, 0, 0.2); color: #FFA500; }
      .threshold-medium { background: rgba(255, 107, 107, 0.2); color: #FF6B6B; }
      .threshold-high { background: rgba(220, 20, 60, 0.2); color: #DC143C; }
      
      .threshold-condition {
        font-family: monospace;
        background: var(--code-background-color, #f5f5f5);
        padding: 2px 4px;
        border-radius: 2px;
        font-size: 0.9em;
      }
      
      .threshold-description {
        flex: 1;
        color: var(--secondary-text-color);
        font-style: italic;
      }
      
      .auto-threshold-info {
        margin-top: 6px;
        padding-top: 4px;
        border-top: 1px dotted var(--divider-color);
      }
      
      /* Ultra compact unevaluated entities - single line */
      .unevaluated-compact {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        margin: 8px 16px;
        background: rgba(255, 152, 0, 0.1);
        border-left: 3px solid var(--warning-color, #ff9800);
        border-radius: 3px;
        color: var(--warning-color, #ff9800);
        font-size: 0.9em;
        font-weight: 500;
      }
      
      .unevaluated-compact ha-icon {
        --mdc-icon-size: 16px;
      }
      
      .unevaluated-content p {
        margin: 0 0 12px 0;
        font-weight: 500;
      }
      
      .unevaluated-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      
      .unevaluated-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 12px;
        background: var(--card-background-color);
        border-radius: 6px;
        border: 1px solid var(--divider-color);
      }
      
      .entity-id {
        font-family: monospace;
        font-size: 0.9em;
        color: var(--primary-text-color);
      }
      
      .evaluate-btn {
        --mdc-button-horizontal-padding: 12px;
        --mdc-typography-button-font-size: 12px;
      }
      
      .more-entities {
        text-align: center;
        color: var(--secondary-text-color);
        font-style: italic;
        padding: 8px;
      }
      
      /* Unavailable entities styling */
      .entity-unavailable {
        opacity: 0.4;
        background-color: rgba(128, 128, 128, 0.1);
        pointer-events: none;
      }
      
      /* Correlations styling */
      .correlations-section {
        margin-top: 8px;
        padding: 8px;
        background: rgba(var(--rgb-primary-color), 0.05);
        border-radius: 4px;
        border-left: 3px solid var(--primary-color);
      }
      
      .correlations-list {
        list-style: none;
        padding: 0;
        margin: 4px 0 0 0;
      }
      
      .correlation-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 4px 0;
        font-size: 0.9em;
        flex-wrap: wrap;
      }
      
      .correlation-entity {
        font-family: monospace;
        font-weight: 500;
        color: var(--primary-color);
      }
      
      .correlation-type {
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 0.8em;
        font-weight: 500;
        text-transform: capitalize;
      }
      
      .correlation-type.functional {
        background: #e3f2fd;
        color: #1976d2;
      }
      
      .correlation-type.location {
        background: #f3e5f5;
        color: #7b1fa2;
      }
      
      .correlation-type.temporal {
        background: #e8f5e8;
        color: #388e3c;
      }
      
      .correlation-type.data_dependency {
        background: #fff3e0;
        color: #f57c00;
      }
      
      .correlation-strength {
        font-weight: 500;
        padding: 1px 4px;
        border-radius: 2px;
        font-size: 0.8em;
      }
      
      .correlation-strength.strength-1 { background: #ffebee; color: #c62828; }
      .correlation-strength.strength-2 { background: #fff3e0; color: #ef6c00; }
      .correlation-strength.strength-3 { background: #fffde7; color: #f9a825; }
      .correlation-strength.strength-4 { background: #f1f8e9; color: #689f38; }
      .correlation-strength.strength-5 { background: #e8f5e8; color: #388e3c; }
      
      .correlation-reason {
        color: var(--secondary-text-color);
        font-style: italic;
        flex: 1;
      }
      
      .entity-unavailable td {
        color: var(--disabled-text-color) !important;
      }
      
      .entity-info.unavailable {
        opacity: 0.6;
        text-decoration: line-through;
      }
      
      .entity-info.unavailable strong {
        color: var(--disabled-text-color);
      }
      
      .entity-info.unavailable small {
        color: var(--disabled-text-color);
      }
      
      .compact-indicator {
        background: #e3f2fd;
        color: #1976d2;
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 0.8em;
        margin-left: 8px;
      }
      
      .progress-details {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 8px;
        font-size: 0.85em;
      }
      
      .retry-indicator {
        background: #fff3e0;
        color: #f57c00;
        padding: 2px 6px;
        border-radius: 4px;
      }
      
      .debug-info {
        background: #f5f5f5;
        color: #666;
        padding: 2px 6px;
        border-radius: 4px;
      }
      
      /* Token Statistics Styles */
      .token-stats {
        margin-top: 12px;
        padding: 12px;
        background: var(--primary-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 8px;
      }
      
      .token-header {
        font-weight: 600;
        color: var(--primary-text-color);
        margin-bottom: 8px;
        font-size: 14px;
      }
      
      .token-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
      }
      
      .token-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 4px 8px;
        background: var(--card-background-color);
        border-radius: 4px;
        border: 1px solid var(--divider-color);
      }
      
      .token-item.current-batch {
        background: var(--primary-color);
        color: var(--text-primary-color);
        border-color: var(--primary-color);
        animation: pulse 2s infinite;
      }
      
      .token-item.current-batch .token-label,
      .token-item.current-batch .token-value {
        color: var(--text-primary-color);
      }
      
      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
      }
      
      .token-label {
        font-size: 12px;
        color: var(--secondary-text-color);
        font-weight: 500;
      }
      
      .token-value {
        font-size: 12px;
        font-weight: 600;
        color: var(--primary-text-color);
      }
      
      .token-live {
        color: var(--info-color, #2196f3);
        animation: tokenPulse 2s infinite;
      }
      
      @keyframes tokenPulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
      }
      
      /* Alert Configuration Styles */
      .alert-config-section {
        margin-top: 20px;
        border: 2px solid var(--divider-color);
        border-radius: 8px;
        background: var(--card-background-color);
      }
      
      .alert-config-btn {
        width: 100%;
        --mdc-typography-button-font-size: 14px;
        --mdc-button-horizontal-padding: 16px;
        border-radius: 8px 8px 0 0;
        border-bottom: 1px solid var(--divider-color);
      }
      
      .alert-config-panel {
        padding: 20px;
        background: var(--card-background-color);
        border-radius: 0 0 8px 8px;
      }
      
      .alert-status h3,
      .notification-config h3,
      .alert-entities h3 {
        margin: 0 0 12px 0;
        color: var(--primary-text-color);
        font-size: 16px;
        font-weight: 600;
      }
      
      .status-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;
        margin-bottom: 20px;
      }
      
      .status-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 12px;
        background: var(--primary-background-color);
        border-radius: 6px;
        border: 1px solid var(--divider-color);
      }
      
      .status-label {
        font-weight: 500;
        color: var(--secondary-text-color);
      }
      
      .status-value {
        font-weight: 600;
      }
      
      .status-value.enabled {
        color: var(--success-color, #4CAF50);
      }
      
      .status-value.disabled {
        color: var(--error-color, #f44336);
      }
      
      .alert-count {
        color: var(--warning-color, #ff9800);
      }
      
      .config-row {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 12px;
      }
      
      .config-row label {
        min-width: 140px;
        font-weight: 500;
        color: var(--primary-text-color);
      }
      
      .service-select {
        flex: 1;
        padding: 8px 12px;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 14px;
      }
      
      .alert-example {
        margin-top: 16px;
        padding: 12px;
        background: var(--primary-background-color);
        border-radius: 6px;
        border-left: 4px solid var(--info-color, #2196F3);
      }
      
      .alert-example h4 {
        margin: 0 0 8px 0;
        font-size: 14px;
        color: var(--primary-text-color);
      }
      
      .example-message {
        font-family: monospace;
        font-size: 12px;
        color: var(--secondary-text-color);
        white-space: pre-wrap;
        background: var(--card-background-color);
        padding: 8px;
        border-radius: 4px;
        border: 1px solid var(--divider-color);
      }
      
      .entities-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 12px;
        margin-top: 12px;
      }
      
      .alert-entity-card {
        padding: 12px;
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        background: var(--card-background-color);
        transition: border-color 0.2s ease;
      }
      
      .alert-entity-card.has-alert {
        border-color: var(--error-color, #f44336);
        background: rgba(244, 67, 54, 0.05);
      }
      
      .entity-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
      }
      
      .entity-name {
        font-weight: 600;
        color: var(--primary-text-color);
        font-size: 14px;
      }
      
      .alert-badge {
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
      }
      
      .alert-badge.ok {
        background: var(--success-color, #4CAF50);
        color: white;
      }
      
      .alert-badge.warning {
        background: var(--warning-color, #ff9800);
        color: white;
      }
      
      .alert-badge.alert {
        background: var(--error-color, #f44336);
        color: white;
      }
      
      .alert-badge.critical {
        background: #d32f2f;
        color: white;
        animation: pulse 1.5s infinite;
      }
      
      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
      }
      
      .entity-details {
        font-size: 12px;
      }
      
      .detail-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 4px;
      }
      
      .detail-row:last-child {
        margin-bottom: 0;
      }
      
      .thresholds {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      
      .threshold-item {
        font-size: 10px;
        padding: 1px 4px;
        border-radius: 2px;
      }
      
      .threshold-item.warning {
        background: rgba(255, 152, 0, 0.2);
        color: var(--warning-color, #ff9800);
      }
      
      .threshold-item.alert {
        background: rgba(244, 67, 54, 0.2);
        color: var(--error-color, #f44336);
      }
      
      .threshold-item.critical {
        background: rgba(211, 47, 47, 0.2);
        color: #d32f2f;
      }
      
      .no-alert-entities {
        text-align: center;
        padding: 20px;
        color: var(--secondary-text-color);
        font-style: italic;
      }
      
      .alert-info {
        margin-top: 20px;
        padding: 12px;
        background: var(--primary-background-color);
        border-radius: 6px;
        border-left: 4px solid var(--info-color, #2196F3);
      }
      
      .alert-info h4 {
        margin: 0 0 8px 0;
        font-size: 14px;
        color: var(--primary-text-color);
      }
      
      .alert-info ul {
        margin: 0;
        padding-left: 16px;
      }
      
      .alert-info li {
        margin-bottom: 4px;
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      
      /* Input Text Configuration Styles */
      .entity-input {
        flex: 1;
        padding: 8px 12px;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 14px;
        font-family: monospace;
      }
      
      .entity-status {
        margin-left: 8px;
        font-size: 12px;
      }
      
      .status-ok {
        color: var(--success-color, #4CAF50);
      }
      
      .status-error {
        color: var(--error-color, #f44336);
      }
      
      .current-value {
        padding: 8px 12px;
        background: var(--secondary-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        font-family: monospace;
        color: var(--primary-text-color);
        font-size: 14px;
        word-break: break-all;
        max-height: 100px;
        overflow-y: auto;
      }
      
      .clear-button {
        padding: 8px 16px;
        background: var(--error-color, #f44336);
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        transition: background-color 0.2s;
      }
      
      .clear-button:hover {
        background: var(--error-color-dark, #d32f2f);
      }
      
      .config-help {
        margin-top: 12px;
        padding: 12px;
        background: rgba(33, 150, 243, 0.1);
        border-radius: 6px;
        border-left: 4px solid var(--info-color, #2196F3);
      }
      
      .config-help h4 {
        margin: 0 0 8px 0;
        font-size: 14px;
        color: var(--primary-text-color);
      }
      
      .config-help p {
        margin: 4px 0;
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      
      .config-help pre {
        background: var(--card-background-color);
        padding: 8px;
        border-radius: 4px;
        border: 1px solid var(--divider-color);
        font-size: 11px;
        color: var(--primary-text-color);
        overflow-x: auto;
      }
      
      .config-help code {
        font-family: 'Roboto Mono', 'Consolas', 'Monaco', monospace;
      }
      
      .config-row label {
        display: flex;
        align-items: center;
        gap: 8px;
        min-width: auto;
      }
      
      .config-row input[type="radio"] {
        margin: 0;
      }
      
      /* Auto-config styles */
      .auto-config-section {
        margin-top: 16px;
        padding: 12px;
        background: rgba(76, 175, 80, 0.1);
        border-radius: 6px;
        border-left: 4px solid var(--success-color, #4caf50);
      }
      
      .auto-config-button {
        padding: 8px 16px;
        background: var(--primary-color, #2196F3);
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        transition: all 0.2s;
        margin-right: 8px;
      }
      
      .auto-config-button:hover {
        background: var(--primary-color-dark, #1976D2);
        transform: translateY(-1px);
      }
      
      .auto-config-button:disabled {
        background: var(--disabled-color, #cccccc);
        cursor: not-allowed;
        transform: none;
      }
      
      .auto-config-status {
        display: inline-block;
        margin-left: 8px;
        font-size: 12px;
        color: var(--success-color, #4caf50);
      }
      
      /* Debug section styles */
      .debug-section {
        margin: 16px 0;
        padding: 12px;
        background: rgba(255, 152, 0, 0.1);
        border-radius: 6px;
        border-left: 4px solid var(--warning-color, #ff9800);
      }
      
      .debug-section h3 {
        margin: 0 0 8px 0;
        font-size: 14px;
        color: var(--primary-text-color);
      }
      
      .debug-info p {
        margin: 4px 0;
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      
      .debug-list {
        list-style: none;
        padding: 0;
        margin: 8px 0;
      }
      
      .debug-list li {
        padding: 4px 8px;
        margin: 2px 0;
        background: var(--card-background-color);
        border-radius: 4px;
        font-size: 11px;
        font-family: monospace;
      }
      
      .debug-warning {
        padding: 8px;
        background: rgba(244, 67, 54, 0.1);
        border-radius: 4px;
        border: 1px solid var(--error-color, #f44336);
      }
      
      .debug-warning p {
        margin: 4px 0;
        font-size: 12px;
        color: var(--error-color, #f44336);
      }
      
      /* Main Controls Container - Side by side layout */
      .main-controls-container {
        display: flex;
        gap: 16px;
        align-items: flex-start;
        margin-bottom: 16px;
      }
      
      .analysis-steps {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 16px;
        background: var(--card-background-color);
        border-radius: 8px;
        border: 1px solid var(--divider-color);
      }
      
      .last-scan-info {
        flex: 0 0 200px;
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        padding: 12px;
        font-size: 14px;
        color: var(--secondary-text-color);
        text-align: center;
      }
      
      .scan-stats {
        line-height: 1.4;
      }
      
      /* Table Filter Controls - Compact horizontal layout */
      .table-filter-controls {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        padding: 12px 16px;
        background: var(--primary-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        margin-bottom: 8px;
      }
      
      .filter-left {
        display: flex;
        align-items: center;
        gap: 8px;
        flex: 1;
        max-width: 300px;
      }
      
      .filter-right {
        display: flex;
        align-items: center;
        gap: 12px;
        flex: 0 0 auto;
      }
      
      .search-input.compact {
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 14px;
        width: 100%;
      }
      
      .category-select.compact {
        padding: 6px 10px;
        border-radius: 6px;
        font-size: 13px;
        min-width: 140px;
      }
      
      .weight-slider.compact {
        width: 80px;
        height: 4px;
      }
      
      .weight-display {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 24px;
        height: 24px;
        background: var(--primary-color);
        color: white;
        border-radius: 50%;
        font-weight: 600;
        font-size: 12px;
      }
      
      .reset-button.compact {
        --mdc-button-horizontal-padding: 8px;
        --mdc-typography-button-font-size: 12px;
        min-width: auto;
        --mdc-theme-primary: var(--error-color);
      }
      
      /* Monitoring Toggle Controls */
      .monitoring-toggle .monitoring-control {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      
      .monitoring-btn {
        --mdc-button-horizontal-padding: 12px;
        --mdc-typography-button-font-size: 12px;
        min-width: auto;
      }
      
      .monitoring-btn.start {
        --mdc-theme-primary: var(--success-color);
      }
      
      .monitoring-btn.stop {
        --mdc-theme-primary: var(--error-color);
      }
    `;
  }

  // Progress calculation helper
  _calculateProgressPercentage() {
    if (!this.scanProgress.entitiesProcessed || !this.scanProgress.totalEntities) {
      return 10; // Show minimal progress when starting
    }
    
    const percentage = Math.round((this.scanProgress.entitiesProcessed / this.scanProgress.totalEntities) * 100);
    return Math.max(10, Math.min(percentage, 100)); // Ensure between 10-100%
  }

  // Progress text rendering helper
  _renderProgressText(isItalian) {
    if (this.scanProgress.entitiesInBatch > 0) {
      const currentText = isItalian ? 
        `Set ${this.scanProgress.currentBatch}: ${this.scanProgress.entitiesInBatch} entità` :
        `Set ${this.scanProgress.currentBatch}: ${this.scanProgress.entitiesInBatch} entities`;
      
      const remainingText = this.scanProgress.remainingEntities > 0 ? 
        (isItalian ? ` (${this.scanProgress.remainingEntities} rimanenti)` : ` (${this.scanProgress.remainingEntities} remaining)`) : 
        '';
      
      const totalText = this.scanProgress.totalEntities > 0 ?
        (isItalian ? ` | Totale: ${this.scanProgress.totalEntities}` : ` | Total: ${this.scanProgress.totalEntities}`) :
        '';
      
      return `${currentText}${remainingText}${totalText}`;
    } else {
      return isItalian ? 'Preparazione scansione...' : 'Preparing scan...';
    }
  }

  async _confirmResetAll(e) {
    if (e) e.preventDefault();
    console.log('_confirmResetAll called'); // Debug log
    const isItalian = this.language.includes('it');
    
    const confirmed = await this._showConfirmDialog(
      isItalian ? 'Conferma Cancellazione' : 'Confirm Reset',
      isItalian ? 
        'Sei sicuro di voler cancellare tutti i dati e riavviare l\'analisi?\n\nQuesto cancellerà:\n• Tutti i risultati dell\'analisi\n• I pesi personalizzati\n• Le soglie di allarme\n• Le correlazioni\n\nQuesta azione non può essere annullata.' :
        'Are you sure you want to clear all data and restart the analysis?\n\nThis will clear:\n• All analysis results\n• Custom weights\n• Alert thresholds\n• Correlations\n\nThis action cannot be undone.',
      isItalian ? 'Cancella Tutto' : 'Clear All',
      isItalian ? 'Annulla' : 'Cancel'
    );

    console.log('Confirmed:', confirmed); // Debug log
    if (confirmed) {
      await this._resetAll();
    }
  }

  async _resetAll() {
    const isItalian = this.language.includes('it');
    
    try {
      this.loading = true;
      
      // Clear all data
      this.entities = {};
      this.overrides = {};
      this.correlations = {};
      this.alertThresholds = {};
      this.tokenStats = {
        totalTokens: 0,
        averageTokensPerEntity: 0,
        totalEntities: 0,
        currentBatch: {
          entities: 0,
          tokens: 0
        }
      };
      this.scanProgress = {
        show: false,
        message: '',
        current: 0,
        total: 0,
        isComplete: false,
        status: 'idle'
      };

      // Clear storage
      await this.hass.connection.sendMessage({
        type: "hass_ai/clear_storage"
      });

      // Reset filters to defaults
      this.minWeight = 3;
      this.categoryFilter = 'ALL';
      this.searchTerm = '';
      
      // Clear localStorage filters as well
      localStorage.removeItem('hass_ai_min_weight');
      localStorage.removeItem('hass_ai_category_filter');
      
      this._showSimpleNotification(
        isItalian ? '🗑️ Tutti i dati sono stati cancellati. Aggiornamento della pagina...' : 
                   '🗑️ All data cleared. Refreshing page...',
        'success'
      );
      
      // Force a page refresh after a short delay to ensure clean state
      setTimeout(() => {
        window.location.reload();
      }, 1500);
      
    } catch (error) {
      console.error('Error resetting data:', error);
      this._showSimpleNotification(
        isItalian ? '❌ Errore durante la cancellazione dei dati' : 
                   '❌ Error clearing data',
        'error'
      );
    } finally {
      this.loading = false;
    }
  }

  async _showConfirmDialog(title, message, confirmText, cancelText) {
    // Use browser's native confirm dialog for simplicity and reliability
    const fullMessage = `${title}\n\n${message}`;
    return confirm(fullMessage);
  }

  _renderAlertConfigPanel(isItalian) {
    // Get only ALERTS entities that are currently visible in the filter
    const alertEntities = Object.entries(this.entities)
      .filter(([entityId, entity]) => {
        const categories = Array.isArray(entity.category) ? entity.category : [entity.category];
        if (!categories.includes('ALERTS')) return false;
        
        // Apply the same filtering logic as the main table
        const weight = this.overrides[entityId]?.overall_weight ?? entity.overall_weight;
        const matchesWeight = weight >= this.minWeight;
        
        // Category filter - if not showing ALL, only show entities that match current category filter
        const matchesCategory = this.categoryFilter === 'ALL' || categories.includes(this.categoryFilter);
        
        return matchesWeight && matchesCategory;
      });

    const availableServices = this._getAvailableNotificationServices();

    return html`
      <div class="alert-config-panel">
        <div class="alert-status">
          <h3>${isItalian ? '📊 Stato Monitoraggio Alert' : '📊 Alert Monitoring Status'}</h3>
          <div class="status-grid">
            <div class="status-item monitoring-toggle">
              <span class="status-label">${isItalian ? 'Monitoraggio:' : 'Monitoring:'}</span>
              <div class="monitoring-control">
                <span class="status-value ${this.alertStatus.monitoring_enabled ? 'enabled' : 'disabled'}">
                  ${this.alertStatus.monitoring_enabled ? 
                    (isItalian ? '✅ Attivo' : '✅ Active') : 
                    (isItalian ? '❌ Inattivo' : '❌ Inactive')
                  }
                </span>
                <ha-button
                  outlined
                  @click=${() => this._toggleAlertMonitoring()}
                  class="monitoring-btn ${this.alertStatus.monitoring_enabled ? 'stop' : 'start'}"
                >
                  ${this.alertStatus.monitoring_enabled ? 
                    (isItalian ? '🛑 Disattiva' : '🛑 Disable') :
                    (isItalian ? '▶️ Attiva' : '▶️ Enable')
                  }
                </ha-button>
              </div>
            </div>
            <div class="status-item">
              <span class="status-label">${isItalian ? 'Entità monitorate:' : 'Monitored entities:'}</span>
              <span class="status-value">${this.alertStatus.total_monitored || 0}</span>
            </div>
            <div class="status-item">
              <span class="status-label">${isItalian ? 'Alert attivi:' : 'Active alerts:'}</span>
              <span class="status-value alert-count">
                ${Object.keys(this.alertStatus.active_alerts || {}).length}
              </span>
            </div>
          </div>
        </div>

        <!-- Debug Section for ALERTS entities -->
        <div class="debug-section">
          <h3>${isItalian ? '🐛 Debug: Entità ALERTS Visibili (Filtrate)' : '🐛 Debug: Visible ALERTS Entities (Filtered)'}</h3>
          ${alertEntities.length > 0 ? html`
            <div class="debug-info">
              <p>${isItalian ? 
                `Trovate ${alertEntities.length} entità ALERTS visibili con filtro peso ≥ ${this.minWeight} e categoria "${this.categoryFilter}":` : 
                `Found ${alertEntities.length} visible ALERTS entities with weight ≥ ${this.minWeight} and category "${this.categoryFilter}":`
              }</p>
              <ul class="debug-list">
                ${alertEntities.map(([entityId, entity]) => html`
                  <li>
                    <strong>${entityId}</strong> 
                    (${isItalian ? 'Peso' : 'Weight'}: ${entity.overall_weight || 'N/A'}, 
                     ${isItalian ? 'Stato' : 'State'}: ${this.hass.states[entityId]?.state || 'unknown'})
                  </li>
                `)}
              </ul>
            </div>
          ` : html`
            <div class="debug-warning">
              <p>⚠️ ${isItalian ? 
                `Nessuna entità ALERTS visibile con peso ≥ ${this.minWeight} e categoria "${this.categoryFilter}".` : 
                `No ALERTS entities visible with weight ≥ ${this.minWeight} and category "${this.categoryFilter}".`
              }</p>
              <p>${isItalian ? 
                'Prova a ridurre il peso minimo o cambiare il filtro di categoria, oppure esegui una nuova analisi AI.' : 
                'Try reducing the minimum weight or changing the category filter, or run a new AI analysis.'
              }</p>
            </div>
          `}
        </div>

        <div class="notification-config">
          <h3>${isItalian ? '🔔 Configurazione Notifiche' : '🔔 Notification Configuration'}</h3>
          
          <div class="config-row">
            <label>
              <input 
                type="radio" 
                name="alert-mode" 
                .checked=${!this.alertStatus.use_input_text}
                @change=${() => this._toggleAlertMode(false)}
              />
              ${isItalian ? 'Servizio di Notifica' : 'Notification Service'}
            </label>
          </div>
          
          ${!this.alertStatus.use_input_text ? html`
            <div class="config-row">
              <label>${isItalian ? 'Servizio:' : 'Service:'}</label>
              <select 
                .value=${this.alertStatus.notification_service}
                @change=${(e) => this._configureAlertService({notification_service: e.target.value})}
                class="service-select"
              >
                ${availableServices.map(service => html`
                  <option value=${service.id} ?selected=${service.id === this.alertStatus.notification_service}>
                    ${service.name}
                  </option>
                `)}
              </select>
            </div>
          ` : ''}
          
          <div class="config-row">
            <label>
              <input 
                type="radio" 
                name="alert-mode" 
                .checked=${this.alertStatus.use_input_text}
                @change=${() => this._toggleAlertMode(true)}
              />
              ${isItalian ? 'Input Text Entity' : 'Input Text Entity'}
            </label>
          </div>
          
          ${this.alertStatus.use_input_text ? html`
            <div class="config-row">
              <label>${isItalian ? 'Entity ID:' : 'Entity ID:'}</label>
              <input 
                type="text" 
                .value=${this.alertStatus.input_text_entity}
                @change=${(e) => this._updateInputTextEntity(e.target.value)}
                placeholder="input_text.hass_ai_alerts"
                class="entity-input"
              />
              <div class="entity-status">
                ${this.alertStatus.input_text_exists ? 
                  html`<span class="status-ok">✅ ${isItalian ? 'Esiste' : 'Exists'}</span>` :
                  html`<span class="status-error">❌ ${isItalian ? 'Non trovato' : 'Not found'}</span>`
                }
              </div>
            </div>
            
            ${this.alertStatus.input_text_exists && this.alertStatus.input_text_entity ? html`
              <div class="config-row">
                <label>${isItalian ? 'Valore Attuale:' : 'Current Value:'}</label>
                <div class="current-value">
                  ${this.hass.states[this.alertStatus.input_text_entity]?.state || isItalian ? 'Non disponibile' : 'Not available'}
                </div>
              </div>
              <div class="config-row">
                <button 
                  class="clear-button"
                  @click=${this._clearInputTextValue}
                >
                  🗑️ ${isItalian ? 'Cancella Alert' : 'Clear Alert'}
                </button>
              </div>
            ` : ''}
            
            ${!this.alertStatus.input_text_exists ? html`
              <div class="config-help">
                <h4>${isItalian ? '📝 Configurazione Automatica' : '📝 Automatic Setup'}</h4>
                <p>${isItalian ? 'Posso creare automaticamente l\'entità input_text per te!' : 'I can create the input_text entity automatically for you!'}</p>
                <div class="auto-config-actions">
                  <ha-button 
                    raised
                    @click=${this._createInputTextEntity}
                    class="create-entity-btn"
                  >
                    ${isItalian ? '✨ Crea Entità Automaticamente' : '✨ Create Entity Automatically'}
                  </ha-button>
                </div>
                <details class="manual-config">
                  <summary>${isItalian ? 'Configurazione manuale (se preferisci)' : 'Manual configuration (if you prefer)'}</summary>
                  <p>${isItalian ? 'Aggiungi al tuo configuration.yaml:' : 'Add to your configuration.yaml:'}</p>
                  <pre><code>input_text:
  hass_ai_alerts:
    name: "HASS AI Alerts"
    max: 1000
    icon: mdi:alert-circle
    initial: "No alerts"</code></pre>
                  <p><em>${isItalian ? 'Poi riavvia Home Assistant' : 'Then restart Home Assistant'}</em></p>
                </details>
              </div>
            ` : ''}
          ` : ''}

          <div class="alert-example">
            <h4>${isItalian ? '📝 Esempio di Messaggio Alert' : '📝 Alert Message Example'}</h4>
            <div class="example-message">
              ${this._generateAlertMessageExample()}
            </div>
          </div>
        </div>

        <div class="alert-info">
          <h4>${isItalian ? 'ℹ️ Come Funziona' : 'ℹ️ How It Works'}</h4>
          <ul>
            <li>${isItalian ? 
              'Le entità con peso 5 vengono controllate ogni 30 secondi' :
              'Weight 5 entities are checked every 30 seconds'
            }</li>
            <li>${isItalian ? 
              'Le entità con peso 1 vengono controllate ogni 30 minuti' :
              'Weight 1 entities are checked every 30 minutes'
            }</li>
            <li>${isItalian ? 
              'Gli alert vengono raggruppati e inviati tramite AI intelligente' :
              'Alerts are grouped and sent via intelligent AI'
            }</li>
            <li>${isItalian ? 
              'Sistema di throttling previene spam di notifiche' :
              'Throttling system prevents notification spam'
            }</li>
          </ul>
        </div>
      </div>
    `;
  }
}

customElements.define("hass-ai-panel", HassAiPanel);
