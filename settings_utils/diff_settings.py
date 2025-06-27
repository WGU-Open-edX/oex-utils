#!/usr/bin/env python3
"""
Script to dump Django settings for different configurations.
Compares main branch with feature branch settings.

Compatible with Python 3.11+

requires:
- Django management command `dump_settings` to be available
- `diff` command available in the environment for comparison
- `git` command available for branch switching
- `click` package available for command-line interface
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Tuple

import click
import re


# Configuration tuples: (django_settings_module, config_file)
CONFIGS = [
    ("lms.envs.production", "lms/envs/minimal.yml"),
    ("lms.envs.production", "lms/envs/mock.yml"),
    ("lms.envs.tutor.production", "/openedx/config/lms.env.yml"),
    ("lms.envs.tutor.development", "/openedx/config/lms.env.yml"),
    ("cms.envs.production", "cms/envs/mock.yml"),
    ("cms.envs.tutor.production", "/openedx/config/cms.env.yml"),
    ("cms.envs.tutor.development", "/openedx/config/cms.env.yml"),
]

# Output directories (defaults)
DEFAULT_MAIN_DIR = "main_settings_dump"
DEFAULT_FEATURE_DIR = "feature_settings_dump"


def run_command(cmd: list[str], verbose: bool = False, **kwargs) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    # DJANGO_SETTINGS_MODULE=cms.envs.tutor.development CMS_CFG=/openedx/config/cms.env.yml ./manage.py cms dump_settings
    try:
        if verbose:
            # Show command output in real-time
            result = subprocess.run(cmd, check=True, text=True, **kwargs)
        else:
            # Capture output silently
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, **kwargs)
        return result
    except subprocess.CalledProcessError as e:
        if verbose:
            click.echo(click.style(f"Error running command: {' '.join(cmd)}", fg='red'), err=True)
            click.echo(click.style(f"Return code: {e.returncode}", fg='red'), err=True)
            if e.stdout:
                click.echo(click.style(f"STDOUT: {e.stdout}", fg='red'), err=True)
            if e.stderr:
                click.echo(click.style(f"STDERR: {e.stderr}", fg='red'), err=True)
        raise


def normalize_filename(text: str) -> str:
    """
    Normalize a string to be used as a filename component.
    
    Converts characters like '/', '-' to underscores and removes file extensions,
    but preserves dots in module paths like 'cms.envs.production'.
    """
    # Only remove file extensions from actual file paths (containing '/')
    if '/' in text:
        text = re.sub(r'\.[^/]*$', '', text)
    
    # Replace forward slashes and hyphens with underscores
    text = re.sub(r'[/-]', '_', text)
    
    # Replace multiple underscores with single underscore
    text = re.sub(r'_+', '_', text)

    # Remove leading/trailing underscores
    text = text.strip('_')

    return text


def generate_output_filename(django_settings_module: str, config_file: str) -> str:
    """Generate output filename from django settings module and config file path."""
    normalized_settings = normalize_filename(django_settings_module)
    normalized_config = normalize_filename(config_file)
    return f"{normalized_settings}__{normalized_config}"


def get_app_type_and_env_var(django_settings_module: str) -> Tuple[str, str]:
    """Determine app type and environment variable name from settings module."""
    app_type = django_settings_module.split(".")[0]
    
    if app_type in ("lms", "cms"):
        env_var = f"{app_type.upper()}_CFG"
        return app_type, env_var
    else:
        raise ValueError(f"Unknown settings module type: {django_settings_module}")


def dump_settings(django_settings_module: str, config_file: str, output_file: Path, verbose: bool = False) -> None:
    """Dump settings for a given configuration."""
    app_type, config_env_var = get_app_type_and_env_var(django_settings_module)
    
    if verbose:
        click.echo(f"Dumping {django_settings_module} with {config_file} -> {output_file}")
    
    # Set up environment
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = django_settings_module
    env["SERVICE_VARIANT"] = app_type
    env[config_env_var] = config_file
    
    # Run the dump command
    cmd = ["./manage.py", app_type, "dump_settings"]

    if verbose:
        click.echo(click.style(f"", fg='blue'), err=True)
        click.echo(click.style(f"DJANGO_SETTINGS_MODULE: {django_settings_module} \\", fg='blue'), err=True)
        click.echo(click.style(f"SERVICE_VARIANT: {env.get('SERVICE_VARIANT')} \\", fg='blue'), err=True)
        click.echo(click.style(f"{config_env_var}: {config_file} \\", fg='blue'), err=True)
        click.echo(click.style(f"{' '.join(cmd)} > {output_file}", fg='blue'), err=True)

    result = run_command(cmd, verbose=verbose, env=env)
    
    # Write output to file
    output_file.write_text(result.stdout)


def switch_branch(branch: str, verbose: bool = False) -> None:
    """Switch to the specified git branch."""
    if verbose:
        click.echo(f"Switching to branch: {branch}")
    run_command(["git", "switch", branch], verbose=verbose)


def process_branch(branch: str, output_dir: Path, verbose: bool = False) -> None:
    """Process all configurations for a branch."""
    click.echo(click.style(f"=== Processing branch: {branch} ===", fg='blue', bold=True))
    switch_branch(branch, verbose)
    
    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True)
    
    with click.progressbar(CONFIGS, label='Processing configurations') as configs:
        for django_settings_module, config_file in configs:
            output_filename = generate_output_filename(django_settings_module, config_file)
            output_file = output_dir / f"{output_filename}.json"
            
            try:
                dump_settings(django_settings_module, config_file, output_file, verbose)
            except Exception as e:
                if verbose:
                    click.echo(click.style(
                        f"Error processing {django_settings_module} with {config_file}: {e}", 
                        fg='red'
                    ), err=True)
                continue
    
    click.echo(click.style(f"Completed processing branch: {branch}", fg='green'))
    click.echo()


@click.command()
@click.argument('main_branch')
@click.argument('feature_branch')
@click.option(
    '--main-dir', 
    default=DEFAULT_MAIN_DIR,
    help='Output directory for main branch settings',
    show_default=True
)
@click.option(
    '--branch-dir',
    default=DEFAULT_FEATURE_DIR,
    help='Output directory for feature branch settings',
    show_default=True
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output and show command output in real-time'
)
def main(main_branch: str, feature_branch: str, main_dir: str, branch_dir: str, verbose: bool) -> None:
    """
    Dump Django settings for different configurations and compare branches.
    
    MAIN_BRANCH: The main/master branch to compare against
    FEATURE_BRANCH: The feature branch to compare
    """
    # Set up directories
    main_dir_path = Path(main_dir)
    branch_dir_path = Path(branch_dir)
    
    click.echo("Starting Django settings dump comparison...")
    click.echo(f"Comparing {main_branch} -> {feature_branch}")
    click.echo(f"Output: {main_dir_path}/ and {branch_dir_path}/")
    click.echo()
    
    try:
        # Clean and create output directories
        if main_dir_path.exists():
            click.echo(f"Cleaning existing directory: {main_dir_path}")
            shutil.rmtree(main_dir_path)
        main_dir_path.mkdir(parents=True)
        
        if branch_dir_path.exists():
            click.echo(f"Cleaning existing directory: {branch_dir_path}")
            shutil.rmtree(branch_dir_path)
        branch_dir_path.mkdir(parents=True)
        
        # Process main branch
        process_branch(main_branch, main_dir_path, verbose)
        
        # Process feature branch
        process_branch(feature_branch, branch_dir_path, verbose)
        
        # Run diff comparison
        click.echo(click.style("=== Running diff comparison ===", fg='blue', bold=True))
        try:
            diff_cmd = ["diff", str(main_dir_path), str(branch_dir_path)]
            # Always show diff output, don't suppress it
            result = run_command(diff_cmd, verbose=verbose)
            
            # diff returns 0 if files are identical, 1 if different, but run_command
            # will raise an exception for non-zero return codes, so we handle it differently
            click.echo(click.style("No differences found between branches", fg='green'))
                
        except subprocess.CalledProcessError as e:
            # diff returns 1 when differences are found, which is normal
            if e.returncode == 1:
                if e.stdout:
                    click.echo(e.stdout)
                click.echo(click.style("Differences found between branches (shown above)", fg='yellow'))
            else:
                click.echo(click.style(f"Diff command failed with return code {e.returncode}", fg='red'), err=True)
                if e.stderr:
                    click.echo(click.style(e.stderr, fg='red'), err=True)
        except FileNotFoundError:
            click.echo(click.style("diff command not found - skipping comparison", fg='yellow'), err=True)
        except Exception as e:
            click.echo(click.style(f"Error running diff: {e}", fg='red'), err=True)
        
        click.echo()
        click.echo(click.style("=== Settings dump complete ===", fg='green', bold=True))
        click.echo(f"{main_branch} branch settings: {main_dir_path}/")
        click.echo(f"{feature_branch} branch settings: {branch_dir_path}/")
        click.echo()
        click.echo("To compare settings manually, you can use:")
        click.echo(f"  # Diff all settings at once:")
        click.echo(f"  diff -u {main_dir_path} {branch_dir_path}")
        click.echo()

        # Show available files for comparison
        master_files = sorted(main_dir_path.glob("*.json"))
        if master_files:
            click.echo(f"  # Diff settings by file:")
            for file in master_files:
                click.echo(f"  echo {file.name} | xargs -I {{}} diff -u {main_dir_path}/{{}} {branch_dir_path}/{{}}")
        
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()