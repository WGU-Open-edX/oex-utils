#!/usr/bin/env python3
"""
Script to automatically find Python files matching the pattern {prefix}_envs_{suffix}.py
and combine all sets found in them into a single output file.
"""

import glob
import ast
import argparse
from typing import Dict, Set, Any


def find_matching_files(pattern: str = "*_envs_*.py") -> list:
    """Find all Python files matching the specified pattern."""
    files = glob.glob(pattern)
    return sorted(files)


def extract_sets_from_file(filepath: str) -> Dict[str, Set[Any]]:
    """
    Extract all set variables from a Python file.
    Returns a dictionary mapping variable names to their set contents.
    """
    sets_found = {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse the Python file into an AST
        tree = ast.parse(content)

        # Look for assignments where the value is a set
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # Check if the assigned value is a set
                if isinstance(node.value, ast.Set):
                    # Extract variable names (handles multiple assignment targets)
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_name = target.id
                            # Extract set elements
                            set_elements = set()
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant):
                                    set_elements.add(elt.value)
                                elif isinstance(
                                    elt, ast.Str
                                ):  # For older Python versions
                                    set_elements.add(elt.s)
                                elif isinstance(
                                    elt, ast.Num
                                ):  # For older Python versions
                                    set_elements.add(elt.n)
                            sets_found[var_name] = set_elements

    except Exception as e:
        print(f"Error processing {filepath}: {e}")

    return sets_found


def combine_sets(all_sets: Dict[str, Dict[str, Set[Any]]]) -> Dict[str, Set[Any]]:
    """
    Combine sets with the same variable name from different files.
    """
    combined = {}

    for filepath, file_sets in all_sets.items():
        for var_name, var_set in file_sets.items():
            if var_name not in combined:
                combined[var_name] = set()
            combined[var_name].update(var_set)

    return combined


def format_set_for_output(var_name: str, var_set: Set[Any]) -> str:
    """Format a set variable for writing to the output file."""
    # Sort elements for consistent output (handles mixed types carefully)
    try:
        sorted_elements = sorted(var_set)
    except TypeError:
        # If elements can't be sorted (mixed types), convert to strings first
        sorted_elements = sorted(var_set, key=str)

    # Format elements with proper Python syntax
    formatted_elements = []
    for elem in sorted_elements:
        if isinstance(elem, str):
            formatted_elements.append(repr(elem))
        else:
            formatted_elements.append(str(elem))

    elements_str = ", ".join(formatted_elements)
    return f"{var_name} = {{{elements_str}}}"


def generate_output_file(
    combined_sets: Dict[str, Set[Any]],
    source_files: list,
    output_filename: str = "combined_sets.py",
):
    """Generate the output file with all combined sets."""

    with open(output_filename, "w", encoding="utf-8") as f:
        # Write header comment
        f.write('"""\n')
        f.write("Combined sets from the following files:\n")
        for filepath in source_files:
            f.write(f"  - {filepath}\n")
        f.write('"""\n\n')

        # Write each combined set
        for var_name in sorted(combined_sets.keys()):
            var_set = combined_sets[var_name]
            f.write(format_set_for_output(var_name, var_set))
            f.write("\n\n")


def main():
    """Main function to orchestrate the set combination process."""
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(
        description="Combine sets from Python files matching pattern *_envs_*.py"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="combined_sets.py",
        help="Output filename (default: combined_sets.py)",
    )
    parser.add_argument(
        "-p",
        "--pattern",
        default="*_envs_*.py",
        help="File matching pattern (default: *_envs_*.py)",
    )

    args = parser.parse_args()

    print(f"Looking for files matching pattern '{args.pattern}'...")

    # Find matching files
    matching_files = find_matching_files(args.pattern)

    if not matching_files:
        print(f"No files found matching the pattern '{args.pattern}'")
        return

    print(f"Found {len(matching_files)} matching files:")
    for f in matching_files:
        print(f"  - {f}")

    # Extract sets from each file
    all_sets = {}
    for filepath in matching_files:
        print(f"Processing {filepath}...")
        file_sets = extract_sets_from_file(filepath)
        if file_sets:
            all_sets[filepath] = file_sets
            print(f"  Found {len(file_sets)} set(s): {list(file_sets.keys())}")
        else:
            print(f"  No sets found in {filepath}")

    if not all_sets:
        print("No sets found in any of the files.")
        return

    # Combine sets with the same name
    print("\nCombining sets...")
    combined_sets = combine_sets(all_sets)

    print(f"Combined into {len(combined_sets)} unique set variable(s):")
    for var_name, var_set in combined_sets.items():
        print(f"  - {var_name}: {len(var_set)} elements")

    # Generate output file
    generate_output_file(combined_sets, matching_files, args.output)

    print(f"\nOutput written to: {args.output}")


if __name__ == "__main__":
    main()
