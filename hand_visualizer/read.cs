import serial
import serial.tools.list_ports
import socket
import threading
import json

# Set up the localhost server details
HOST = '127.0.0.1'
PORT = 65432  # You can change this to any available port

def handle_client(conn):
    try:
        # Read from the serial port and send data to the client
        while True:
            if ser.in_waiting > 0:
                # Read a line from the serial port
                line = ser.readline().decode('utf-8').strip()
                
                # Format data as needed (e.g., JSON)
                data_to_send = {
                    "serial_data": line
                }
                json_data = json.dumps(data_to_send)
                
                # Send data to the client
                conn.sendall(json_data.encode())
                print(f"Sent: {json_data}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

# List all available serial ports and pick the first one
ports = list(serial.tools.list_ports.comports())
if not ports:
    print("No serial ports found.")
    exit()

# Pick the first available port
serial_port = ports[0].device
baud_rate = 115200  # Set the baud rate (must match the device's baud rate)

try:
    # Open the serial port
    with serial.Serial(serial_port, baud_rate, timeout=1) as ser:
        print(f"Reading from {serial_port}...")

        # Set up the server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            print(f"Server listening on {HOST}:{PORT}")

            while True:
                conn, addr = s.accept()
                print(f"Connected by {addr}")

                # Create a thread to handle the client
                client_thread = threading.Thread(target=handle_client, args=(conn,))
                client_thread.start()
except serial.SerialException as e:
    print(f"Serial Error: {e}")
except socket.error as e:
    print(f"Socket Error: {e}")
except KeyboardInterrupt:
    print("\nExiting...")
