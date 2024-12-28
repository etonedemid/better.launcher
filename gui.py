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

# Default config values
config = {
    "update_enabled": True,
    "assets_saving_enabled": True
}

# Holds the daemon subprocess so we can kill it on exit
daemon_process = None

# ------------------------------------
# Config load/save
# ------------------------------------
def load_settings():
    """
    Load JSON settings from CONFIG_FILE into the global 'config' dict.
    """
    global config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try:
                file_config = json.load(f)
                config["update_enabled"] = file_config.get("update_enabled", True)
                config["assets_saving_enabled"] = file_config.get("assets_saving_enabled", True)
            except json.JSONDecodeError:
                print("Failed to decode config file. Using defaults.")
    else:
        print("No config file found. Using defaults.")

def save_settings():
    """
    Save JSON settings from the global 'config' dict to CONFIG_FILE.
    """
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

# ------------------------------------
# Helper for paths
# ------------------------------------
def get_script_directory() -> Path:
    """Return the path to the directory containing this script."""
    return Path(__file__).resolve().parent

def get_daemon_path() -> Path:
    """
    Return the path to the 'daemon' file (executable) in the same directory.
    """
    return get_script_directory() / "daemon"

def get_assets_source_path() -> Path:
    """
    Return the path to the 'assets' folder in the same directory.
    """
    return get_script_directory() / "assets"

def get_tmp_assets_path() -> Path:
    """
    Return the path to the /tmp/Protoverse/assets folder (for Linux).
    """
    return Path("/tmp") / "Protoverse" / "assets"

# ------------------------------------
# Copy assets utilities
# ------------------------------------
def copy_assets_to_tmp():
    """
    Copy the local 'assets' folder to /tmp/Protoverse/assets (if enabled).
    """
    if not config["assets_saving_enabled"]:
        print("Assets saving is disabled. Skipping copy to tmp.")
        return

    src = get_assets_source_path()
    dst = get_tmp_assets_path()

    if not src.exists():
        print("No assets directory found locally.")
        return

    # Remove existing /tmp assets if they exist
    if dst.exists():
        shutil.rmtree(dst)

    try:
        shutil.copytree(src, dst)
        print("Assets copied to /tmp successfully.")
    except Exception as e:
        print(f"Error copying assets to /tmp: {e}")

def copy_assets_from_tmp():
    """
    Copy the assets from /tmp/Protoverse/assets back to the local 'assets' folder (if enabled).
    """
    if not config["assets_saving_enabled"]:
        print("Assets saving is disabled. Skipping copy from tmp.")
        return

    src = get_tmp_assets_path()
    dst = get_assets_source_path()

    if not src.exists():
        print("No assets directory found in /tmp/Protoverse. Skipping.")
        return

    # Remove local assets folder if it exists
    if dst.exists():
        shutil.rmtree(dst)

    try:
        shutil.copytree(src, dst)
        print("Assets copied back from /tmp to local directory successfully.")
    except Exception as e:
        print(f"Error copying assets from /tmp: {e}")

