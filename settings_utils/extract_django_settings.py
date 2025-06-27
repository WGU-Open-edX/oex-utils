#!/usr/bin/env python3
"""
Django Settings Variable Extractor

This script parses a Django settings file and extracts all uppercase variable names,
including those used in dictionary key assignments (e.g., CONFIG["key"] = value).
It then generates a Python file containing a set with all those variable names.
"""

import ast
import argparse
import sys
from pathlib import Path
from typing import Set


def extract_settings_variables(settings_file_path: str) -> Set[str]:
    """
    Extract all uppercase variable names from a Django settings file.
    This includes both direct variable assignments and full dictionary key paths.

    Args:
        settings_file_path: Path to the Django settings file

    Returns:
        Set of uppercase variable names found in the file
    """
    try:
        with open(settings_file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: Settings file '{settings_file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file '{settings_file_path}': {e}")
        sys.exit(1)

    try:
        # Parse the Python file into an AST
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Error parsing '{settings_file_path}': {e}")
        sys.exit(1)

    settings_vars = set()

    def extract_variable_name(node):
        """Extract variable name or full dictionary path from various node types."""
        if isinstance(node, ast.Name):
            # Simple variable name like DEBUG
            var_name = node.id
            if var_name.isupper() and var_name.isidentifier():
                return var_name
        elif isinstance(node, ast.Subscript):
            # Handle dictionary access like CONFIG["key"] or CONFIG["redis"]["host"]
            return reconstruct_subscript_path(node)
        return None

    def reconstruct_subscript_path(node):
        """Reconstruct the full path of a subscript expression."""

        def get_subscript_string(n):
            if isinstance(n, ast.Name):
                return n.id
            elif isinstance(n, ast.Subscript):
                base = get_subscript_string(n.value)
                if base is None:
                    return None
                key = get_key_string(n.slice)
                if key is None:
                    return None
                return f"{base}[{key}]"
            return None

        def get_key_string(slice_node):
            """Extract the key as a string representation."""
            if isinstance(slice_node, ast.Constant):
                # String or number literal
                if isinstance(slice_node.value, str):
                    return f'"{slice_node.value}"'
                else:
                    return str(slice_node.value)
            elif isinstance(slice_node, ast.Name):
                # Variable name as key
                return slice_node.id
            return None

        full_path = get_subscript_string(node)
        if full_path:
            # Check if the base variable (first part) is uppercase
            base_var = full_path.split("[")[0]
            if base_var.isupper() and base_var.isidentifier():
                return full_path
        return None

    # Walk through all nodes in the AST
    for node in ast.walk(tree):
        # Look for assignment nodes (variable = value)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                var_name = extract_variable_name(target)
                if var_name:
                    settings_vars.add(var_name)

        # Also handle augmented assignments (variable += value, variable["key"] += value, etc.)
        elif isinstance(node, ast.AugAssign):
            var_name = extract_variable_name(node.target)
            if var_name:
                settings_vars.add(var_name)

    return settings_vars


def generate_output_file(
    settings_vars: Set[str], input_file: str, output_file_path: str
):
    """
    Generate a Python file containing a set with all the extracted variable names.

    Args:
        settings_vars: Set of variable names to include
        output_file_path: Path where the output file should be written
    """
    try:
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(
                f"# This file contains all uppercase variable names found in {input_file}\n\n"
            )

            # Write the set with proper formatting
            f.write(f"{output_file_path.removesuffix('.py')} = {{\n")

            # Sort the variables for consistent output
            sorted_vars = sorted(settings_vars)
            for i, var in enumerate(sorted_vars):
                # Add comma except for the last item
                comma = "," if i < len(sorted_vars) - 1 else ""
                f.write(f"    '{var}'{comma}\n")

            f.write("}\n")

        print(
            f"Successfully generated '{output_file_path}' with {len(settings_vars)} settings variables."
        )

    except Exception as e:
        print(f"Error writing output file '{output_file_path}': {e}")
        sys.exit(1)


def flatten_path(path_str: str) -> str:
    """Flatten a file path by removing the file extension and joining the parts with underscores."""
    path = Path(path_str)
    return "_".join(path.with_suffix("").parts)


def main():
    parser = argparse.ArgumentParser(
        description="Extract Django settings variable names and generate a Python file with a set containing them."
    )
    parser.add_argument(
        "settings_file", help="Path to the Django settings file to parse"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the variables that would be extracted without creating the output file",
    )

    args = parser.parse_args()

    # Check if settings file exists
    if not Path(args.settings_file).exists():
        print(f"Error: Settings file '{args.settings_file}' does not exist.")
        sys.exit(1)

    # Extract variables from the settings file
    print(f"Parsing Django settings file: {args.settings_file}")
    settings_vars = extract_settings_variables(args.settings_file)

    if not settings_vars:
        print("No uppercase variables found in the settings file.")
        return

    print(f"Found {len(settings_vars)} settings variables:")
    for var in sorted(settings_vars):
        print(f"  - {var}")

    if args.dry_run:
        print("\nDry run mode - no output file created.")
        return

    output_path = f"{flatten_path(args.settings_file)}.py"

    # Generate the output file
    generate_output_file(settings_vars, args.settings_file, output_path)


if __name__ == "__main__":
    main()
