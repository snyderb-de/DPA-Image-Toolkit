from PIL import Image
import os
import re
from collections import defaultdict

def merge_images(group, input_directory, output_directory):
    input_files = [os.path.join(input_directory, f) for f in os.listdir(input_directory) if f.startswith(group) and f.endswith('.tif')]
    images = [Image.open(x) for x in input_files]
    widths, heights = zip(*(i.size for i in images))

    total_height = sum(heights)
    max_width = max(widths)

    new_img = Image.new('RGB', (max_width, total_height))

    y_offset = 0
    for img in images:
        new_img.paste(img, (0, y_offset))
        y_offset += img.height
    new_img.save(os.path.join(output_directory, f'{group}.tif'))

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
        merge_images(group, path, path)
        print("Finished processing group", group)
    else:
        print("Operation cancelled by user.")
        break

print("Operation completed successfully.")
