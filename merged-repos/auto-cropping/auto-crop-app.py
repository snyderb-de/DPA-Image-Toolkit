import customtkinter as ctk
import threading
import os
import shutil
from tkinter import filedialog
from crop_images import find_large_non_white_object

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AutoCropApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Auto Crop")
        self.geometry("620x520")
        self.resizable(False, False)

        self.folder_path = None
        self.is_running = False

        self._build_ui()

    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header, text="Auto Crop", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left")

        self.mode_switch = ctk.CTkSwitch(
            header, text="Dark mode", command=self._toggle_mode, width=100
        )
        self.mode_switch.pack(side="right")
        self.mode_switch.select()

        # ── Folder picker ────────────────────────────────────────
        folder_frame = ctk.CTkFrame(self)
        folder_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.folder_label = ctk.CTkLabel(
            folder_frame,
            text="No folder selected",
            anchor="w",
            text_color="gray",
        )
        self.folder_label.pack(side="left", fill="x", expand=True, padx=12, pady=12)

        ctk.CTkButton(
            folder_frame, text="Browse", width=90, command=self._pick_folder
        ).pack(side="right", padx=10, pady=10)

        # ── Start button ─────────────────────────────────────────
        self.start_btn = ctk.CTkButton(
            self,
            text="Start Cropping",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
            command=self._start,
        )
        self.start_btn.pack(fill="x", padx=20, pady=(0, 10))

        # ── Progress ─────────────────────────────────────────────
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=14)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            progress_frame, text="— / —", width=60, anchor="e"
        )
        self.progress_label.pack(side="right")

        # ── Log ──────────────────────────────────────────────────
        self.log_box = ctk.CTkTextbox(
            self,
            state="disabled",
            font=ctk.CTkFont(family="Courier", size=12),
        )
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    # ── Mode toggle ───────────────────────────────────────────────
    def _toggle_mode(self):
        if self.mode_switch.get():
            ctk.set_appearance_mode("dark")
            self.mode_switch.configure(text="Dark mode")
        else:
            ctk.set_appearance_mode("light")
            self.mode_switch.configure(text="Light mode")

    # ── Folder picker ─────────────────────────────────────────────
    def _pick_folder(self):
        path = filedialog.askdirectory(title="Select a folder containing images")
        if path:
            self.folder_path = path
            # Truncate long paths for display
            display = path if len(path) <= 60 else "…" + path[-57:]
            self.folder_label.configure(text=display, text_color=("black", "white"))
            self.start_btn.configure(state="normal")

    # ── Logging ───────────────────────────────────────────────────
    def _log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.configure(state="disabled")
        self.log_box.see("end")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ── Start ─────────────────────────────────────────────────────
    def _start(self):
        if self.is_running:
            return
        self.is_running = True
        self.start_btn.configure(state="disabled", text="Running…")
        self._clear_log()
        self.progress_bar.set(0)
        self.progress_label.configure(text="— / —")
        threading.Thread(target=self._run_crop, daemon=True).start()

    # ── Crop worker (background thread) ──────────────────────────
    def _run_crop(self):
        folder = self.folder_path
        output_folder = os.path.join(folder, "cropped")
        error_folder = os.path.join(output_folder, "errors")
        error_log_path = os.path.join(error_folder, "errors.txt")

        image_files = [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith((".tif", ".tiff", ".jpg", ".jpeg", ".png", ".bmp", ".gif"))
        ]

        if not image_files:
            self.after(0, self._log, "No image files found in the selected folder.")
            self.after(0, self._finish, [], 0)
            return

        total = len(image_files)
        errors = []
        saved = 0

        for i, image_file in enumerate(image_files):
            name = os.path.basename(image_file)
            try:
                result_path, reason = find_large_non_white_object(image_file, output_folder)
                if result_path:
                    saved += 1
                    self.after(0, self._log, f"✓  {name}")
                else:
                    self.after(0, self._log, f"—  {name}  ({reason})")
            except Exception as e:
                msg = f"{name}: {e}"
                errors.append(msg)
                os.makedirs(error_folder, exist_ok=True)
                shutil.copy2(image_file, os.path.join(error_folder, name))
                self.after(0, self._log, f"✗  {msg}")

            pct = (i + 1) / total
            count_text = f"{i + 1} / {total}"
            self.after(0, self.progress_bar.set, pct)
            self.after(0, self.progress_label.configure, {"text": count_text})

        if errors:
            with open(error_log_path, "w") as f:
                f.write("\n".join(errors))
            self.after(0, self._log, f"\n{len(errors)} error(s) written to {error_log_path}")

        self.after(0, self._finish, errors, saved, total)

    # ── Finish ────────────────────────────────────────────────────
    def _finish(self, errors, saved=0, total=0):
        self.is_running = False
        if errors:
            label = f"Done — {saved}/{total} saved, {len(errors)} error(s)"
        else:
            label = f"Done — {saved}/{total} saved"
        self.start_btn.configure(state="normal", text=label)
        self.after(4000, lambda: self.start_btn.configure(text="Start Cropping"))


if __name__ == "__main__":
    app = AutoCropApp()
    app.mainloop()
