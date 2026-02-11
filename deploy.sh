#!/bin/bash

# VitalCore - Cloudflare Pages Deployment Script

echo "========================================"
echo "🚀 VitalCore Deployment to Cloudflare"
echo "========================================"

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "📦 Installing Cloudflare Wrangler..."
    npm install -g wrangler
fi

# Login to Cloudflare (if not already logged in)
echo ""
echo "🔐 Please login to Cloudflare:"
wrangler login

# Create or deploy to Cloudflare Pages
echo ""
echo "🌐 Deploying to Cloudflare Pages..."

# Option 1: Direct upload (for Pages)
wrangler pages deploy . --project-name=vital-core

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌍 Your website will be available at:"
echo "   https://vital-core.pages.dev"
echo ""
echo "🔗 Custom domain: https://vital-core.site"
echo ""
echo "========================================"
