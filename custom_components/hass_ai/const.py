"""Constants for the HASS AI integration."""

DOMAIN = "hass_ai"

# AI Provider options - Only Local Agent supported
AI_PROVIDER_LOCAL = "Local Agent"

AI_PROVIDERS = [AI_PROVIDER_LOCAL]

# Default values
DEFAULT_SCAN_INTERVAL = 7  # days
DEFAULT_BATCH_SIZE = 10    # entities per batch
DEFAULT_AI_PROVIDER = AI_PROVIDER_LOCAL

# Entity importance levels
IMPORTANCE_IGNORE = 0
IMPORTANCE_VERY_LOW = 1
IMPORTANCE_LOW = 2
IMPORTANCE_MEDIUM = 3
IMPORTANCE_HIGH = 4
IMPORTANCE_CRITICAL = 5

# Storage keys
STORAGE_KEY_OVERRIDES = "overrides"
STORAGE_KEY_LAST_SCAN = "last_scan"
STORAGE_KEY_VERSION = "version"
