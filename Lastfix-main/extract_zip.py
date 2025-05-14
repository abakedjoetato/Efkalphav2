import os
import zipfile
import shutil

# Path to the zip file
zip_path = '/home/runner/workspace/attached_assets/Morefix-main.zip'

# Extract to a temporary directory
temp_dir = '/tmp/bot_extract'
if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
os.makedirs(temp_dir, exist_ok=True)

# Extract the zip file
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(temp_dir)

# List the extracted contents
print("Extracted files:")
for root, dirs, files in os.walk(temp_dir):
    level = root.replace(temp_dir, '').count(os.sep)
    indent = ' ' * 4 * level
    print(f"{indent}{os.path.basename(root)}/")
    sub_indent = ' ' * 4 * (level + 1)
    for file in files:
        print(f"{sub_indent}{file}")

# Copy all files from the extracted directory to the main directory
# Assuming the zip contains a single top-level directory
extracted_dir = None
for item in os.listdir(temp_dir):
    item_path = os.path.join(temp_dir, item)
    if os.path.isdir(item_path):
        extracted_dir = item_path
        break

if extracted_dir:
    print(f"\nCopying files from {extracted_dir} to current directory...")
    for item in os.listdir(extracted_dir):
        src = os.path.join(extracted_dir, item)
        dst = os.path.join('.', item)
        
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"Copied directory: {item}")
        else:
            if os.path.exists(dst):
                os.remove(dst)
            shutil.copy2(src, dst)
            print(f"Copied file: {item}")
else:
    print("No directory found in the extracted zip")