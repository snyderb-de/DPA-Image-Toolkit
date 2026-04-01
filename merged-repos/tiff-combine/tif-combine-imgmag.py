import os
import re
from collections import defaultdict
import subprocess

def merge_images(group, input_directory, output_directory):
    try:
        input_files = [os.path.join(input_directory, f) for f in os.listdir(input_directory) if f.startswith(group) and f.endswith('.tif')]
        output_file = os.path.join(output_directory, f'{group}.tif')
        subprocess.run(['convert'] + input_files + [output_file], check=True)
    except subprocess.CalledProcessError:
        print(f"Error: ImageMagick failed for group {group}")
        return False
    return True

path = input("Please input the path to your TIFF files: ")
if not os.path.exists(path) or not os.path.isdir(path):
    print("The path you entered does not exist or is not a directory.")
    exit()

files = [f for f in os.listdir(path) if f.endswith('.tif')]
groups = defaultdict(list)
for file in files:
    base_name = re.sub('_\d{3}$', '', file)
    groups[base_name].append(file)

print("\nPre-Combine Summary:")
print("Total groups:", len(groups))
print("Total files:", len(files))

for group in groups:
    print(f"\nDo you wish to continue with the operation for group {group}? (Y/N)")
    user_input = input()
    if user_input.lower() == 'y':
        print("Continuing with the operation...")
        if not merge_images(group, path, path):
            print("Operation failed. Exiting...")
            break
        print("Finished processing group", group)
    else:
        print("Operation cancelled by user.")
        break

print("Operation completed successfully.")
