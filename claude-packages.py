import os
import requests
import time
import re
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description="Slackware Package Downloader")
parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without downloading packages")
parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
args = parser.parse_args()

# Fetch the PACKAGES.TXT file
response = requests.get("http://slackware.oregonstate.edu/slackware64-current/slackware64/PACKAGES.TXT")
packages_txt = response.text

# Extract the package information and generate URLs
packages = re.findall(r"PACKAGE NAME:\s*(.*?)\nPACKAGE LOCATION:\s*(.*?)\n", packages_txt, re.DOTALL)
urls = []
for package, location in packages:
    url = f"http://slackware.oregonstate.edu/slackware64-current{location}/{package}"
    urls.append(url)

# Remove duplicate URLs
urls = list(set(urls))

if args.verbose:
    print(f"Found {len(urls)} unique package URLs.")

# Download each package
for url in urls:
    package_name = url.split("/")[-1]
    subdir = url.split("/")[-2]
    
    if args.verbose:
        print(f"Processing package: {package_name}")
    
    if not args.dry_run:
        # Create the folder structure if it doesn't exist
        os.makedirs(f"slackware64/{subdir}", exist_ok=True)
        
        # Download the package
        response = requests.get(url, stream=True)
        with open(f"slackware64/{subdir}/{package_name}", "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
        
        # Rate limit the downloads (adjust the sleep duration as needed)
        time.sleep(1)
    else:
        if args.verbose:
            print(f"Skipping download of package: {package_name}")

if args.dry_run:
    print("Dry run completed. No packages were downloaded.")
else:
    print("Package download completed.")
