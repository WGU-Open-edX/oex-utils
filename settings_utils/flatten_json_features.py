import json
import sys
from pathlib import Path

def flatten_features(input_dir="main_settings_dump"):
    """
    Process all JSON files in the specified directory, extracting FEATURES keys
    to the top level and saving with 'flattened' added to the filename.
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"Directory {input_dir} does not exist.")
        return
    
    # Find all JSON files in the directory
    json_files = list(input_path.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return
    
    for json_file in json_files:
        try:
            # Read the original JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if FEATURES key exists
            if "FEATURES" in data and isinstance(data["FEATURES"], dict):
                # Extract FEATURES content to top level
                features_content = data["FEATURES"]
                
                # Remove the FEATURES key from original data
                del data["FEATURES"]
                
                # Add all FEATURES keys to the top level
                data.update(features_content)
            
            # Save the modified JSON back to the original file with sorted keys
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, sort_keys=True)
                f.write("\n")

            print(f"Processed: {json_file.name}")
            
        except json.JSONDecodeError as e:
            print(f"Error reading JSON file {json_file.name}: {e}")
        except Exception as e:
            print(f"Error processing {json_file.name}: {e}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        flatten_features()
    elif len(sys.argv) == 2:
        flatten_features(sys.argv[1])
    else:
        print("Usage: python flatten_json_features.py [input_directory]")
        print("If no directory provided, defaults to 'main_settings_dump'")
        sys.exit(1)