#!/usr/bin/env bash
set -euo pipefail

PLIST="$HOME/Library/LaunchAgents/com.lukasfrantisak.wifiautotoggle.plist"
LOGDIR="$HOME/Library/Logs"
SCRIPT="$HOME/Dev/macos-wifi-auto-toggle/monitor_thunderbolt_wifi.py"

mkdir -p "$HOME/Library/LaunchAgents" "$LOGDIR"

cat > "$PLIST" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lukasfrantisak.wifiautotoggle</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/lukasfrantisak/Dev/macos-wifi-auto-toggle/monitor_thunderbolt_wifi.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/lukasfrantisak/Library/Logs/wifiautotoggle.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/lukasfrantisak/Library/Logs/wifiautotoggle.error.log</string>
    <key>WorkingDirectory</key>
    <string>/Users/lukasfrantisak/Dev/macos-wifi-auto-toggle</string>
</dict>
</plist>
PLIST

# reload agenta moderní cestou
launchctl bootout gui/$(id -u) "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap gui/$(id -u) "$PLIST"
launchctl kickstart -k gui/$(id -u)/com.lukasfrantisak.wifiautotoggle

echo "✓ Agent reloaded. Tail log:"
tail -n 50 "$LOGDIR/wifiautotoggle.log" || true