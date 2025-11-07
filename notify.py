# notify.py
import subprocess

def notify(title: str, message: str):
    """
    Zobrazí macOS systémovou notifikaci pomocí AppleScriptu.
    """
    script = f'display notification "{message}" with title "{title}"'
    subprocess.run(["osascript", "-e", script])