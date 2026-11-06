# AutoDJ Camfrog Live Testing Guide

**Repository:** `cvsz/autodj`  
**Date:** 2026-11-02  

---

## 1. Overview

Camfrog live integration testing requires actual Camfrog credentials and a
Camfrog client installation. This document describes how to run live tests
safely without exposing credentials or interacting with public rooms.

## 2. Prerequisites

| Item | Requirement |
|------|-------------|
| Camfrog client | Installed on Windows 11 |
| Camfrog credentials | Operator nick and room access |
| Test room | Isolated test room (not a public room) |
| Windows host | Windows 11 (Build 22000+) |

## 3. Security Rules

| Rule | Rationale |
|------|-----------|
| Never expose credentials | Credentials never logged or committed |
| Never transmit to public rooms | Use isolated test room only |
| Never interact with unrelated users | Test only with controlled accounts |
| Mock tests separate from live tests | Mocks never represented as live evidence |

## 4. Running Live Tests

```powershell
# Unit + mock tests only (no live Camfrog)
.\tools\camfrog-qualification\Test-AutoDJCamfrogIntegration.ps1

# Live tests (requires credentials, isolated test room only)
.\tools\camfrog-qualification\Test-AutoDJCamfrogIntegration.ps1 `
    -RunLive `
    -CamfrogNick "TestBot" `
    -CamfrogRoom "QualificationTest"
```

Or using environment variables:

```powershell
$env:AUTODJ_CAMFROG_NICK = "TestBot"
$env:AUTODJ_CAMFROG_ROOM = "QualificationTest"
.\tools\camfrog-qualification\Test-AutoDJCamfrogIntegration.ps1 -RunLive
```

## 5. Test Categories

| Category | Description | Credentials Required |
|----------|-------------|---------------------|
| Unit tests | Mocked adapter behavior | No |
| Mock integration | Simulated Camfrog interaction | No |
| Live integration | Actual Camfrog session | Yes |

## 6. Live Test Scenarios

| Test ID | Description | Status |
|---------|-------------|--------|
| CAMFROG-LIVE-01 | Successful connection | Requires credentials |
| CAMFROG-LIVE-02 | Failed authentication | Requires credentials |
| CAMFROG-LIVE-03 | Room connection | Requires credentials |
| CAMFROG-LIVE-04 | Event handling | Requires credentials |
| CAMFROG-LIVE-05 | Graceful disconnect | Requires credentials |

## 7. Evidence

Live test evidence must be sanitized to remove:
- Credentials and tokens
- Personal information
- Camfrog nicknames (except operator's own)
- Room names (except test room)

## 8. Blocker Status

**No Camfrog credentials or runtime are currently available.** Live
integration testing is blocked until credentials and a Windows host with
Camfrog client are provisioned.
