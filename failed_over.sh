#!/bin/bash

failed=0
green_count=0
total=10

echo "Testing failover stability..."

for i in $(seq 1 $total); do
  # Get response with status code
  response=$(curl -s http://13.247.176.63:8080/version)
  http_code=$(curl -s -o /dev/null -w "%{http_code}" http://13.247.176.63:8080/version)
  
  # Extract pool from JSON response
  pool=$(echo "$response" | grep -o '"APP_POOL":"[^"]*"' | cut -d'"' -f4)
  
  # If grep fails, try alternative parsing
  if [ -z "$pool" ]; then
    pool=$(echo "$response" | sed -n 's/.*"APP_POOL":"\([^"]*\)".*/\1/p')
  fi
  
  echo "Request $i: Status=$http_code, Pool=$pool"
  
  if [ "$http_code" != "200" ]; then
    failed=$((failed + 1))
  fi
  
  if [ "$pool" = "green" ]; then
    green_count=$((green_count + 1))
  fi
  
  sleep 0.5
done

echo ""
echo "=== RESULTS ==="
echo "Failed requests: $failed/$total"
echo "Green responses: $green_count/$total"

if [ $total -gt 0 ]; then
  percentage=$((green_count * 100 / total))
else
  percentage=0
fi

echo "Green percentage: $percentage%"

if [ $failed -eq 0 ] && [ $percentage -ge 95 ]; then
  echo "TEST PASSED"
else
  echo "TEST FAILED"
fi