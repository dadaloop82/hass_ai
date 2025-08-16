"""Constants for the HASS AI integration."""

DOMAIN = "hass_ai"
CONF_AI_PROVIDER = "ai_provider"
CONF_CONVERSATION_AGENT = "conversation_agent"
CONF_SCAN_INTERVAL = "scan_interval"

# AI Provider options - Only Local Agent supported
AI_PROVIDER_LOCAL = "Local Agent"

AI_PROVIDERS = [AI_PROVIDER_LOCAL]

# Default values
DEFAULT_SCAN_INTERVAL = 7  # days
DEFAULT_BATCH_SIZE = 2     # entities per batch - Ultra-small for token safety
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

# Alert monitoring constants
ALERT_MONITORING_ENABLED = "alert_monitoring_enabled"
ALERT_NOTIFICATION_SERVICE = "alert_notification_service"
ALERT_NOTIFICATION_TARGET = "alert_notification_target"
ALERT_LAST_NOTIFICATIONS = "alert_last_notifications"

# Alert monitoring intervals (in seconds)
ALERT_INTERVAL_WEIGHT_5 = 30      # Critical alerts every 30 seconds
ALERT_INTERVAL_WEIGHT_1 = 1800    # Low alerts every 30 minutes
ALERT_MIN_INTERVAL = 30           # Minimum interval between same entity alerts
ALERT_THROTTLE_TIME = 300         # 5 minutes throttle for repeated alerts

# Token limit management
MAX_TOKEN_ERROR_KEYWORDS = [
    "exceed",
    "maximum",
    "limit",
    "token",
    "too long",
    "too many",
    "context length",
    "input too large",
    "quota",
    "rate limit"
]

# Dynamic batch size management
MIN_BATCH_SIZE = 1
MAX_BATCH_SIZE = 50
DEFAULT_BATCH_SIZE = 10
BATCH_REDUCTION_FACTOR = 0.8  # Reduce by 20% each time

# Error messages for token limits
TOKEN_LIMIT_ERROR_MESSAGE = (
    "⚠️ Token limit exceeded! The conversation agent has reached its maximum token capacity. "
    "To resolve this issue:\n\n"
    "🔧 **Recommended Solutions:**\n"
    "• Increase the max_tokens parameter in your conversation agent configuration\n"
    "• Reduce the batch size in HASS AI settings (try 5-8 entities per batch)\n"
    "• Use a conversation agent with higher token limits\n\n"
    "📊 **Current batch was stopped to prevent errors.**"
)
