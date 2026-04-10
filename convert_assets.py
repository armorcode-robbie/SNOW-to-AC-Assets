#!/usr/bin/env python3
"""
Convert customer ServiceNow export (u_server_app_service.csv) to ArmorCode asset import format.

Fields that map directly to ArmorCode columns are placed there.
All remaining fields are concatenated into a pipe-delimited tags string
in the format "key:value|key:value".
"""

import csv
import sys
import os

# --- Configuration -----------------------------------------------------------

INPUT_FILE = "u_server_app_service.csv"
OUTPUT_FILE = "armorcode_assets_import.csv"

# ArmorCode asset CSV columns (from assets-sample)
ARMORCODE_COLUMNS = [
    "name", "source", "type", "hostname", "dnsName", "cloudProvider",
    "os", "osVersion", "ipv4", "ipv6", "cloudAccountId", "arn",
    "macAddress", "location", "owner", "registry", "imageTag", "imageRepo",
    "cluster", "namespace", "instanceStatus", "region", "storageType",
    "publiclyAccessible", "engineVersion", "subnetIds", "vpcId", "engine",
    "role", "architecture", "runtime", "version", "cloudService", "tags"
]

# Direct field mapping: customer_column -> armorcode_column
FIELD_MAP = {
    "server_name":               "name",
    "server_mac_address":        "macAddress",
    "server_ip_address":         "ipv4",
    "server_os":                 "os",
    "server_os_version":         "osVersion",
    "server_operational_status":  "instanceStatus",
    "server_environment":        "location",
    "service_delivery_manager":  "owner",
}

# Also copy server_name into hostname
HOSTNAME_SOURCE = "server_name"

# Columns that map directly (values of FIELD_MAP + hostname)
MAPPED_CUSTOMER_COLS = set(FIELD_MAP.keys())

# --- Helpers -----------------------------------------------------------------

def clean_value(val):
    """Strip whitespace and normalize multiline fields into a single line."""
    if val is None:
        return ""
    return " ".join(val.split()).strip()


def build_tags(row, customer_columns):
    """Build a pipe-delimited tag string from all unmapped, non-empty fields."""
    tags = []
    for col in customer_columns:
        if col in MAPPED_CUSTOMER_COLS:
            continue
        val = clean_value(row.get(col, ""))
        if val:
            # Sanitize the key and value for tag format
            safe_key = col.replace("|", "_").replace(":", "_")
            safe_val = val.replace("|", " ").replace(":", " -")
            tags.append(f"{safe_key}:{safe_val}")
    return "|".join(tags)


# --- Main --------------------------------------------------------------------

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, INPUT_FILE)
    output_path = os.path.join(script_dir, OUTPUT_FILE)

    if not os.path.exists(input_path):
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        customer_columns = reader.fieldnames

        if not customer_columns:
            print("Error: Could not read headers from input file.", file=sys.stderr)
            sys.exit(1)

        rows_out = []
        for row in reader:
            out = {col: "" for col in ARMORCODE_COLUMNS}

            # Apply direct mappings
            for src, dst in FIELD_MAP.items():
                out[dst] = clean_value(row.get(src, ""))

            # hostname = server_name
            out["hostname"] = clean_value(row.get(HOSTNAME_SOURCE, ""))

            # Default type to HOST (these are servers)
            out["type"] = "HOST"

            # Default source to ServiceNow
            out["source"] = "ServiceNow"

            # Build tags from all unmapped fields
            out["tags"] = build_tags(row, customer_columns)

            rows_out.append(out)

    with open(output_path, "w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=ARMORCODE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Converted {len(rows_out)} assets -> {output_path}")


if __name__ == "__main__":
    main()
