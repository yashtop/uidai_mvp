#!/bin/bash
# server/scripts/test_all_modes.sh - COMPREHENSIVE TEST

set -e

API_URL="http://localhost:8000"

echo "============================================"
echo "Testing All Modes: AI, Record, Hybrid"
echo "============================================"

# Clean old runs
rm -rf /tmp/uidai_runs/*

# Test 1: AI Mode (Automated)
echo ""
echo "=========================================="
echo "Test 1: AI Mode (Fully Automated)"
echo "=========================================="

AI_RESPONSE=$(curl -s -X POST "$API_URL/api/run" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.aubank.in/",
    "testCreationMode": "ai",
    "story": "Test homepage: verify page loads, check navigation menu, test search",
    "mode": "headless",
    "preset": "quick"
  }')

AI_RUN_ID=$(echo "$AI_RESPONSE" | jq -r '.runId')
echo "AI Run ID: $AI_RUN_ID"

# Wait for AI mode
echo "Waiting for AI mode to complete..."
for i in {1..60}; do
  STATUS=$(curl -s "$API_URL/api/run/$AI_RUN_ID" | jq -r '.status')
  if [ "$STATUS" == "completed" ] || [ "$STATUS" == "failed" ]; then
    break
  fi
  echo -n "."
  sleep 2
done
echo ""

curl -s "$API_URL/api/run/$AI_RUN_ID" | jq '{status, phase, testsTotal, testsPassed, testsFailed}'

# Test 2: Record Mode (Manual)
echo ""
echo "=========================================="
echo "Test 2: Record Mode (Manual Recording)"
echo "=========================================="

read -p "Start Record mode? Browser will open for manual recording [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    RECORD_RESPONSE=$(curl -s -X POST "$API_URL/api/run" \
      -H "Content-Type: application/json" \
      -d '{
        "url": "https://www.aubank.in/",
        "testCreationMode": "record",
        "mode": "headed"
      }')
    
    RECORD_RUN_ID=$(echo "$RECORD_RESPONSE" | jq -r '.runId')
    echo "Record Run ID: $RECORD_RUN_ID"
    echo ""
    echo "⚠️  Browser will open - perform your test, then close browser"
    echo "⏳ Waiting for recording..."
    
    # Wait longer for manual recording
    for i in {1..300}; do
      STATUS=$(curl -s "$API_URL/api/run/$RECORD_RUN_ID" | jq -r '.status')
      if [ "$STATUS" == "completed" ] || [ "$STATUS" == "failed" ]; then
        break
      fi
      sleep 2
    done
    
    curl -s "$API_URL/api/run/$RECORD_RUN_ID" | jq '{status, phase, testsTotal, testsPassed}'
else
    echo "Skipping Record mode"
fi

# Test 3: Hybrid Mode
echo ""
echo "=========================================="
echo "Test 3: Hybrid Mode (Record + AI)"
echo "=========================================="

read -p "Start Hybrid mode? Browser will open for recording first [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    HYBRID_RESPONSE=$(curl -s -X POST "$API_URL/api/run" \
      -H "Content-Type: application/json" \
      -d '{
        "url": "https://www.aubank.in/",
        "testCreationMode": "hybrid",
        "story": "Add edge cases: test with invalid inputs, empty fields, and error scenarios",
        "mode": "headless",
        "preset": "balanced"
      }')
    
    HYBRID_RUN_ID=$(echo "$HYBRID_RESPONSE" | jq -r '.runId')
    echo "Hybrid Run ID: $HYBRID_RUN_ID"
    echo ""
    echo "⚠️  Browser will open for recording"
    echo "   1. Record your main workflow"
    echo "   2. Close browser when done"
    echo "   3. AI will generate additional tests"
    echo ""
    
    # Wait for hybrid mode
    for i in {1..300}; do
      STATUS=$(curl -s "$API_URL/api/run/$HYBRID_RUN_ID" | jq -r '.status')
      PHASE=$(curl -s "$API_URL/api/run/$HYBRID_RUN_ID" | jq -r '.phase')
      echo "Status: $STATUS | Phase: $PHASE"
      
      if [ "$STATUS" == "completed" ] || [ "$STATUS" == "failed" ]; then
        break
      fi
      sleep 3
    done
    
    curl -s "$API_URL/api/run/$HYBRID_RUN_ID" | jq '{status, phase, testsTotal, testsPassed, testsFailed, storySource}'
else
    echo "Skipping Hybrid mode"
fi

echo ""
echo "============================================"
echo "All Tests Complete"
echo "============================================"

# Summary
echo ""
echo "Run IDs:"
echo "  AI Mode:     $AI_RUN_ID"
[ -n "$RECORD_RUN_ID" ] && echo "  Record Mode: $RECORD_RUN_ID"
[ -n "$HYBRID_RUN_ID" ] && echo "  Hybrid Mode: $HYBRID_RUN_ID"