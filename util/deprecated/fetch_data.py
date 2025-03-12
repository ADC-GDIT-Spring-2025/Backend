'''
fetch_data.py

This module is used to download and extract the Enron email dataset from the CMU servers.

It is only meant to be used once to retrieve the data and should not be run multiple times.

This module stores the dataset in the data/maildir/ directory, in which there are folders for each account.
'''

def extract_data_from_source():
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
    
    with open(tar_file_path, 'wb') as file:
        if total_size == 0:
            file.write(response.content)
        else:
            downloaded = 0
            for data in response.iter_content(chunk_size=8192):
                downloaded += len(data)
                file.write(data)
                progress = int(50 * downloaded / total_size)
                print(f"\rDownload progress: [{'=' * progress}{' ' * (50-progress)}] {downloaded}/{total_size} bytes", end='')
    
    print("\nExtracting files...")
    # Extract the tar.gz file
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