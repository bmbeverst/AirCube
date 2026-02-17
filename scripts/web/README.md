# AirCube Web Dashboard

A lightweight Flask web app for monitoring AirCube air quality sensor in real-time from any browser.

## Features

- **Real-time updates** via WebSockets (no page refresh needed)
- **Three live graphs**: Temperature/Humidity, AQI, eCO2/eTVOC
- **Current values display** with color-coded AQI
- **Responsive design** works on desktop, tablet, and mobile
- **Multi-client support** - multiple browsers can connect simultaneously
- **Auto-detection** of AirCube serial port

## Installation

### On Raspberry Pi 5 (ARM64)

All dependencies are ARM64-compatible (pure Python or have ARM wheels).

```bash
cd /home/pi
git clone <your-repo> aircube-web
cd aircube-web/scripts/web

uv venv
```

If you encounter any issues, install system dependencies first:

```bash
sudo apt update
sudo apt install python3-dev python3-pip python3-venv
```

### On Development Machine

```bash
cd scripts/web

# Create virtual environment
uv venv
uv run app.py
```

## Usage

### Run the web server

**Without CSV logging:**

```bash
uv run app.py
```

**With CSV logging:**

```bash
# Set the log directory (will be created if it doesn't exist)
export AIRCUBE_LOG_DIR=./data/logs
uv run app.py
```

Or in one line:

```bash
AIRCUBE_LOG_DIR=./data/logs uv run app.py
```

The server will:

1. Auto-detect the AirCube USB serial port
2. Start streaming sensor data
3. Serve the dashboard at `http://localhost:5000`
4. Log data to CSV (if AIRCUBE_LOG_DIR is set)

### Access from other devices

Find your Raspberry Pi's IP address:

```bash
hostname -I
```

Then access from any device on the same network:

```
http://<raspberry-pi-ip>:5000
```

For example: `http://192.168.1.100:5000`

## CSV Data Logging

The web app supports automatic CSV logging of all sensor data.

### Enable CSV Logging

**Option 1: Use the convenience script**

```bash
./start-with-logging.sh
```

This will save logs to `./data/logs` by default.

**Option 2: Set environment variable manually**

```bash
export AIRCUBE_LOG_DIR=/home/pi/aircube-data
python app.py
```

Or permanently in your shell profile (`~/.bashrc` or `~/.zshrc`):

```bash
echo 'export AIRCUBE_LOG_DIR=/home/pi/aircube-data' >> ~/.bashrc
source ~/.bashrc
```

### CSV File Format

- **Filename**: `aircube_log_YYYYMMDD_HHMMSS.csv` (timestamped when server starts)
- **Location**: In the configured `AIRCUBE_LOG_DIR` directory
- **Format**: Compatible with all other AirCube scripts
- **Columns**: timestamp, ens210_status, temperature_c, temperature_f, humidity, ens16x_status, etvoc, eco2, aqi

### Example

```bash
# Create log directory
mkdir -p ~/aircube-logs

# Start server with logging
AIRCUBE_LOG_DIR=~/aircube-logs python app.py
```

Logs will be saved as:

```
~/aircube-logs/aircube_log_20260216_143052.csv
~/aircube-logs/aircube_log_20260216_150123.csv
...
```

Each time you start the server, a new timestamped CSV file is created.

## Run on Boot (Raspberry Pi)

Create a systemd service to start automatically:

```bash
sudo nano /etc/systemd/system/aircube-web.service
```

Paste this content:

```ini
[Unit]
Description=AirCube Web Dashboard
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/aircube-web/scripts/web
Environment="PATH=/home/pi/aircube-web/scripts/web/venv/bin"
Environment="AIRCUBE_LOG_DIR=/home/pi/aircube-logs"
ExecStart=/home/pi/aircube-web/scripts/web/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable aircube-web
sudo systemctl start aircube-web
sudo systemctl status aircube-web
```

View logs:

```bash
sudo journalctl -u aircube-web -f
```

## Troubleshooting

### No serial port found

List available ports:

```bash
python -c "from serial.tools import list_ports; [print(f'{p.device} - {p.description}') for p in list_ports.comports()]"
```

### Permission denied on serial port

Add user to dialout group (Linux):

```bash
sudo usermod -a -G dialout $USER
# Log out and back in for changes to take effect
```

### Can't access from other devices

Make sure firewall allows port 5000:

```bash
sudo ufw allow 5000
```

## Architecture

```
AirCube Device (USB Serial @ 115200 baud)
    ↓
Flask Backend (Python)
    ├─ Serial Reader Thread
    ├─ WebSocket Server (Socket.IO)
    └─ HTTP Server (Dashboard)
    ↓
Web Browser (Any Device)
    ├─ Real-time Value Display
    └─ Three Live Charts (Chart.js)
```

## Dependencies

- **Flask**: Web framework
- **Flask-SocketIO**: WebSocket support for real-time data push
- **pyserial**: Serial port communication
- **Chart.js**: Client-side charting library (loaded via CDN)

## Performance

On Raspberry Pi 5:

- **CPU Usage**: <5%
- **RAM Usage**: ~60MB
- **Update Rate**: Real-time (1 sample/second from device)
- **Concurrent Users**: 10-20+ browsers easily

## Customization

### Change history buffer size

In `app.py`, line 16:

```python
data_buffer = collections.deque(maxlen=500)  # Change to desired size
```

In `templates/index.html`, line 132:

```javascript
const maxPoints = 3000; // Change to match or be less than backend
```

### Change port or host

In `app.py`, last line:

```python
socketio.run(app, host='0.0.0.0', port=5000, debug=False)
```

### Manually specify serial port

In `app.py`, change `main()` function:

```python
# port = find_aircube_port()  # Comment out auto-detection
port = '/dev/ttyUSB0'  # Specify your port
```

## License

Same as parent AirCube project.
