#!/usr/bin/env bash
# Test script to demonstrate the results-tracking framework

# Colors
c_green="\033[1;32m"; c_yellow="\033[1;33m"; c_red="\033[1;31m"; c_blue="\033[1;34m"; c_reset="\033[0m"

# Results tracking
declare -A STEP_STATUS

# Helper function for logging step results
log_step() {
  STEP_STATUS["$1"]=$2
  if [[ $2 == "OK" ]]; then
    echo -e "${c_green}✓ $1${c_reset}"
  else
    echo -e "${c_red}✗ $1 ($3)${c_reset}"
  fi
}

echo -e "${c_blue}==== Test Results Tracking ====${c_reset}"
echo

# Test step 1 - This will succeed
if (
  echo "Running step 1..."
  true  # This always succeeds
); then
  log_step "Step 1: Success test" OK
else
  log_step "Step 1: Success test" FAIL "$?"
fi

# Test step 2 - This will fail
if (
  echo "Running step 2..."
  false  # This always fails
); then
  log_step "Step 2: Failure test" OK
else
  log_step "Step 2: Failure test" FAIL "$?"
fi

# Test step 3 - This will succeed
if (
  echo "Running step 3..."
  ls /tmp >/dev/null 2>&1  # Should succeed
); then
  log_step "Step 3: Command test" OK
else
  log_step "Step 3: Command test" FAIL "$?"
fi

echo
echo -e "${c_blue}Summary:${c_reset}"
for step in "Step 1: Success test" "Step 2: Failure test" "Step 3: Command test"; do
  if [[ "${STEP_STATUS[$step]}" == "OK" ]]; then
    echo -e "  ${c_green}✓${c_reset} $step"
  elif [[ "${STEP_STATUS[$step]}" == "FAIL" ]]; then
    echo -e "  ${c_red}✗${c_reset} $step"
  else
    echo -e "  ${c_yellow}?${c_reset} $step (not executed)"
  fi
done
