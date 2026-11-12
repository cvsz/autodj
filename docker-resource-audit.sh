#!/usr/bin/env bash
set -Eeuo pipefail

# ============================================================
# Docker & WSL2 Resource Audit
# Read-only diagnostics — does not stop or modify services.
# Output: ./logs/docker-resource-audit-YYYYMMDD-HHMMSS.log
# ============================================================

TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
LOG_DIR="${PWD}/logs"
LOG_FILE="${LOG_DIR}/docker-resource-audit-${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

exec > >(tee -a "$LOG_FILE") 2>&1

section() {
    printf '\n\n'
    printf '%s\n' "============================================================"
    printf '===== %s =====\n' "$1"
    printf '%s\n' "============================================================"
}

run() {
    local description="$1"
    shift

    printf '\n--- %s ---\n' "$description"

    if ! command -v "$1" >/dev/null 2>&1; then
        printf '[SKIPPED] Command not installed: %s\n' "$1"
        return 0
    fi

    "$@" || {
        local status=$?
        printf '[WARNING] Command failed (exit %s): %s\n' "$status" "$description"
        return 0
    }
}

section "AUDIT METADATA"
printf 'Timestamp: %s\n' "$(date --iso-8601=seconds)"
printf 'Hostname:  %s\n' "$(hostname)"
printf 'Kernel:    %s\n' "$(uname -r)"
printf 'User:      %s\n' "$(id)"
printf 'Log file:  %s\n' "$LOG_FILE"

section "DOCKER RESOURCE USAGE"
run "Container resource usage" docker stats --no-stream

section "CME API LOGS"
run "CME API recent logs" docker logs --timestamps --tail 150 cme-p0-drill-api-1

section "ZCODER LLM LOGS"
run "ZCoder LLM recent logs" docker logs --timestamps --tail 100 zcoder-llm

section "POSTGRESQL INSTANCES"
run "PostgreSQL cluster inventory" pg_lsclusters

section "DOCKER VOLUME REFERENCES"
run "Docker volume inventory" docker volume ls
run "Docker disk usage and volume details" docker system df -v

section "FIREWALL RULES"
run "nftables ruleset" sudo nft list ruleset
run "iptables IPv4 rules" sudo iptables -S
run "iptables IPv6 rules" sudo ip6tables -S

section "LISTENING PORTS"
run "Listening TCP/UDP sockets" sudo ss -tulpn

section "SNAP PACKAGES"
run "Installed Snap packages" snap list

section "DOCKER NETWORKS"
run "Docker network inventory" docker network ls

section "DOCKER COMPOSE PROJECTS"
run "Compose project inventory" docker compose ls --all

section "DOCKER CONTAINER INVENTORY"
run "All containers and states" docker ps -a --no-trunc

section "SYSTEM MEMORY"
run "Memory usage" free -h

section "DISK SPACE"
run "Filesystem usage" df -h

section "SYSTEMD SERVICES"
run "Running services" systemctl list-units --type=service --state=running --no-pager

section "AUDIT COMPLETE"
printf 'Completed: %s\n' "$(date --iso-8601=seconds)"
printf 'Report: %s\n' "$LOG_FILE"
printf '\nNo containers, images, networks, or volumes were intentionally modified.\n'
