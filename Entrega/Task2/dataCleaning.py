import pandas as pd
from config import cfg


def onNull(records, table):
    # This function is now updated with the 'require' logic
    if not records:
        return records

    # First, handle required fields. If a required field is null, drop the row.
    null_rule = cfg.onNull.get(table, {})
    required_fields = null_rule.get("require", [])

    if required_fields:
        original_count = len(records)

        # We need to use a standard None representation first
        def normalize(value):
            if isinstance(value, str):
                stripped = value.strip()
                if stripped.lower() in ("", "\\n", "none", "nan", "na", "n/a", "\\N"):
                    return None
            return None if pd.isna(value) else value

        records = [
            r
            for r in records
            if all(normalize(r.get(field)) is not None for field in required_fields)
        ]
        dropped_count = original_count - len(records)
        if dropped_count > 0:
            print(
                f"[INFO] Table '{table}': Dropped {dropped_count} rows due to missing required fields."
            )

    # Second, apply default or substitution logic (for backward compatibility)
    method = null_rule.get("method")
    if method == "default":
        default_values = null_rule.get("criteria", {})
        for r in records:
            for field, default in default_values.items():
                if pd.isna(r.get(field)) or r.get(field) in ("", None):
                    r[field] = default
        return records
    elif method == "substitution":
        # (This logic remains the same)
        criteria = null_rule.get("criteria", {})
        for r in records:
            for field, substitute in criteria.items():
                if pd.isna(r.get(field)) or r.get(field) in ("", None):
                    if substitute in r:
                        r[field] = r.get(substitute)
                    else:
                        r[field] = substitute
        return records

    # Default behavior if no specific 'method' is provided after require check
    return records


def onDuplicate(records, table):
    dup_rule = cfg.onDuplicateRule.get(table, "ignore")
    dup_base = cfg.onDuplicateBase.get(table)
    if not records:
        return records

    def resolve_keys(fields):
        if not fields:
            return []
        if isinstance(fields, (list, tuple, set)):
            candidates = list(fields)
        else:
            candidates = [fields]
        return [
            field
            for field in candidates
            if any(field in record for record in records)
        ]
    
    dedupe_keys = resolve_keys(dup_base)

    if not dedupe_keys:
        return records

    unique_records = []
    seen = {}

    if isinstance(dup_rule, dict) and "add" in dup_rule:
        target_field = dup_rule["add"]
        for record in records:
            key = tuple(record.get(f) for f in dedupe_keys)
            if key not in seen:
                seen[key] = record.copy()
                seen[key][target_field] = float(seen[key].get(target_field, 0) or 0)
            else:
                seen[key][target_field] += float(record.get(target_field, 0) or 0)
        unique_records = list(seen.values())
        
    elif dup_rule in ("ignore", None):
        seen_keys = set()
        for record in records:
            key = tuple(record.get(f) for f in dedupe_keys)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_records.append(record)
    else:
        raise ValueError(
            f"Unknown duplicate handling rule for table {table}: {dup_rule}"
        )
    return unique_records


def cleanData(data):
    cleaned = {}
    print("[INFO] Initializing duplicate search and null resolving")

    for table, records in data.items():
        records = onNull(records, table)
        unique_records = onDuplicate(records, table)
        cleaned[table] = unique_records

    print("[INFO] Data cleaning completed")
    return cleaned
