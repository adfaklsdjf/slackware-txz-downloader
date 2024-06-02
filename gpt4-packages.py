import os
import requests
import time
import re
import argparse
import sys
import hashlib

def create_verbose_function(verbose_flag):
    def verbose(message):
        if verbose_flag:
            print(message)
    return verbose

def parse_checksums(checksum_content):
    checksums = {}
    for line in checksum_content.splitlines():
        match = re.match(r"^([a-fA-F0-9]{32})\s+\./(.+)$", line)
        if match:
            checksum, filename = match.groups()
            checksums[filename] = checksum
    return checksums

# Parse command line arguments
parser = argparse.ArgumentParser(description="Slackware Package Downloader")
parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without downloading packages")
parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
parser.add_argument("--sleep", type=int, default=3, help="Sleep time between downloads in seconds (default: 3)")
parser.add_argument("--rate-limit", type=int, default=500, help="Download rate limit in kilobytes/sec (default: 500)")
parser.add_argument("--packages-file", help="Path to the local PACKAGES.TXT file")
parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
parser.add_argument("packages", nargs="*", help="Package names to download (optional)")
args = parser.parse_args()
verbose = create_verbose_function(args.verbose)
verbose("Arguments: {}".format(args))

# Read the PACKAGES.TXT file
if args.packages_file:
    verbose("Reading PACKAGES.TXT file: {}".format(args.packages_file))
    with open(args.packages_file, "r") as file:
        packages_txt = file.read()
else:
    verbose("Downloading PACKAGES.TXT file...")
    response = requests.get("http://slackware.oregonstate.edu/slackware64-current/slackware64/PACKAGES.TXT")
    packages_txt = response.text

# Download and parse the CHECKSUMS.md5 file
verbose("Downloading CHECKSUMS.md5 file...")
response = requests.get("http://slackware.oregonstate.edu/slackware64-current/slackware64/CHECKSUMS.md5")
checksums = parse_checksums(response.text)

# Extract the package information and generate URLs
packages = re.findall(r"PACKAGE NAME:\s*(.*?)\nPACKAGE LOCATION:\s*(.*?)\nPACKAGE SIZE \(compressed\):\s*(.*?)\n", packages_txt, re.DOTALL)
urls = []
total_size = 0
for package, location, size in packages:
    if not args.packages or package in args.packages:
        url = "http://slackware.oregonstate.edu/slackware64-current/{}/{}".format(location.lstrip('./'), package)
        urls.append((url, size))
        size_kb = int(size.split()[0])
        total_size += size_kb

# Remove duplicate URLs
urls = list(set(urls))

print("Found {} unique package URLs.".format(len(urls)))
print("Total download size: {} KB".format(total_size))

# Calculate the estimated download time
download_time = total_size / args.rate_limit + len(urls) * args.sleep
print("Estimated download time: {:.2f} seconds".format(download_time))

print("")

# Download each package
for url, size in urls:
    package_name = url.split("/")[-1]
    subdir = url.split("/")[-2]
    
    print("")
    verbose("Package Name: {}".format(package_name))
    print("URL: {}".format(url))
    verbose("Download Destination: slackware64/{}/{}".format(subdir, package_name))
    
    if not args.dry_run:
        # Create the folder structure if it doesn't exist
        os.makedirs("slackware64/{}/".format(subdir), exist_ok=True)
        
        # Determine file path
        file_path = "slackware64/{}/{}".format(subdir, package_name)
        verbose("File path: {}".format(file_path))

        # Check if the file should be downloaded
        file_exists = os.path.exists(file_path)
        file_size = os.path.getsize(file_path) if file_exists else 0
        file_checksum_valid = False

        if file_exists and file_size > 0:
            if not args.overwrite:
                with open(file_path, "rb") as existing_file:
                    existing_file_checksum = hashlib.md5(existing_file.read()).hexdigest()
                expected_checksum = checksums.get("{}/{}".format(subdir, package_name), "")
                if existing_file_checksum == expected_checksum:
                    file_checksum_valid = True
                    print("File {} exists and checksum is valid. Skipping download.".format(file_path))
                    continue
                else:
                    print("File {} exists but checksum is invalid. Re-downloading...".format(file_path))
        
        if file_exists and file_size == 0:
            print("Empty file {} exists. Overwriting with downloaded file...".format(file_path))

        # Download the package with rate limiting and real-time information
        verbose("Downloading {}...".format(package_name))
        response = requests.get(url, stream=True)
        verbose("Response received")
        total_size = int(response.headers.get("Content-Length", 0))
        verbose("Total size: {} bytes".format(total_size))
        block_size = 32 * 1024  # 32 KB
        downloaded_size = 0
        start_time = time.time()
        
        if response.status_code == 200:
            verbose("Response status code: 200")
            with open(file_path, "wb") as file:
                verbose("File opened")
                for data in response.iter_content(block_size):
                    downloaded_size += len(data)
                    file.write(data)
                    
                    # Update real-time download information
                    percent = 100 * downloaded_size / total_size
                    elapsed_time = time.time() - start_time
                    download_speed = downloaded_size / elapsed_time / 1024  # KB/s
                    remaining_time = (total_size - downloaded_size) / 1024 / download_speed if download_speed > 0 else 0  # Seconds
                    
                    sys.stdout.write("\rDownloading {}: {:.2f}% - {:.2f} KB/s - {:.2f} KB / {:.2f} KB - ETA: {:.2f}s".format(
                        package_name, percent, download_speed, downloaded_size / 1024, total_size / 1024, remaining_time))
                    sys.stdout.flush()
                    
                    # Rate limiting
                    if download_speed > args.rate_limit:
                        verbose("\nDownload speed exceeded rate limit. Sleeping for {:.2f}s...".format(download_speed / args.rate_limit - 1))
                        time.sleep(download_speed / args.rate_limit - 1)
                    else:
                        time.sleep(0.1)  # Add a small delay to allow the download progress to update
        else:
            print("Error downloading {}: {}".format(package_name, response.status_code))
            print("Response content:")
            print(response.content.decode())

        sys.stdout.write("\n")
        verbose("Flush")
        sys.stdout.flush()
        verbose("Download complete")

        # Verify the checksum of the downloaded file
        with open(file_path, "rb") as downloaded_file:
            downloaded_file_checksum = hashlib.md5(downloaded_file.read()).hexdigest()
        expected_checksum = checksums.get("{}/{}".format(subdir, package_name), "")
        if downloaded_file_checksum == expected_checksum:
            print("Checksum verification passed for {}".format(file_path))
        else:
            print("Warning: Checksum verification failed for {}. Expected: {}, Got: {}".format(
                file_path, expected_checksum, downloaded_file_checksum))
        
        # Sleep between downloads
        verbose("Sleeping for {} seconds...".format(args.sleep))
        time.sleep(args.sleep)
    else:
        print("Dry run: Skipping download of {}".format(url))

if args.dry_run:
    print("Dry run completed. No packages were downloaded.")
else:
    print("Package download completed.")
