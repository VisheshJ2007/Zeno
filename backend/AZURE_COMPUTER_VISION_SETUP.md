# Azure Computer Vision Read API Setup

## What You Need
You have Azure OpenAI keys, but OCR requires **Azure Computer Vision** (different service).

## Quick Setup (5 minutes)

### Step 1: Go to Azure Portal
**Link**: https://portal.azure.com

### Step 2: Create Computer Vision Resource
1. Click **"+ Create a resource"**
2. Search for **"Computer Vision"** or **"Azure AI Vision"**
3. Click **"Create"**

### Step 3: Configure the Resource
- **Subscription**: Use your existing subscription
- **Resource Group**: Create new or use existing
- **Region**: Choose closest to you (e.g., East US, West Europe)
- **Name**: Something like `ocr-computer-vision`
- **Pricing Tier**: Select **Free F0** (5000 requests/month free)

### Step 4: Get Your Keys
After creation (takes 1-2 minutes):
1. Go to your Computer Vision resource
2. Click **"Keys and Endpoint"** in the left menu
3. Copy:
   - **Key 1** (looks like: `abc123def456...`)
   - **Endpoint** (looks like: `https://YOUR-RESOURCE.cognitiveservices.azure.com/`)

### Step 5: Add to .env File
```env
AZURE_VISION_KEY=your_key_here
AZURE_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
```

## Free Tier Details
- **5000 transactions per month** - FREE
- **After 5000**: $1 per 1000 transactions
- **Max file size**: 50MB
- **Optimized for handwriting**

## Alternative: Use Azure Document Intelligence
If you want even better handwriting recognition:
1. Search for **"Document Intelligence"** (formerly Form Recognizer)
2. Same process as above
3. Better for structured documents and forms
4. Free tier: 500 pages/month

## Can't Find Computer Vision?
Your Azure subscription might not have it enabled. Try:
1. **Azure AI Services** (all-in-one resource that includes Vision)
2. Or create a new free Azure account

## Need Help?
Let me know if you:
- Can't find Computer Vision in Azure
- Need help with a different Azure service
- Want to use a different OCR provider
