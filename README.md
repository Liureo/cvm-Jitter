# cvm Jitter

`cvm Jitter` is a dual-PC hardware jitter recoil compensation project designed for **Apex Legends**. It runs on a control PC and sends mouse movement commands to a gaming PC through MAKCU or Ferrum hardware. Both a local desktop UI and a LAN WebUI are included.

## Features

- Dual-PC hardware control architecture
- MAKCU support
- Ferrum Serial support
- Ferrum Net (UDP) support
- Local desktop UI for hardware connection, configuration, and control
- LAN WebUI accessible from phones and other computers
- Multiple jitter patterns: upper left, upper right, horizontal, lower left, lower right, and circle
- Adjustable movement amplitude and step delay
- Optional vertical pressure with independent amplitude and interval settings
- Hold, toggle, and always-active trigger modes
- Left, right, middle, and two side mouse button triggers
- Optional Ads-only gate with a customizable ADS button
- Automatic configuration saving
- Hardware test movement
- Simplified Chinese, Traditional Chinese, and English UI languages
- Custom color themes for the desktop UI and WebUI

## Dual-PC Architecture

```text
Gaming PC ── Game and mouse input
    │
    └── MAKCU or Ferrum hardware ◀── Control PC running cvm Jitter
```

The control PC runs `cvm Jitter` and generates the jitter movement sequence. The hardware device receives serial or network commands and outputs mouse movement to the gaming PC. This project is designed for dual-PC setups only.

## System Requirements

- Windows 10 or Windows 11
- Python 3.10 or later
- Python Launcher for Windows (`py` command)
- MAKCU or Ferrum-compatible hardware
- An available USB serial port
- For Ferrum Net, a network connection between the control PC and the device

Main Python dependencies:

- PySide6
- pyserial
- Flask

Headless Raspberry Pi / Linux dependencies:

- Python 3.10 or later
- pyserial
- Flask
- A user account with serial device permission, usually through the `dialout` group

## Installation

1. Download or extract the project.
2. Run `setup.bat`.
3. The setup script creates a `.venv` virtual environment and installs the required dependencies.
4. Run `start.bat` after setup is complete.

Manual PowerShell installation:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Raspberry Pi Headless Service

`cvm Jitter` can also run on Raspberry Pi OS or another Linux system without
the local PySide desktop window. In this mode the Raspberry Pi connects to the
MAKCU or Ferrum hardware and exposes the existing LAN WebUI.

Recommended setup:

1. Copy the `cvm-Jitter` directory to the Raspberry Pi.
2. Install Python virtual environment support if needed:

```bash
sudo apt update
sudo apt install -y python3 python3-venv
```

3. Install the headless Python dependencies:

```bash
cd cvm-Jitter
chmod +x install_raspberry_pi.sh
./install_raspberry_pi.sh
```

4. Allow the current user to access USB serial devices, then log out and back in:

```bash
sudo usermod -aG dialout "$USER"
```

5. Run the WebUI service manually:

```bash
.venv/bin/python main_headless.py
```

The console prints a LAN URL such as `http://192.168.1.20:8765`. Open that URL
from a phone or computer on the same network.

Linux serial ports usually appear as `/dev/ttyUSB0`, `/dev/ttyACM0`, or stable
paths under `/dev/serial/by-id/`. You can select discovered ports in the WebUI
or save a manual path in `config.json`.

### systemd Autostart

Use the included installer to start the headless WebUI automatically at boot
from the directory where the project currently lives:

```bash
cd ~/Desktop/cvm-Jitter
./install_autostart.sh
```

The installer writes `/etc/systemd/system/cvm-jitter.service` using the current
project path and current Linux user, then enables and starts the service.

If you prefer a manual `/opt/cvm-Jitter` installation, the included
`cvm-jitter.service` file is a template. It assumes the app is installed at
`/opt/cvm-Jitter` and runs as the `pi` user.

Manual example:

```bash
sudo mkdir -p /opt
sudo cp -R cvm-Jitter /opt/cvm-Jitter
cd /opt/cvm-Jitter
sudo chown -R pi:pi /opt/cvm-Jitter
sudo -u pi ./install_raspberry_pi.sh
sudo cp cvm-jitter.service /etc/systemd/system/cvm-jitter.service
sudo systemctl daemon-reload
sudo systemctl enable --now cvm-jitter.service
```

Check service status and logs:

```bash
systemctl status cvm-jitter.service
journalctl -u cvm-jitter.service -f
```

If your Raspberry Pi username or install path is different, edit
`cvm-jitter.service` before copying it to `/etc/systemd/system/`.

### Desktop IP Popup

If the Raspberry Pi boots into the desktop, install the optional IP display
autostart helper:

```bash
cd ~/Desktop/cvm-Jitter
./install_ip_display.sh
```

On the next desktop login it waits until WiFi gets an IP, then shows the current
WebUI address, for example `http://192.168.1.20:8765`. It also shows the
`.local` hostname address when available. If no popup appears, install `zenity`:

```bash
sudo apt install -y zenity
```

Do not expose port `8765` directly to the public internet.

Note: 4,000,000 baud support depends on the Raspberry Pi, USB serial adapter,
cable quality, and kernel driver. If the device is unstable, start with
`115200` baud.

## Hardware Connection

### MAKCU

1. Connect the MAKCU device to the control PC and gaming PC.
2. Open `cvm Jitter` and select `MAKCU`.
3. Select the device COM port and its current baud rate.
4. Click **Connect Hardware**.
5. After connecting, click **Test Move** to verify movement output.

