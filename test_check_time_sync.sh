#!/bin/bash

# Test script for check_time_sync.sh

echo "=== Testing check_time_sync.sh ==="
echo

# Test 1: Help message
echo "Test 1: Help message"
./check_time_sync.sh --help
echo "Exit code: $?"
echo

# Test 2: Once mode
echo "Test 2: Once mode"
./check_time_sync.sh --once
echo "Exit code: $?"
echo

# Test 3: Invalid argument
echo "Test 3: Invalid argument"
./check_time_sync.sh --invalid 2>&1
echo "Exit code: $?"
echo

echo "=== All tests completed ==="
