# Team related utilities
Utilities which are helpful for team processes

## Scripts

### `picker.py`

Given a list of options, this script will randomly select items one at a time without replacement.
You can pass in the options as arguments or pass in a path to a file containing the options, one per line.

Requires the `click` package. Can be run with `uv run` to automatically ensure dependencies are available.

```sh
uv run picker.py --help
uv run picker.py apple banana cherry
uv run picker.py -f ~/path/to/options.txt
```

### `query_gh_prs.py`

To use this script:
1. Install Python (if needed)
2. Install requests library:

```sh
pip install requests
```

3. Create a GitHub Personal Access Token:Go to https://github.com/settings/tokens
Click "Generate new token (classic)"
Give it a name like "OpenEdx PR Analysis"
Select scope: public_repo (or repo if you need private repos)
Copy the token
4. Run the script:

```sh
# Set your token as environment variable
export GITHUB_TOKEN='your_token_here'

# Run the script
python3 github_pr_analysis.py
```

#### Output:
The script will create three files:

- merged_prs_detailed.csv - Every PR with full details
- merged_prs_summary.csv - Count of PRs per user
- merged_prs_raw.json - Raw API responses for further analysis