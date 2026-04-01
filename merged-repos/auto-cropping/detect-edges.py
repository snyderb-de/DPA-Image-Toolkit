import cv2
import os
from tkinter import Tk, filedialog

def detect_edges(input_path, blur_ksize=(7, 7), threshold1=150, threshold2=300):
    """
    Detect edges in an image using the Canny edge detection algorithm and save it to a subfolder.

    :param input_path: Path to the input image
    :param blur_ksize: Kernel size for GaussianBlur
    :param threshold1: First threshold for the hysteresis procedure in Canny
    :param threshold2: Second threshold for the hysteresis procedure in Canny
    """
    # Read the image
    image = cv2.imread(input_path)
    if image is None:
        print(f"Error: could not read image at {input_path}")
        return

    # Convert to grayscale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply GaussianBlur to reduce image noise
    blurred_image = cv2.GaussianBlur(gray_image, blur_ksize, 0)
    
    # Use Canny edge detection
    edges = cv2.Canny(blurred_image, threshold1, threshold2)
    
    # Prepare the subfolder path
    dir_name = os.path.dirname(input_path)
    edges_dir = os.path.join(dir_name, 'canny-edges')
    
    # Create the subfolder if it doesn't exist
    if not os.path.exists(edges_dir):
        os.makedirs(edges_dir)
    
    # Prepare the output file path
    base_name = os.path.basename(input_path)
    save_path = os.path.join(edges_dir, f"canny_{base_name}")
    
    # Save the image with detected edges
    cv2.imwrite(save_path, edges)
    
    print(f"Edges detected and image saved to {save_path}")

# GUI for file selection
root = Tk()
root.withdraw()  # Hide the main window
file_path = filedialog.askopenfilename(title="Select an image", filetypes=[("Image files", "*.tif *.tiff *.jpg *.jpeg *.png *.bmp *.gif")])

if file_path:
    detect_edges(file_path)
else:
    print("File selection cancelled.")
