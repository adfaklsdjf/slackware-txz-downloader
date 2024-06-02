import os
import time
import requests
from urllib.parse import urljoin
import argparse

def fetch_and_parse_packages(url):
    response = requests.get(url)
    response.raise_for_status()  # Ensure we notice bad responses
    data = response.text

    packages = []
    for line in data.split('\n'):
        if line.startswith('PACKAGE NAME:'):
            package_name = line.split(': ')[1].strip()
        if line.startswith('PACKAGE LOCATION:'):
            location = line.split(': ')[1].strip()
            # Construct full URL for package
            full_url = urljoin(url, f"{location}/{package_name}")
            packages.append((full_url, package_name, location))

    return packages

def download_packages(packages, rate_limit_seconds=1, dry_run=False, verbose=False):
    for full_url, package_name, location in packages:
        local_dir = f"slackware64/{location.split('/')[-1]}"
        os.makedirs(local_dir, exist_ok=True)  # Ensure directory exists
        local_path = os.path.join(local_dir, package_name)

        if dry_run:
            print(f"Dry run: would download {package_name} to {local_path}")
        else:
            if not os.path.exists(local_path):  # Check if file already downloaded
                if verbose:
                    print(f"Downloading {package_name}...")
                response = requests.get(full_url, stream=True)
                response.raise_for_status()
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                if verbose:
                    print(f"Downloaded to {local_path}")
                time.sleep(rate_limit_seconds)  # Rate limiting

def main():
    parser = argparse.ArgumentParser(description="Download packages from a Slackware package list.")
    parser.add_argument("--dry-run", action="store_true", help="Run the script in dry run mode without downloading files")
    parser.add_argument("--verbose", action="store_true", help="Run the script in verbose mode to output more information")
    args = parser.parse_args()

    url = "http://slackware.oregonstate.edu/slackware64-current/slackware64/PACKAGES.TXT"
    packages = fetch_and_parse_packages(url)
    download_packages(packages, dry_run=args.dry_run, verbose=args.verbose)

if __name__ == "__main__":
    main()

