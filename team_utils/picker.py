#!/usr/bin/env python3
#
# /// script
# dependencies = [
#   "click",
# ]
# ///

import click
import random
import sys


def load_options_from_file(filepath):
    """Load options from a file, one per line."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            options = [line.strip() for line in f if line.strip()]
        return options
    except FileNotFoundError:
        click.echo(f"Error: File '{filepath}' not found.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error reading file '{filepath}': {e}", err=True)
        sys.exit(1)


@click.command()
@click.option(
    '-f', '--file', 
    type=click.Path(exists=True),
    help='File containing options (one per line)'
)
@click.argument('options', nargs=-1)
def main(file, options):
    """Randomly pick options from a list. Press Enter to get the next option.
    
    Examples:
    
    picker.py apple banana cherry          # Use command-line arguments
    picker.py -f options.txt                # Read from file
    """
    
    # Ensure exactly one input method is used
    if file and options:
        click.echo("Error: Cannot use both file input and command-line arguments.", err=True)
        sys.exit(1)
    
    if not file and not options:
        click.echo("Error: Must provide either options as arguments or use --file.", err=True)
        click.echo("Use --help for usage information.")
        sys.exit(1)
    
    # Load options based on input method
    if file:
        option_list = load_options_from_file(file)
        if not option_list:
            click.echo("Error: File is empty or contains no valid options.", err=True)
            sys.exit(1)
    else:
        option_list = list(options)
    
    # Shuffle the list
    random.shuffle(option_list)
    
    click.echo(f"Loaded {len(option_list)} options. Press Enter to get the next option, or Ctrl+C to quit.\n")
    
    try:
        while option_list:
            click.pause("")
            option = option_list.pop()
            click.echo(f"{option}")
            click.echo("🫴\n")
        
        click.echo("🤲 🔚")
        
    except KeyboardInterrupt:
        remaining = len(option_list)
        click.echo(f"\n\nExiting... ({remaining} option{'s' if remaining != 1 else ''} remaining)")
        sys.exit(0)


if __name__ == "__main__":
    main()
