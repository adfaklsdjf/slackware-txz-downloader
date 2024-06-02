import os
import requests
import time
import re
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description="Slackware Package Downloader")
parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without downloading packages")
parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
parser.add_argument("--sleep", type=int, default=3, help="Sleep time between downloads in seconds (default: 3)")
parser.add_argument("--rate-limit", type=int, default=500, help="Download rate limit in kilobytes/sec (default: 500)")
args = parser.parse_args()

# Fetch the PACKAGES.TXT file
response = requests.get("http://slackware.oregonstate.edu/slackware64-current/slackware64/PACKAGES.TXT")
packages_txt = response.text

# Extract the package information and generate URLs
packages = re.findall(r"PACKAGE NAME:\s*(.*?)\nPACKAGE LOCATION:\s*(.*?)\nPACKAGE SIZE \(compressed\):\s*(.*?)\n", packages_txt, re.DOTALL)
urls = []
total_size = 0
for package, location, size in packages:
    url = "http://slackware.oregonstate.edu/slackware64-current{}/{}".format(location, package)
    urls.append((url, size))
    size_kb = int(size.split()[0])
    total_size += size_kb

# Remove duplicate URLs
urls = list(set(urls))

if args.verbose:
    print("Found {} unique package URLs.".format(len(urls)))
    print("Total download size: {} KB".format(total_size))

# Calculate the estimated download time
download_time = total_size / args.rate_limit + len(urls) * args.sleep
print("Estimated download time: {:.2f} seconds".format(download_time))

# Download each package
for url, size in urls:
    package_name = url.split("/")[-1]
    subdir = url.split("/")[-2]
    
    if args.verbose:
        print("Package Name: {}".format(package_name))
        print("URL: {}".format(url))
        print("Download Destination: slackware64/{}/{}".format(subdir, package_name))
        print()
    
    if not args.dry_run:
        # Create the folder structure if it doesn't exist
        os.makedirs("slackware64/{}/".format(subdir), exist_ok=True)
        
        # Download the package with rate limiting
        response = requests.get(url, stream=True)
        with open("slackware64/{}/{}".format(subdir, package_name), "wb") as file:
            start_time = time.time()
            downloaded_size = 0
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
                    downloaded_size += len(chunk)
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 0:
                        download_speed = downloaded_size / elapsed_time / 1024  # KB/s
                        if download_speed > args.rate_limit:
                            time.sleep(download_speed / args.rate_limit - 1)
        
        # Sleep between downloads
        time.sleep(args.sleep)

if args.dry_run:
    print("Dry run completed. No packages were downloaded.")
else:
    print("Package download completed.")