### Ferrum Serial

1. Select `Ferrum`.
2. Set the connection mode to `Serial`.
3. Select the correct COM port and baud rate.
4. Click **Connect Hardware**, then run **Test Move**.

### Ferrum Net

1. Select `Ferrum`.
2. Set the connection mode to `Net`.
3. Enter the device IP address, UDP port, and the 8-digit hexadecimal UUID shown by the device.
4. Confirm that the control PC can reach the device over the network.
5. Click **Connect Hardware**.

## Usage

1. Connect the hardware from the **Hardware** tab.
2. Run **Test Move** to verify that the device is working.
3. Select a jitter pattern from the **Settings** tab.
4. Configure movement amplitude and step delay.
5. Select a trigger mode and trigger button.
6. Enable **Ads only** and select the ADS button when jitter should require aiming down sights.
7. Enable vertical pressure from the **Advanced** tab when required.
8. Click **Enable Jitter** to arm the system.
9. Use the selected trigger mode to start movement.
10. Click **Stop** when finished.

Start with a low amplitude and a longer delay, then adjust gradually. Different sensitivities, DPI values, weapons, and attachments require different settings.

## Configuration Reference

| Setting | Description |
| --- | --- |
| Hardware | Select MAKCU or Ferrum |
| Connection mode | Select Serial or Net for Ferrum |
| COM port | The Windows serial port assigned to the hardware |
| Baud rate | Uses the current device baud rate; the application does not automatically switch the device to 4M |
| Jitter pattern | The repeating mouse movement path |
| Amplitude | Mouse movement distance for each step |
| Step delay | Time between jitter movement steps |
| Vertical pressure | Adds repeated downward movement while jitter is active |
| Pressure amplitude | Downward movement distance for each pressure step |
| Pressure interval | Time between downward pressure steps |
| Trigger mode | Hold, toggle, or always active |
| Trigger button | Mouse button state read from the connected hardware |
| Ads only | Requires the selected ADS button to be held before jitter can run |
| ADS button | Customizable ADS input; defaults to mouse right |

## Local Desktop UI

The local Qt desktop UI provides full access to:

- Hardware and connection settings
- Jitter and vertical pressure settings
- Trigger configuration
- Connection and run status
- Hardware test movement
- Local and WebUI color themes
- LAN WebUI controls

Most desktop settings are saved automatically when changed.

## LAN WebUI

When **LAN WebUI** is enabled in the desktop application, the server listens on `0.0.0.0:8765`. The application displays a LAN URL that can be opened from another phone or computer on the same network.

- The WebUI displays hardware connection and jitter status.
- Configuration changes are sent to the desktop application after clicking **Save Settings**.
- Live status polling does not overwrite unsaved form changes.
- Do not expose port `8765` directly to the public internet.

## Configuration File

Settings are stored in `config.json` in the project root.

To restore the default configuration:

1. Close the application.
2. Back up or delete `config.json`.
3. Start the application again.

The application recreates the configuration using its default values.

## Project Structure

```text
.
├── main.py                    # Qt application entry point
├── config.json                # User configuration
├── requirements.txt           # Python dependencies
├── setup.bat                  # First-time setup
├── start.bat                  # Application launcher
└── app
    ├── core                   # Configuration, themes, patterns, and workers
    ├── hardware               # MAKCU and Ferrum drivers
    ├── i18n                   # Desktop UI translations
    ├── ui                     # Qt interface, styles, and application icon
    │   └── icon
    │       └── cvm.jpg
    └── web                    # Flask WebUI
```

## Troubleshooting

### The COM port is missing

- Check the USB connection and device power.
- Confirm that the serial port appears in Windows Device Manager.
- Click **Refresh** in the application.
- Make sure another program is not using the serial port.

### Hardware connection fails

- Confirm that the selected hardware type, COM port, and baud rate are correct.
- MAKCU and Ferrum Serial use the device's current baud rate.
- The application does not automatically change the device baud rate.
- Ferrum Net requires the correct IP address, UDP port, and 8-digit hexadecimal UUID.

### Test movement works, but the result is unsuitable

- Adjust the jitter amplitude and step delay.
- Try another movement pattern.
- Tune the settings separately for the game sensitivity, mouse DPI, weapon, and attachments.

### The WebUI cannot be opened

- Confirm that the WebUI is enabled in the desktop application.
- Confirm that both devices are on the same local network.
- Allow Python through Windows Firewall on private networks.
- Use the LAN URL displayed by the application. Do not use `127.0.0.1` from another device.

## License

Copyright (c) 2025 asenyeroao-ct. All rights reserved.

This project is licensed under a custom license. See [LICENSE](LICENSE) for details.

### Key Points

- Personal, non-commercial use is permitted.
- Modification and redistribution are allowed with proper attribution.
- Commercial use is prohibited without written permission.
- The original author, `asenyeroao-ct`, must be credited in all distributions.

## Disclaimer

This project is for learning and testing purposes only. This program is designed for dual-PC setups only. The author is not responsible for any game account bans, penalties, hardware damage, data loss, or other consequences resulting from the use of this program, and no compensation will be provided. Users must bear the risks of use and understand the possible consequences. Users are responsible for ensuring compliance with applicable laws and the terms of service of any software or games used with this tool.

## Contributing

Contributions are welcome. Feel free to submit a pull request.

## Support

Join the Discord server for community support, discussions, and updates:

https://discord.gg/6SxKbrdq8C
