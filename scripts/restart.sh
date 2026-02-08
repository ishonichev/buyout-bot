#!/bin/bash
# Quick restart script for development

echo "🔄 Restarting bot..."
docker-compose restart bot

echo "📋 Following logs (Ctrl+C to exit):"
docker-compose logs -f bot
