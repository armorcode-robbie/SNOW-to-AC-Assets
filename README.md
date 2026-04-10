# SNOW-to-AC-Assets

Convert ServiceNow server/app service CSV exports into the ArmorCode asset import format.

## What it does

Reads `u_server_app_service.csv` (a ServiceNow export) and produces `armorcode_assets_import.csv` with columns matching the ArmorCode asset import template. Fields that don't map directly to an ArmorCode column are concatenated into a pipe-delimited `tags` string (`key:value|key:value`).

### Field mapping

| ServiceNow column | ArmorCode column |
|---|---|
| `server_name` | `name`, `hostname` |
| `server_mac_address` | `macAddress` |
| `server_ip_address` | `ipv4` |
| `server_os` | `os` |
| `server_os_version` | `osVersion` |
| `server_operational_status` | `instanceStatus` |
| `server_environment` | `location` |
| `service_delivery_manager` | `owner` |

All assets are assigned `type=HOST` and `source=ServiceNow` by default.

## Usage

1. Place `u_server_app_service.csv` in the same directory as the script.
2. Run:

```bash
python convert_assets.py
```

3. The output file `armorcode_assets_import.csv` will be created in the same directory.

## Requirements

Python 3 (standard library only — no extra dependencies).
