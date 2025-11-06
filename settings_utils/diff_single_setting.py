import os
import json
import sys
import difflib


def load_json_settings(path):
    with open(path, 'r') as f:
        return json.load(f)

def values_differ(a, b):
    try:
        return json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True)
    except Exception:
        return a != b

def compare_json_files(main_file, feature_file, settings_key):
    main_settings = load_json_settings(main_file)
    feature_settings = load_json_settings(feature_file)

    main_val = main_settings.get(settings_key)
    feature_val = feature_settings.get(settings_key)
    
    if main_val is None:
        print(f"No {settings_key} found in {main_file}.")
        exit(1)

    if not values_differ(main_val, feature_val):
        return None

    main_json = json.dumps(main_val, indent=2, sort_keys=True)
    feature_json = json.dumps(feature_val, indent=2, sort_keys=True) if feature_val is not None else ""
    
    diff = difflib.unified_diff(
        main_json.splitlines(keepends=True),
        feature_json.splitlines(keepends=True),
        fromfile=f"{main_file}:{settings_key}",
        tofile=f"{feature_file}:{settings_key}"
    )
    
    return ''.join(diff)

def main(settings_key, main_settings_dump="main_settings_dump", feature_settings_dump="feature_settings_dump"):
    main_files = {f for f in os.listdir(main_settings_dump) if f.endswith('.json')}
    feature_files = {f for f in os.listdir(feature_settings_dump) if f.endswith('.json')}
    shared_files = sorted(main_files & feature_files)

    for filename in shared_files:
        main_path = os.path.join(main_settings_dump, filename)
        feature_path = os.path.join(feature_settings_dump, filename)

        diff_output = compare_json_files(main_path, feature_path, settings_key)
        if not diff_output:
            continue  # Skip files with no diffs

        print(f"=== {filename} ===")
        print(diff_output)

if __name__ == '__main__':
    if len(sys.argv) == 2:
        main(sys.argv[1])
    elif len(sys.argv) == 4:
        main(sys.argv[3], sys.argv[1], sys.argv[2])
    else:
        print("Usage: python diff_features.py [settings_key] OR [main_settings_dump] [feature_settings_dump] [settings_key]")
        sys.exit(1)
