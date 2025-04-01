'''
fetch_data.py

This module is used to download and extract the Enron email dataset from the CMU servers.

It is only meant to be used once to retrieve the data and should not be run multiple times.

This module stores the dataset in the data/maildir/ directory, in which there are folders for each account.
'''

def extract_data_from_source():
    """
    Download and extract the Enron email dataset from CMU servers.
    
    This function:
    1. Checks if the dataset already exists to avoid duplicate downloads
    2. Creates a data directory if it doesn't exist
    3. Downloads the Enron dataset (~423MB) with progress tracking
    4. Extracts the tar.gz file into the data directory
    5. Optionally removes the tar.gz file to save disk space
    
    Returns:
        str: Absolute path to the data directory where files were extracted
        
    Note:
        This function should only be run once to set up the dataset.
        The extracted dataset is approximately 1.7GB in size.
    """
    import requests
    import tarfile
    import os
    from pathlib import Path

    # Check if the data/maildir/ directory exists and exit if it does
    if os.path.exists("data/maildir/"):
        print("The Enron dataset has already been downloaded and extracted.")
        return

    # Create a data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    # URL of the Enron dataset
    url = "https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz"
    
    # Download file path
    tar_file_path = data_dir / "enron_mail.tar.gz"
    
    print("Downloading Enron dataset...")
    # Download the file with progress tracking
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    # Stream the download with progress tracking
    with open(tar_file_path, 'wb') as file:
        if total_size == 0:
            # If content-length header is missing, download without progress tracking
            file.write(response.content)
        else:
            # Download with progress bar
            downloaded = 0
            for data in response.iter_content(chunk_size=8192):
                downloaded += len(data)
                file.write(data)
                progress = int(50 * downloaded / total_size)
                print(f"\rDownload progress: [{'=' * progress}{' ' * (50-progress)}] {downloaded}/{total_size} bytes", end='')
    
    print("\nExtracting files...")
    # Extract the tar.gz file to the data directory
    with tarfile.open(tar_file_path, 'r:gz') as tar:
        tar.extractall(path=data_dir)
    
    print("Download and extraction complete!")
    print(f"Files extracted to: {data_dir.absolute()}")
    
    # Optionally remove the tar.gz file to save space
    os.remove(tar_file_path)
    
    return str(data_dir.absolute())

# Example usage
if __name__ == "__main__":
    # First download and extract the dataset
    data_dir = extract_data_from_source()