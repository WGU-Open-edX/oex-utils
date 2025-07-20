import os
import json
import sys

IGNORED_SETTINGS = {
    "JWT_AUTH",
    "LOGGING",
    "USAGE_ID_PATTERN",
    "THIS_UUID",
    "CONTENTSTORE",
    "DOC_STORE_CONFIG",
    "MODULESTORE",
}

added_settings = set()    

def load_json_settings(path):
    with open(path, 'r') as f:
        return json.load(f)

def to_org_row(cols, action="TODO"):
    return '| ' + ' | '.join(cols) + f' | {action} |'

def values_differ(a, b):
    try:
        return json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True)
    except Exception:
        return a != b

def summarize_value(val, max_len=70):
    try:
        s = json.dumps(val, sort_keys=True)
        if len(s) <= max_len:
            return s
        return f"{s[:30]} … {s[-30:]}"
    except Exception:
        return "{{ unprintable }}"

def first_diff_item(val1, val2, path=""):
    """Return first difference between val1 and val2 with full key path."""
    # Handle dicts
    if isinstance(val1, dict) and isinstance(val2, dict):
        keys = sorted(set(val1) | set(val2))
        for key in keys:
            v1 = val1.get(key, "__missing__")
            v2 = val2.get(key, "__missing__")
            new_path = f"{path}.{key}" if path else key
            result = first_diff_item(v1, v2, new_path)
            if result:
                return result
        return None

    # Handle sequences
    elif isinstance(val1, (list, tuple)) and isinstance(val2, (list, tuple)):
        max_len = max(len(val1), len(val2))
        for i in range(max_len):
            try:
                v1 = val1[i]
            except IndexError:
                v1 = "__missing__"
            try:
                v2 = val2[i]
            except IndexError:
                v2 = "__missing__"
            new_path = f"{path}[{i}]"
            result = first_diff_item(v1, v2, new_path)
            if result:
                return result
        return None

    # Handle scalars / mismatched types
    elif val1 != val2:
        return (path, val1, val2)

    return None

def format_value(val, diff_kv=None):
    """Return a summary for a value, possibly showing just the first diff kv"""
    if diff_kv:
        key, val_x = diff_kv
        return f"{key}: {summarize_value(val_x)}"
    elif isinstance(val, dict):
        return f"{summarize_value(val)}"
    else:
        return summarize_value(val)

def compare_json_files(file1, file2):
    settings1 = load_json_settings(file1)
    settings2 = load_json_settings(file2)

    all_keys = sorted(set(settings1) | set(settings2))
    rows = []

    for key in all_keys:
        if key in IGNORED_SETTINGS:
            continue

        in1 = key in settings1
        in2 = key in settings2
        val1 = settings1.get(key)
        val2 = settings2.get(key)

        if not in1 or not in2 or values_differ(val1, val2):
            if isinstance(val1, dict) and isinstance(val2, dict):
                diff = first_diff_item(val1, val2)
                val1_fmt = format_value(val1, (diff[0], diff[1])) if diff else "(dict)"
                val2_fmt = format_value(val2, (diff[0], diff[2])) if diff else "(dict)"
            else:
                val1_fmt = format_value(val1) if in1 else ''
                val2_fmt = format_value(val2) if in2 else ''

            row = (key, val1_fmt if in1 else '', val2_fmt if in2 else '')
            
            # if row not in added_settings:
            #     added_settings.add(row)
            rows.append(row)
    return rows

def main(dir1, dir2):
    dir1_label = os.path.basename(os.path.normpath(dir1))
    dir2_label = os.path.basename(os.path.normpath(dir2))

    files1 = {f for f in os.listdir(dir1) if f.endswith('.json')}
    files2 = {f for f in os.listdir(dir2) if f.endswith('.json')}
    shared_files = sorted(files1 & files2)

    for filename in shared_files:
        path1 = os.path.join(dir1, filename)
        path2 = os.path.join(dir2, filename)

        diff_rows = compare_json_files(path1, path2)
        if not diff_rows:
            continue  # Skip files with no diffs

        print(f"* {filename}")
        print(f"diff {path1} {path2}")
        print(to_org_row(["SETTING", dir1_label, dir2_label], action="action"))
        print('|' + '-'*30 + '+' + '-'*30 + '+' + '-'*30 + '+' + '-'*30 + '|')
        for row in diff_rows:
            print(to_org_row(row))
        print()  # blank line between tables

    print("* END")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python table_diff.py <dir1> <dir2>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])