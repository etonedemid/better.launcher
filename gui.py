import tkinter as tk
from tkinter import ttk
import shutil
import os
import requests
import hashlib
import webbrowser
import subprocess
import json
from pathlib import Path

# ------------------------------------
# Global config and file paths
# ------------------------------------
CONFIG_FILE = "config.txt"
THEMES_FOLDER = "themes"

# Default config values
config = {
    "update_enabled": True,
    "assets_saving_enabled": True,
    "theme": "Dark"  # Default theme
}

themes = {}  # Holds the available themes

# Holds the daemon subprocess so we can kill it on exit
daemon_process = None

# ------------------------------------
# Config load/save
# ------------------------------------
def load_settings():
    global config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try:
                file_config = json.load(f)
                config.update(file_config)
            except json.JSONDecodeError:
                print("Failed to decode config file. Using defaults.")
    else:
        print("No config file found. Using defaults.")

def save_settings():
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

# ------------------------------------
# Theme management
# ------------------------------------
def load_themes():
    """
    Load themes from the THEMES_FOLDER. Each theme is a .txt file.
    """
    global themes
    themes.clear()

    themes_path = Path(THEMES_FOLDER)
    if not themes_path.exists():
        themes_path.mkdir()
        # Create a default Dark theme file if it doesn't exist
        with open(themes_path / "Dark.txt", "w") as f:
            f.write(
                "background=#111111\n"
                "foreground=#dcdcdc\n"
                "accent=#222222\n"
                "button_bg=#282828\n"
                "entry_bg=#c8c8c8\n"
            )

    for theme_file in themes_path.glob("*.txt"):
        theme_name = theme_file.stem
        with open(theme_file, "r") as f:
            try:
                theme_data = {}
                for line in f:
                    key, value = line.strip().split("=")
                    theme_data[key] = value
                themes[theme_name] = theme_data
            except Exception as e:
                print(f"Failed to load theme {theme_file}: {e}")

def setup_theme(root, theme_name):
    """
    Apply a theme to the application.
    """
    style = ttk.Style(root)
    theme_data = themes.get(theme_name, themes["Dark"])  # Default to "Dark" theme

    bg_color = theme_data.get("background", "#111111")
    fg_color = theme_data.get("foreground", "#dcdcdc")
    accent_color = theme_data.get("accent", "#222222")
    button_bg = theme_data.get("button_bg", "#282828")
    entry_bg = theme_data.get("entry_bg", "#c8c8c8")

    style.theme_use("clam")
    style.configure(
        ".",
        background=bg_color,
        foreground=fg_color,
        fieldbackground=entry_bg,
        bordercolor=bg_color
    )
    style.configure("TFrame", background=bg_color)
    style.configure("TLabel", background=bg_color, foreground=fg_color)
    style.configure(
        "TButton",
        background=button_bg,
        foreground=fg_color,
        relief="flat",
        padding=(6, 4)
    )
    style.map("TButton", background=[("active", accent_color)])
    style.configure("TCheckbutton", background=bg_color, foreground=fg_color)
    style.map(
        "TCheckbutton",
        background=[("active", bg_color)],
        foreground=[("selected", accent_color)]
    )

    root.configure(bg=bg_color)

