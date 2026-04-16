#!/bin/bash

# Test webhook with sample PagerDuty alert

echo "🧪 Testing ShiftZero webhook..."

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Server is not running!"
    echo "Start it with: python -m uvicorn shiftzero.webhook:app --reload"
    exit 1
fi

echo "✅ Server is running"
echo ""
echo "📤 Sending sample PagerDuty alert..."
echo ""

# Send sample alert
response=$(curl -s -X POST http://localhost:8000/webhook/pagerduty \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/sample_pagerduty_alert.json)

echo "📥 Response:"
echo "$response" | python3 -m json.tool

echo ""
echo "✅ Test complete! Check server logs for agent activity."
