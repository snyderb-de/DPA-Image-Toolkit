import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import subprocess
import re
import os

def select_folder():
    root = tk.Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory(title="Please select the folder containing your TIFF files")
    if not folder_path:
        messagebox.showinfo("Operation Cancelled", "No folder selected.")
        return None
    folder_path = Path(folder_path)
    if not folder_path.is_dir():
        messagebox.showerror("Error", "The path you entered does not exist or is not a directory.")
        return None
    return folder_path

def rename_tiffs(path):
    for tiff_file in path.glob('*.tiff'):
        tiff_file.rename(tiff_file.with_suffix('.tif'))

def create_subfolder(path):
    combined_tifs_folder = path / "combined-tifs"
    combined_tifs_folder.mkdir(exist_ok=True)
    return combined_tifs_folder

def get_group_name(file_path):
    file_name = file_path.name
    underscore_count = file_name.count("_")
    if underscore_count == 1:
        return file_name.split("_")[0]
    elif underscore_count == 2:
        match = re.match(r'^(.*?_.*)_\d+\..*$', file_name)
        if match:
            return match.group(1)
    return file_name

def merge_images(group, input_directory, output_directory, log_textbox, progress_bar):
    tif_files = list(input_directory.glob(f"{group}*.tif"))
    if not tif_files:
        log_textbox.insert(tk.END, f"No TIFF files found for group: {group}\n")
        return

    input_files = [str(file.resolve()) for file in tif_files]
    input_files_joined = ','.join(f'"{file}"' for file in input_files)
    output_file = f'"{(output_directory / f"{group}.tif").resolve()}"'

    irfanview_path = Path(os.environ.get("ProgramFiles", ""), "IrfanView", "i_view64.exe").resolve()
    command = f'"{irfanview_path}" /cmdexit /multitif=({output_file},{input_files_joined})'

    try:
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.stderr:
            log_textbox.insert(tk.END, f"Error in merging TIFF files: {result.stderr}\n")
        else:
            for file in tif_files:
                log_textbox.insert(tk.END, f"Processed file: {file}\n")
            progress_bar['value'] += len(tif_files)
            log_textbox.see(tk.END)
    except subprocess.CalledProcessError as e:
        log_textbox.insert(tk.END, f"Error occurred: {e}\n")

def terminate_application(root):
    root.quit()
    root.destroy()

def process_groups(groups, input_directory, output_directory, log_textbox, progress_bar, process_button, root):
    total_groups = len(groups)
    progress_increment = 100 / total_groups

    for group in groups:
        log_textbox.insert(tk.END, f"Processing group: {group}\n")
        merge_images(group, input_directory, output_directory, log_textbox, progress_bar)
        log_textbox.insert(tk.END, f"Finished processing group: {group}\n\n")
        log_textbox.see(tk.END)
        progress_bar['value'] += progress_increment
        root.update_idletasks()
    process_button.config(text="Exit", command=lambda: terminate_application(root))

def main():
    folder_path = select_folder()
    if folder_path is None:
        return

    rename_tiffs(folder_path)
    combined_tifs_folder = create_subfolder(folder_path)
    tif_files = list(folder_path.glob('*.tif'))
    groups = set(get_group_name(file) for file in tif_files)

    if messagebox.askyesno("Confirmation", f"Do you wish to continue with the operation?\nFound {len(groups)} groups to process."):
        root = tk.Tk()
        root.title("Processing Your Files Into Groups")
        text_frame = tk.Frame(root)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        log_textbox = tk.Text(text_frame, height=15, width=80)
        log_textbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(text_frame, command=log_textbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        log_textbox.config(yscrollcommand=scrollbar.set)
        progress_bar = ttk.Progressbar(root, orient='horizontal', mode='determinate', length=280)
        progress_bar.pack(padx=10, pady=10, fill=tk.X)
        process_button = tk.Button(root, text="Start Processing", command=lambda: process_groups(groups, folder_path, combined_tifs_folder, log_textbox, progress_bar, process_button, root))
        process_button.pack(pady=10)
        root.mainloop()

if __name__ == "__main__":
    main()
