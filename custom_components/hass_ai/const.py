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
