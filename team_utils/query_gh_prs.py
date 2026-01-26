#!/usr/bin/env python3
"""
Query GitHub for merged PRs in the openedx organization
with robust error handling and rate limiting protection.
"""

import requests
from datetime import datetime, timedelta
from collections import defaultdict
import json
import csv
import os
import time

# Configuration
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', 'YOUR_TOKEN_HERE')
ORG_NAME = 'openedx'
# Change to any GH usernames you want to pull against
USERNAMES = [ 
    'brianjbuck-wgu',
    'diana-villalvazo-wgu',
    'jacobo-dominguez-wgu',
    'jesusbalderramawgu',
    'rodmgwgu',
    'wgu-jesse-stewart',
    'wgu-taylor-payne',
    'holaontiveros',
    'tonybusa',
    'dwong2708'
]

# Calculate date 13 months ago
MONTHS_AGO = 13
since_date = (datetime.now() - timedelta(days=MONTHS_AGO * 30)).strftime("%Y-%m-%d")

headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

# Add session with retry logic
session = requests.Session()
session.headers.update(headers)

def check_rate_limit():
    """Check GitHub API rate limit status."""
    try:
        response = session.get('https://api.github.com/rate_limit', timeout=10)
        if response.status_code == 200:
            data = response.json()
            remaining = data['resources']['search']['remaining']
            reset_time = data['resources']['search']['reset']
            
            if remaining < 5:
                wait_time = reset_time - time.time() + 10  # Add 10 second buffer
                if wait_time > 0:
                    print(f"\nRate limit low ({remaining} remaining). Waiting {int(wait_time)} seconds...")
                    time.sleep(wait_time)
            
            return remaining
    except Exception as e:
        print(f"Could not check rate limit: {e}")
        return None

def make_request_with_retry(url, max_retries=5):
    """Make request with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=30)
            
            # Check rate limit from response headers
            if 'X-RateLimit-Remaining' in response.headers:
                remaining = int(response.headers['X-RateLimit-Remaining'])
                if remaining < 5:
                    check_rate_limit()
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                print(f"\nRate limit hit (403). Checking rate limit status...")
                check_rate_limit()
                time.sleep(5)
                continue
            elif response.status_code == 422:
                print(f"Validation error (422) for URL: {url}")
                return None
            else:
                print(f"HTTP {response.status_code}: {response.text[:200]}")
                return None
                
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            wait_time = (2 ** attempt) + 1  # Exponential backoff: 2, 5, 9, 17, 33 seconds
            print(f"\nConnection error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print("Max retries reached. Skipping this request.")
                return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    return None

def get_all_repos(org):
    """Get all repositories in the organization."""
    repos = []
    page = 1
    
    print(f"Fetching repositories for {org}...")
    
    while True:
        url = f'https://api.github.com/orgs/{org}/repos?per_page=100&page={page}'
        data = make_request_with_retry(url)
        
        if not data:
            break
            
        repos.extend(data)
        
        if len(data) < 100:
            break
            
        page += 1
        time.sleep(0.5)  # Small delay between requests
        
    print(f"Found {len(repos)} repositories\n")
    return repos

def get_merged_prs_for_user(org, repo_name, username, since_date):
    """Get merged PRs for a specific user in a specific repo."""
    prs = []
    page = 1
    
    while True:
        query = f'repo:{org}/{repo_name} is:pr is:merged author:{username} merged:>={since_date}'
        url = f'https://api.github.com/search/issues?q={query}&per_page=100&page={page}'
        
        data = make_request_with_retry(url)
        
        if not data:
            break
            
        items = data.get('items', [])
        
        if not items:
            break
            
        prs.extend(items)
        
        if len(items) < 100:
            break
            
        page += 1
        time.sleep(2)  # GitHub search API is more restrictive - wait 2 seconds
        
    return prs

def main():
    # Check initial rate limit
    print("Checking GitHub API rate limit...")
    remaining = check_rate_limit()
    if remaining is not None:
        print(f"Search API requests remaining: {remaining}\n")
    
    # Data structure: {username: {repo_name: [pr_list]}}
    results = defaultdict(lambda: defaultdict(list))
    
    # Get all repos
    repos = get_all_repos(ORG_NAME)
    
    total_repos = len(repos)
    
    # For each user, search across all repos
    for user_idx, username in enumerate(USERNAMES, 1):
        print(f"\n[{user_idx}/{len(USERNAMES)}] Searching for {username}...")
        user_total = 0
        
        for repo_idx, repo in enumerate(repos, 1):
            repo_name = repo['name']
            
            # Show progress every 50 repos
            if repo_idx % 50 == 0:
                print(f"  Progress: {repo_idx}/{total_repos} repos checked...")
            
            prs = get_merged_prs_for_user(ORG_NAME, repo_name, username, since_date)
            
            if prs:
                results[username][repo_name] = prs
                user_total += len(prs)
                print(f"  ✓ {repo_name}: {len(prs)} PRs")
        
        print(f"Total for {username}: {user_total} PRs")
        
        # Save intermediate results after each user
        with open(f'intermediate_results_{username}.json', 'w') as f:
            json.dump(dict(results[username]), f, indent=2)
    
    # Generate summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    total_prs = 0
    summary_data = []
    
    for username in USERNAMES:
        user_prs = sum(len(prs) for prs in results[username].values())
        total_prs += user_prs
        repo_count = len(results[username])
        
        summary_data.append({
            'username': username,
            'total_prs': user_prs,
            'repositories': repo_count
        })
        
        print(f"{username:30} {user_prs:4} PRs across {repo_count} repos")
    
    print(f"\nGrand Total: {total_prs} merged PRs since {since_date}")
    
    # Export detailed results to CSV
    print("\nExporting detailed results to CSV...")
    with open('merged_prs_detailed.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Username', 'Repository', 'PR Title', 'PR URL', 'Merged At', 'Created At'])
        
        for username, repos in results.items():
            for repo_name, prs in repos.items():
                for pr in prs:
                    writer.writerow([
                        username,
                        repo_name,
                        pr['title'],
                        pr['html_url'],
                        pr.get('closed_at', 'N/A'),
                        pr.get('created_at', 'N/A')
                    ])
    
    # Export summary to CSV
    with open('merged_prs_summary.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['username', 'total_prs', 'repositories'])
        writer.writeheader()
        writer.writerows(summary_data)
    
    # Export raw JSON
    with open('merged_prs_raw.json', 'w') as f:
        json_results = {k: dict(v) for k, v in results.items()}
        json.dump(json_results, f, indent=2)
    
    print("\nFiles generated:")
    print("  - merged_prs_detailed.csv (all PRs with details)")
    print("  - merged_prs_summary.csv (summary by user)")
    print("  - merged_prs_raw.json (raw data)")
    print("  - intermediate_results_*.json (backup files)")

if __name__ == '__main__':
    if GITHUB_TOKEN == 'YOUR_TOKEN_HERE':
        print("Please set your GitHub token!")
        print("Either:")
        print("  1. Set environment variable: export GITHUB_TOKEN='your_token'")
        print("  2. Or edit the script and replace YOUR_TOKEN_HERE")
        print("\nCreate a token at: https://github.com/settings/tokens")
        print("Required scope: 'public_repo' or 'repo'")
    else:
        main()