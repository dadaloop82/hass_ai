# API Keys Configuration Guide

This guide explains how to obtain and configure API keys for external AI providers in HASS AI.

## 🤖 AI Provider Options

HASS AI supports three AI providers:

1. **Home Assistant Conversation Agent** (Default) - Uses your configured HA conversation integration
2. **OpenAI GPT** - Requires OpenAI API key
3. **Google Gemini** - Requires Google AI Studio API key

## 🔑 Getting API Keys

### OpenAI API Key

1. **Create OpenAI Account**
   - Go to [OpenAI Platform](https://platform.openai.com/)
   - Sign up or log in to your account

2. **Generate API Key**
   - Navigate to [API Keys page](https://platform.openai.com/api-keys)
   - Click "Create new secret key"
   - Give it a name (e.g., "HASS AI")
   - Copy the generated key (starts with `sk-`)

3. **Important Notes**
   - ⚠️ **Save the key immediately** - you won't be able to see it again
   - 💰 OpenAI API is **pay-per-use** - check [pricing](https://openai.com/pricing)
   - 🔒 Keep your API key secure and never share it publicly

### Google Gemini API Key

1. **Access Google AI Studio**
   - Go to [Google AI Studio](https://aistudio.google.com/)
   - Sign in with your Google account

2. **Generate API Key**
   - Navigate to [API Keys section](https://aistudio.google.com/app/apikey)
   - Click "Create API Key"
   - Choose your Google Cloud project or create a new one
   - Copy the generated key

3. **Important Notes**
   - 🆓 Google Gemini has a **generous free tier**
   - 📊 Monitor usage in Google Cloud Console
   - 🔒 Keep your API key secure

## ⚙️ Configuration in HASS AI

### Initial Setup

1. **Add Integration**
   - Go to Settings → Devices & Services
   - Click "Add Integration"
   - Search for "HASS AI"

2. **Choose AI Provider**
   - **Conversation**: No additional setup needed
   - **OpenAI**: You'll be prompted for your API key
   - **Gemini**: You'll be prompted for your API key

3. **Enter API Key**
   - Paste your API key when prompted
   - Click "Submit"

### Changing AI Provider

1. **Access Integration Options**
   - Go to Settings → Devices & Services
   - Find "HASS AI" integration
   - Click "Configure"

2. **Update Settings**
   - Change AI provider if needed
   - Update API key if switching to external provider
   - Save changes

## 🔍 Verification

After configuration, the integration will:

- ✅ Test the API connection
- ✅ Display the active AI provider in logs
- ✅ Show analysis method in the panel results

## 💡 Recommendations

### For Beginners
- Start with **Conversation Agent** (free, uses your HA setup)
- Upgrade to external providers for better analysis quality

### For Advanced Users
- **OpenAI GPT-3.5**: Excellent balance of cost and quality
- **Google Gemini**: Great free tier, good for experimentation

### Cost Optimization
- Use **batch analysis** (default: 10 entities per batch)
- Monitor API usage in provider dashboards
- Consider conversation agent for basic needs

## 🚨 Troubleshooting

### Common Issues

1. **Invalid API Key**
   - Double-check the key is copied correctly
   - Ensure no extra spaces or characters
   - Verify the key hasn't expired

2. **API Quota Exceeded**
   - Check your usage in provider dashboard
   - Add payment method if needed
   - Consider switching to conversation agent temporarily

3. **Network Issues**
   - Check internet connectivity
   - Verify firewall settings
   - Integration will fallback to conversation agent

### Support

- 📖 [Documentation](https://github.com/dadaloop82/hass_ai)
- 🐛 [Issues](https://github.com/dadaloop82/hass_ai/issues)
- 💬 [Discussions](https://github.com/dadaloop82/hass_ai/discussions)

---

**Security Note**: Never commit API keys to version control or share them publicly. HASS AI stores keys securely in Home Assistant's encrypted storage.
