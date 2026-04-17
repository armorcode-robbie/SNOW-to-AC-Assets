#!/usr/bin/env python3
"""
Convert customer ServiceNow export (u_server_app_service.csv) to ArmorCode asset import format.

Fields that map directly to ArmorCode columns are placed there.
All remaining fields are concatenated into a pipe-delimited tags string
in the format "key:value|key:value".

The input CSV uses human-readable column names (e.g. "Server", "IP Address").
Some column names appear more than once in the header row; for any duplicated
header, we merge values across instances, preferring whichever one is non-empty.
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
    "Server":             "name",
    "MAC Address":        "macAddress",
    "IP Address":         "ipv4",
    "Operating System":   "os",
    "OS Version":         "osVersion",
    "Operational status": "instanceStatus",
    "Environment":        "location",
    "DPO (former DM)":    "owner",
}

# Also copy Server into hostname so ArmorCode correlation works
HOSTNAME_SOURCE = "Server"

# Columns that map directly (values of FIELD_MAP + hostname)
MAPPED_CUSTOMER_COLS = set(FIELD_MAP.keys())

# Mapped columns that should ALSO be emitted as tags, in addition to populating
# their direct ArmorCode field. Useful for fields that customers want to filter
# on or see in the tag view even though they're already structured.
ALSO_TAG_COLUMNS = {
    "Operational status",
    "Environment",
    "DPO (former DM)",
}

# Explicit tag-key overrides. For columns whose header changed from the old
# snake_case format but where we want to keep emitting the original tag key
# for downstream compatibility.
TAG_KEY_OVERRIDES = {
    "APM ID": "service_u_apm_id",
}

# --- Helpers -----------------------------------------------------------------

def clean_value(val):
    """Strip whitespace and normalize multiline fields into a single line."""
    if val is None:
        return ""
    return " ".join(val.split()).strip()


def row_to_dict(headers, values):
    """Merge a row's values into a dict keyed on header name.

    The new CSV format contains duplicate column names in the header row
    (e.g. "Operational status" appears twice). For each duplicated header
    we keep whichever instance has a non-empty value, preferring the first
    non-empty one encountered.
    """
    merged = {}
    for h, v in zip(headers, values):
        v = clean_value(v)
        if h not in merged or (not merged[h] and v):
            merged[h] = v
    return merged


def build_tags(row, customer_columns):
    """Build a pipe-delimited tag string from all unmapped, non-empty fields."""
    tags = []
    seen = set()
    for col in customer_columns:
        # Skip mapped columns unless they're explicitly also emitted as tags
        if col in MAPPED_CUSTOMER_COLS and col not in ALSO_TAG_COLUMNS:
            continue
        # Skip duplicate headers — row_to_dict already merged them
        if col in seen:
            continue
        seen.add(col)

        val = row.get(col, "")
        if not val:
            continue

        # Apply tag-key override if one exists for this column
        key = TAG_KEY_OVERRIDES.get(col, col)

        # Sanitize the key and value for tag format
        safe_key = key.replace("|", "_").replace(":", "_")
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
        reader = csv.reader(infile)
        try:
            customer_columns = next(reader)
        except StopIteration:
            print("Error: Could not read headers from input file.", file=sys.stderr)
            sys.exit(1)

        if not customer_columns:
            print("Error: Empty header row.", file=sys.stderr)
            sys.exit(1)

        rows_out = []
        for values in reader:
            # Pad/truncate values to header length so zip() doesn't drop cells
            if len(values) < len(customer_columns):
                values = values + [""] * (len(customer_columns) - len(values))

            row = row_to_dict(customer_columns, values)

            out = {col: "" for col in ARMORCODE_COLUMNS}

            # Apply direct mappings
            for src, dst in FIELD_MAP.items():
                out[dst] = row.get(src, "")

            # hostname = Server
            out["hostname"] = row.get(HOSTNAME_SOURCE, "")

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
