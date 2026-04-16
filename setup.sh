#!/bin/bash

# ShiftZero Setup Script

set -e

echo "🚀 Setting up ShiftZero..."

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your AWS credentials and API keys!"
fi

# Start PostgreSQL (optional for Phase 1)
echo "🐘 Starting PostgreSQL..."
if command -v docker &> /dev/null && (command -v docker-compose &> /dev/null || docker compose version &> /dev/null); then
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d postgres
    else
        docker compose up -d postgres
    fi
    echo "⏳ Waiting for PostgreSQL to be ready..."
    sleep 5
else
    echo "⚠️  Docker/Docker Compose not found. Skipping PostgreSQL setup."
    echo "   (Phase 1 MVP works without database - state is in-memory)"
fi

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your credentials"
echo "2. Run: source venv/bin/activate"
echo "3. Run: python -m uvicorn shiftzero.webhook:app --reload"
echo "4. Test with: curl http://localhost:8000/health"
echo ""
echo "For testing, see: tests/test_webhook.sh"