# ------------------------------------
# Daemon-related functionality
# ------------------------------------
def download_daemon():
    if not config["update_enabled"]:
        print("Daemon updates are disabled.")
        return
    
    print("Downloading daemon...")
    daemon_url = "http://better-game.network/daemon"
    daemon_path = Path("daemon")

    try:
        response = requests.get(daemon_url, stream=True, timeout=10)
        if response.status_code == 200:
            with open(daemon_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("Daemon downloaded successfully.")
            daemon_path.chmod(0o755)
        else:
            print(f"Failed to download daemon: {response.status_code}")
    except requests.RequestException as e:
        print(f"Error downloading daemon: {e}")

def start_daemon():
    global daemon_process
    daemon_path = Path("./daemon")
    if not daemon_path.exists():
        print("Daemon not found. Downloading...")
        download_daemon()

    try:
        daemon_process = subprocess.Popen("./daemon", shell=False)
        print("Daemon started successfully.")
    except Exception as e:
        print(f"Failed to start daemon: {e}")

def stop_daemon():
    global daemon_process
    if daemon_process:
        try:
            daemon_process.terminate()
            daemon_process.wait(5)  # Wait for graceful shutdown
            print("Daemon stopped.")
        except Exception as e:
            print(f"Failed to stop daemon: {e}")
        daemon_process = None

# ------------------------------------
# GUI: Redesigned Options Menu
# ------------------------------------
class OptionsWindow(tk.Toplevel):
    """
    A redesigned options menu with a cleaner and more modern look.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Options")
        self.geometry("400x300")
        self.configure(bg=parent["bg"])  # match theme background

        self.update_var = tk.BooleanVar(value=config["update_enabled"])
        self.assets_var = tk.BooleanVar(value=config["assets_saving_enabled"])
        self.theme_var = tk.StringVar(value=config["theme"])

        # Header
        header = ttk.Label(self, text="Options", font=("Segoe UI", 14, "bold"))
        header.pack(pady=10)

        # Daemon updates toggle
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="x", pady=5)
        ttk.Label(frame, text="Enable Daemon Updates:").grid(row=0, column=0, sticky="w", padx=5)
        update_check = ttk.Checkbutton(frame, variable=self.update_var, command=self.on_update_toggle)
        update_check.grid(row=0, column=1, sticky="e", padx=5)

        # Assets saving toggle
        frame2 = ttk.Frame(self, padding=10)
        frame2.pack(fill="x", pady=5)
        ttk.Label(frame2, text="Enable Assets Saving:").grid(row=0, column=0, sticky="w", padx=5)
        assets_check = ttk.Checkbutton(frame2, variable=self.assets_var, command=self.on_assets_toggle)
        assets_check.grid(row=0, column=1, sticky="e", padx=5)

        # Theme selection dropdown
        frame3 = ttk.Frame(self, padding=10)
        frame3.pack(fill="x", pady=5)
        ttk.Label(frame3, text="Select Theme:").grid(row=0, column=0, sticky="w", padx=5)
        theme_dropdown = ttk.Combobox(frame3, values=list(themes.keys()), textvariable=self.theme_var, state="readonly")
        theme_dropdown.grid(row=0, column=1, sticky="e", padx=5)
        theme_dropdown.bind("<<ComboboxSelected>>", self.on_theme_change)

        # Close button
        close_btn = ttk.Button(self, text="Close", command=self.on_close)
        close_btn.pack(pady=20)

    def on_update_toggle(self):
        config["update_enabled"] = self.update_var.get()
        print(f"Daemon update is now {'enabled' if config['update_enabled'] else 'disabled'}.")

    def on_assets_toggle(self):
        config["assets_saving_enabled"] = self.assets_var.get()
        print(f"Assets saving is now {'enabled' if config['assets_saving_enabled'] else 'disabled'}.")

    def on_theme_change(self, event=None):
        config["theme"] = self.theme_var.get()
        print(f"Theme changed to {config['theme']}.")
        setup_theme(self.master, config["theme"])  # Apply the selected theme dynamically

    def on_close(self):
        save_settings()
        self.destroy()

# ------------------------------------
# GUI: Main Menu
# ------------------------------------
def on_play_clicked():
    start_daemon()
    webbrowser.open("https://better.game/#/play")

def on_exit_clicked(root):
    save_settings()
    stop_daemon()
    root.quit()

def main_menu():
    root = tk.Tk()
    root.title("made by etonedemid")

    load_themes()
    setup_theme(root, config["theme"])

    main_frame = ttk.Frame(root, padding=20)
    main_frame.grid(row=0, column=0, sticky="nsew")
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    title_label = ttk.Label(main_frame, text="Better Launcher", font=("Segoe UI", 16, "bold"))
    title_label.grid(row=0, column=0, pady=(0, 20))

    play_button = ttk.Button(main_frame, text="Play", command=on_play_clicked)
    play_button.grid(row=1, column=0, sticky="ew", pady=5)

    options_button = ttk.Button(main_frame, text="Options", command=lambda: OptionsWindow(root))
    options_button.grid(row=2, column=0, sticky="ew", pady=5)

    exit_button = ttk.Button(main_frame, text="Exit", command=lambda: on_exit_clicked(root))
    exit_button.grid(row=3, column=0, sticky="ew", pady=5)

    root.mainloop()

# ------------------------------------
# Entry point
# ------------------------------------
if __name__ == "__main__":
    load_settings()
    main_menu()