# ------------------------------------
# Daemon-related functions
# ------------------------------------
def download_daemon():
    if not config["update_enabled"]:
        print("Daemon updates are disabled.")
        return
    
    print("Downloading daemon...")
    daemon_url = "http://better-game.network/daemon"
    daemon_path = get_daemon_path()

    try:
        response = requests.get(daemon_url, stream=True, timeout=10)
        if response.status_code == 200:
            with open(daemon_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("Daemon downloaded successfully.")
            # After downloading, ensure it's executable
            daemon_path.chmod(0o755)
        else:
            print(f"Failed to download daemon: {response.status_code}")
    except requests.RequestException as e:
        print(f"Error downloading daemon: {e}")

def validate_daemon():
    if not config["update_enabled"]:
        print("Daemon updates are disabled.")
        return
    
    print("Validating daemon...")
    daemon_path = get_daemon_path()
    
    if not daemon_path.exists():
        download_daemon()
        return

    hash_url = "https://better-game.network/asset/index.txt"
    
    try:
        response = requests.get(hash_url, timeout=10)
        if response.status_code == 200:
            lines = response.text.splitlines()
            # Example line might be: "Hash: abc123..."
            # Adjust parsing as needed. We'll assume the last line has a hash.
            expected_hash = lines[-1].strip()[6:70]

            sha256_hash = hashlib.sha256()
            with open(daemon_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            current_hash = sha256_hash.hexdigest()

            if current_hash == expected_hash:
                print("Daemon is up-to-date.")
            else:
                print("Daemon hash mismatch. Downloading updated daemon...")
                download_daemon()
        else:
            print(f"Failed to retrieve hash file: {response.status_code}")
    except requests.RequestException as e:
        print(f"Error retrieving hash file: {e}")

def start_daemon():
    """
    1) Copy local assets -> /tmp
    2) Start the daemon
    """
    global daemon_process

    daemon_path = get_daemon_path()
    if not daemon_path.exists():
        print("Daemon not found. Please download or place it in the same folder.")
        return

    # Make sure daemon is executable
    daemon_path.chmod(0o755)

    copy_assets_to_tmp()

    print("Starting daemon...")
    try:
        daemon_process = subprocess.Popen([str(daemon_path)], shell=False)
        print("Daemon started successfully.")
    except Exception as e:
        print(f"Failed to start daemon: {e}")

def stop_daemon():
    """
    Stop the daemon process if it's running.
    """
    global daemon_process
    if daemon_process and daemon_process.poll() is None:
        print("Stopping daemon...")
        try:
            daemon_process.terminate()
            daemon_process.wait(5)  # optional wait for graceful shutdown
            print("Daemon stopped.")
        except Exception as e:
            print(f"Failed to stop daemon: {e}")
    daemon_process = None

# ------------------------------------
# Browser
# ------------------------------------
def open_browser():
    print("Opening browser...")
    try:
        webbrowser.open("https://better.game/#/play")
        print("Browser opened successfully.")
    except Exception as e:
        print(f"Failed to open browser: {e}")

# ------------------------------------
# GUI: Dark Theme Setup
# ------------------------------------
def setup_dark_theme(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    # Define color palette
    bg_color = "#111111"     # main background
    fg_color = "#dcdcdc"     # text
    accent_color = "#222222" # accent color
    button_bg = "#282828"    # button background
    entry_bg = "#c8c8c8"     # entry frames, etc.

    # General styling
    style.configure(
        ".",
        background=bg_color,
        foreground=fg_color,
        fieldbackground=entry_bg,
        bordercolor=bg_color
    )
    # Frame
    style.configure("TFrame", background=bg_color)
    # Label
    style.configure("TLabel", background=bg_color, foreground=fg_color)
    # Button
    style.configure("TButton",
        background=button_bg,
        foreground=fg_color,
        relief="flat",
        padding=(6, 4)
    )
    style.map("TButton", background=[("active", accent_color)])
    # Checkbutton
    style.configure("TCheckbutton", background=bg_color, foreground=fg_color)
    style.map("TCheckbutton",
        background=[("active", bg_color)],
        foreground=[("selected", accent_color)]
    )

    default_font = ("Segoe UI", 10)
    style.configure(".", font=default_font)

    # Root window background
    root.configure(bg=bg_color)

# ------------------------------------
# GUI: Main Menu
# ------------------------------------
def on_play_clicked():
    validate_daemon()
    open_browser()
    start_daemon()

def on_options_clicked(root):
    OptionsWindow(root)

def on_exit_clicked(root):
    """
    1) Copy /tmp -> local assets
    2) Stop daemon
    3) Save settings
    4) Exit
    """
    copy_assets_from_tmp()
    stop_daemon()
    save_settings()
    root.quit()

def main_menu():
    root = tk.Tk()
    root.title("Better-Game Launcher")

    setup_dark_theme(root)

    main_frame = ttk.Frame(root, padding=20)
    main_frame.grid(row=0, column=0, sticky="nsew")
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    # Title
    title_label = ttk.Label(main_frame, text="better.launcher", font=("Segoe UI", 14, "bold"))
    title_label.grid(row=0, column=0, pady=(0, 20))

    # Play button
    play_button = ttk.Button(main_frame, text="Play", command=on_play_clicked)
    play_button.grid(row=1, column=0, sticky="ew", pady=5)

    # Options button
    options_button = ttk.Button(main_frame, text="Options", command=lambda: on_options_clicked(root))
    options_button.grid(row=2, column=0, sticky="ew", pady=5)

    # Exit button
    exit_button = ttk.Button(main_frame, text="Exit", command=lambda: on_exit_clicked(root))
    exit_button.grid(row=3, column=0, sticky="ew", pady=5)

    root.mainloop()

# ------------------------------------
# GUI: Options Window
# ------------------------------------
class OptionsWindow(tk.Toplevel):
    """
    A separate window for toggling update_enabled and assets_saving_enabled.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Options")
        self.geometry("300x150")
        self.configure(bg=parent["bg"])  # match dark background

        self.update_var = tk.BooleanVar(value=config["update_enabled"])
        self.assets_var = tk.BooleanVar(value=config["assets_saving_enabled"])

        # Daemon updates toggle
        self.update_check = ttk.Checkbutton(
            self, text="Enable Daemon Updates", variable=self.update_var,
            command=self.on_update_toggle
        )
        self.update_check.pack(pady=10, anchor="w")

        # Assets saving toggle
        self.assets_check = ttk.Checkbutton(
            self, text="Enable Assets Saving", variable=self.assets_var,
            command=self.on_assets_toggle
        )
        self.assets_check.pack(pady=5, anchor="w")

        # Close button
        close_btn = ttk.Button(self, text="Close", command=self.on_close)
        close_btn.pack(pady=10)

    def on_update_toggle(self):
        config["update_enabled"] = self.update_var.get()
        print(f"Daemon update is now {'enabled' if config['update_enabled'] else 'disabled'}.")

    def on_assets_toggle(self):
        config["assets_saving_enabled"] = self.assets_var.get()
        print(f"Assets saving is now {'enabled' if config['assets_saving_enabled'] else 'disabled'}.")

    def on_close(self):
        save_settings()
        self.destroy()

# ------------------------------------
# Entry point
# ------------------------------------
if __name__ == "__main__":
    load_settings()
    main_menu()
