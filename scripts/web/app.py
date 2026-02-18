"""
AirCube Web App
A Flask web server that reads from AirCube serial device and streams data to browsers.
"""

import collections
import csv
import json
import os
import re
import signal
import sys
from datetime import datetime
from pathlib import Path
from threading import Lock, Thread

import serial
from flask import Flask, render_template
from flask_socketio import SocketIO
from serial.tools import list_ports

# JSON pattern for parsing sensor data
JSON_PATTERN = re.compile(r"\{.*\}")

# CSV header compatible with other AirCube scripts
CSV_HEADER = [
    "timestamp",
    "ens210_status",
    "temperature_c",
    "temperature_f",
    "humidity",
    "ens16x_status",
    "etvoc",
    "eco2",
    "aqi",
]

app = Flask(__name__)
app.config["SECRET_KEY"] = "aircube-secret-key-change-in-production"
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
serial_connection = None
serial_lock = Lock()
data_buffer = collections.deque(maxlen=100000)
t0 = None

# CSV logging
csv_file = None
csv_writer = None
log_directory = None


def parse_json_line(line):
    """Parse a JSON sensor data line into a flat dict."""
    match = JSON_PATTERN.search(line)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return {
            "timestamp": data.get("timestamp"),
            "temperature_c": data["ens210"].get("temperature_c"),
            "temperature_f": data["ens210"].get("temperature_f"),
            "humidity": data["ens210"].get("humidity"),
            "ens210_status": data["ens210"].get("status"),
            "ens16x_status": data["ens16x"].get("status"),
            "etvoc": data["ens16x"].get("etvoc"),
            "eco2": data["ens16x"].get("eco2"),
            "aqi": data["ens16x"].get("aqi"),
        }
    except (KeyError, TypeError, json.JSONDecodeError):
        return None


def find_aircube_port():
    """Try to auto-detect AirCube device."""
    ports = list_ports.comports()
    # Try to find ESP32 device
    for port in ports:
        if (
            "USB" in port.description
            or "ESP32" in port.description
            or "CP210" in port.description
        ):
            return port.device
    return None


def init_csv_logging(log_dir):
    """Initialize CSV logging if directory is configured."""
    global csv_file, csv_writer, log_directory

    if not log_dir:
        return False

    # Convert to Path object
    log_path = Path(log_dir)

    # Check if directory exists
    if not log_path.exists():
        print(f"Warning: Log directory '{log_dir}' does not exist. Creating it...")
        try:
            log_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error: Could not create log directory: {e}")
            return False

    if not log_path.is_dir():
        print(f"Error: '{log_dir}' is not a directory")
        return False

    # Create timestamped CSV file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = log_path / f"aircube_log_{timestamp}.csv"

    try:
        csv_file = open(csv_filename, "w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(CSV_HEADER)
        csv_file.flush()
        log_directory = log_dir
        print(f"CSV logging enabled: {csv_filename}")
        return True
    except Exception as e:
        print(f"Error: Could not open CSV file for writing: {e}")
        return False


def serial_reader_thread(port, baud=115200):
    """Background thread that reads serial data and broadcasts to all clients."""
    global serial_connection, t0

    try:
        with serial.Serial(port, baud, timeout=1) as ser:
            serial_connection = ser
            print(f"Connected to {port} at {baud} baud")

            while serial_connection:
                try:
                    line = ser.readline()
                    if line:
                        decoded = line.decode(errors="ignore").strip()
                        parsed = parse_json_line(decoded)

                        if parsed:
                            # Prepare data for broadcast
                            broadcast_data = {
                                "time": parsed.get("timestamp"),
                                "temperature_f": parsed.get("temperature_f"),
                                "humidity": parsed.get("humidity"),
                                "aqi": parsed.get("aqi"),
                                "eco2": parsed.get("eco2"),
                                "etvoc": parsed.get("etvoc"),
                            }

                            # Store in buffer
                            data_buffer.append(broadcast_data)

                            # Write to CSV if logging is enabled
                            if csv_writer:
                                row = [
                                    parsed.get("timestamp"),
                                    parsed.get("ens210_status"),
                                    parsed.get("temperature_c"),
                                    parsed.get("temperature_f"),
                                    parsed.get("humidity"),
                                    parsed.get("ens16x_status"),
                                    parsed.get("etvoc"),
                                    parsed.get("eco2"),
                                    parsed.get("aqi"),
                                ]
                                csv_writer.writerow(row)
                                csv_file.flush()

                            # Broadcast to all connected clients
                            socketio.emit("sensor_data", broadcast_data)

                except (serial.SerialException, OSError) as e:
                    print(f"Serial error: {e}")
                    break

    except serial.SerialException as e:
        print(f"Failed to open serial port: {e}")
    finally:
        serial_connection = None
        print("Serial connection closed")


@app.route("/")
def index():
    """Serve the main dashboard."""
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():
    """When a client connects, send them historical data."""
    print(f"Client connected")
    # Send historical data buffer
    if data_buffer:
        socketio.emit("historical_data", list(data_buffer))


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnect."""
    print(f"Client disconnected")


@socketio.on("request_history")
def handle_history_request():
    """Send historical data on request."""
    if data_buffer:
        socketio.emit("historical_data", list(data_buffer))


def cleanup():
    """Cleanup resources on shutdown."""
    global csv_file
    if csv_file:
        print("\nClosing CSV log file...")
        csv_file.close()
        csv_file = None


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\nShutting down...")
    cleanup()
    sys.exit(0)


def main():
    """Start the web server."""
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    # Try to auto-detect AirCube port
    port = find_aircube_port()

    if not port:
        print("ERROR: No serial port found!")
        print("Available ports:")
        for p in list_ports.comports():
            print(f"  {p.device} - {p.description}")
        # return  # Comment out to test locally without AirCube

        print("Adding test data to simulate connection...")
        import random

        for x in range(data_buffer.maxlen):
            broadcast_data = {
                "time": 1771380002099 + (x * 30000),
                "temperature_f": random.randint(0, 2000),
                "humidity": 30,
                "aqi": 80,
                "eco2": 200,
                "etvoc": 2000,
            }
            data_buffer.append(broadcast_data)

    print(f"Starting AirCube Web Server...")
    print(f"Using port: {port}")

    # Check for log directory configuration
    log_dir = os.environ.get("AIRCUBE_LOG_DIR")
    if log_dir:
        print(f"Log directory configured: {log_dir}")
        if init_csv_logging(log_dir):
            print(f"✓ CSV logging enabled")
        else:
            print(f"✗ CSV logging failed to initialize")
    else:
        print("CSV logging disabled (set AIRCUBE_LOG_DIR to enable)")

    # Start serial reader thread
    serial_thread = Thread(target=serial_reader_thread, args=(port,), daemon=True)
    serial_thread.start()

    # Start Flask app
    print(f"\nWeb dashboard available at:")
    print(f"  http://localhost:5000")
    print(f"  http://<raspberry-pi-ip>:5000")
    print(f"\nPress Ctrl+C to stop\n")

    try:
        socketio.run(
            app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True
        )
    finally:
        cleanup()


if __name__ == "__main__":
    main()
