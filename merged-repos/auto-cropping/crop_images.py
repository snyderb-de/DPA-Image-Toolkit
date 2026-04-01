from PIL import Image
import cv2
import os
import shutil
from tkinter import Tk, filedialog

# Function to find large non-white object and save the cropped image
def find_large_non_white_object(input_path, output_folder, min_size=(50, 50), max_contours=100):
    # Read DPI metadata with Pillow
    pil_image = Image.open(input_path)
    dpi = pil_image.info.get('dpi')
    pil_image.close()

    image = cv2.imread(input_path)
    if image is None:
        raise ValueError("Image not found or path is incorrect")

    height, width = image.shape[:2]

    # Convert to grayscale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Threshold to find non-white areas
    _, thresh_image = cv2.threshold(gray_image, 253, 255, cv2.THRESH_BINARY_INV)

    # Find contours
    contours, _ = cv2.findContours(thresh_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter and sort contours by area
    large_contours = [cnt for cnt in contours if cv2.contourArea(cnt) >= min_size[0] * min_size[1]]
    large_contours = sorted(large_contours, key=cv2.contourArea, reverse=True)[:max_contours]

    os.makedirs(output_folder, exist_ok=True)

    if not contours:
        return None, "image appears blank or fully white — nothing to crop"

    if not large_contours:
        return None, f"something was found but it's too small to crop (minimum {min_size[0]}×{min_size[1]}px)"

    x, y, w, h = cv2.boundingRect(large_contours[0])

    # 2.5% of object size, clamped between 15px and 100px
    padding_x = max(15, min(100, int(0.025 * w)))
    padding_y = max(15, min(100, int(0.025 * h)))

    x_padded = max(x - padding_x, 0)
    y_padded = max(y - padding_y, 0)
    w_padded = min(w + 2 * padding_x, width - x_padded)
    h_padded = min(h + 2 * padding_y, height - y_padded)

    cropped_image = image[y_padded:y_padded + h_padded, x_padded:x_padded + w_padded]

    cropped_save_path = os.path.join(output_folder, os.path.basename(input_path))

    pil_cropped_image = Image.fromarray(cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB))
    if dpi:
        pil_cropped_image.save(cropped_save_path, dpi=dpi)
    else:
        pil_cropped_image.save(cropped_save_path)

    return cropped_save_path, None


# GUI for folder selection
def main():
    root = Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory(title="Select a folder containing images")

    if not folder_path:
        print("Folder selection cancelled.")
        return

    output_folder = os.path.join(folder_path, 'cropped')
    error_folder = os.path.join(output_folder, 'errors')
    error_log_path = os.path.join(error_folder, 'errors.txt')

    image_files = [
        os.path.join(folder_path, f) for f in os.listdir(folder_path)
        if f.lower().endswith(('.tif', '.tiff', '.jpg', '.jpeg', '.png', '.bmp', '.gif'))
    ]

    if not image_files:
        print("No image files found in the selected folder.")
        return

    errors = []
    for image_file in image_files:
        try:
            result_path, reason = find_large_non_white_object(image_file, output_folder)
            if result_path:
                print(f"Saved: {result_path}")
            else:
                print(f"Skipped: {os.path.basename(image_file)} — {reason}")
        except Exception as e:
            msg = f"{os.path.basename(image_file)}: {e}"
            print(f"Error: {msg}")
            errors.append(msg)
            os.makedirs(error_folder, exist_ok=True)
            shutil.copy2(image_file, os.path.join(error_folder, os.path.basename(image_file)))

    if errors:
        with open(error_log_path, 'w') as f:
            f.write('\n'.join(errors))
        print(f"\n{len(errors)} error(s) logged to {error_log_path}")

if __name__ == "__main__":
    main()
