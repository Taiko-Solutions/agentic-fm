# FMSConfigUpgrader

> Status: **exploration** | Created: 2026-03-20

## Overview

`FMSConfigUpgrader` is a command-line utility that ships with FileMaker Server. It upgrades FMS configuration files from one server version to another.

## Where It Runs

This tool is installed on every FileMaker Server at:
```
/opt/FileMaker/FileMaker Server/Database Server/bin/FMSConfigUpgrader
```

**In the agentic-fm context**, this tool is the most specialized and narrowly scoped of the three CLI tools. It has a single purpose: upgrading configuration files during FMS version migrations.

## Command Reference

```
Usage: Upgrade from_vers from_file to_file
```

| Parameter | Purpose |
|---|---|
| `from_vers` | The FMS version number the config file was created with |
| `from_file` | Path to the source configuration file |
| `to_file` | Path to write the upgraded configuration file |

---

## What It Does

When FileMaker Server is upgraded from one major version to another (e.g., FMS 20 → FMS 21), its configuration files may need structural changes — new keys, deprecated settings, format changes. `FMSConfigUpgrader` handles this translation automatically.

FMS configuration files include:
- Server-level settings (max connections, cache size, logging)
- Security configuration (SSL, authentication)
- Web Publishing Engine settings
- Backup schedule definitions
- Progressive download settings
- ODBC/JDBC configuration

---

## Relevance to agentic-fm

This tool has **limited direct relevance** to the agentic-fm workflow. It's useful in one specific scenario:

### FMS Version Migration

When the development environment upgrades FMS versions (e.g., updating the Docker container's FMS image), configuration files from the previous version need upgrading. If `automation.json` references FMS-specific settings that depend on config file values, the agent should be aware that a version upgrade may invalidate those settings.

### Docker Environment

In the current Docker-based architecture, FMS configuration is typically handled during container build or through environment variables. However, if the FMS container uses persistent volume mounts for configuration, `FMSConfigUpgrader` can ensure config compatibility after image updates.

---

## Server-Side Execution

Unlike `FMDeveloperTool` and `FMDataMigration`, this tool is typically run once during an upgrade — not as part of a recurring workflow. It would most likely be called from:
- A Docker entrypoint script during container startup
- A manual upgrade procedure
- An FMS upgrade automation script

---

## Next Steps

1. **Document FMS config file locations** — identify which config files exist in the Docker FMS container and their paths
2. **Assess upgrade automation** — determine if this tool should be part of an automated FMS Docker image upgrade workflow
3. **Low priority** — this tool doesn't impact the core agentic-fm skills pipeline
