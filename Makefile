# AutoDJ Makefile - Cross-platform build and automation
# ======================================================

# Variables
PY ?= python3
BUILD_DIR ?= build
DIST_DIR ?= dist
LOG_DIR ?= logs
BUILD_LOG_DIR ?= $(LOG_DIR)/build
BUILD_LOG_TS ?= $(shell date +%Y%m%d%H%M%S)

# Targets
.PHONY: all clean win11-check mpv-check nsis-check pyinstaller-check help

all: help ## Run this target to see available help messages

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

clean:  ## Clean build artifacts
	rm -rf $(BUILD_DIR) $(DIST_DIR) $(LOG_DIR)

# SKIP_CHECKS=1 bypasses all prerequisite checks (for air-gapped / pre-validated machines)
win11-check:  ## Verify Windows 11 (build 22000+) and NSIS/mpv/PyInstaller availability
	@mkdir -p "$(BUILD_LOG_DIR)" 2>/dev/null || true
	@echo "=== Windows 11 Prerequisite Check ($(BUILD_LOG_TS)) ==="
	@ifeq ($(SKIP_CHECKS),1)
	@echo "  SKIP: prerequisite checks disabled (SKIP_CHECKS=1)" | tee -a "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log"
	@echo "  SKIP: prerequisite checks disabled (SKIP_CHECKS=1)"
	@else
	@$(PY) tools/win11_check.py win11-check 2>&1 | tee -a "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log"
	@if [ $$? -ne 0 ]; then echo "ERROR: Prerequisite checks failed. See log." >> "$(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log" 2>&1; exit 1; fi
	@endif
	@echo "Logs: $(BUILD_LOG_DIR)/win11-check-$(BUILD_LOG_TS).log"

mpv-check:  ## Check if mpv is available
	@$(PY) tools/win11_check.py mpv-check

nsis-check:  ## Check if NSIS is available
	@$(PY) tools/win11_check.py nsis-check

pyinstaller-check:  ## Check if PyInstaller is available
	@$(PY) tools/win11_check.py pyinstaller-check

.PHONY: all clean win11-check mpv-check nsis-check pyinstaller-check help
