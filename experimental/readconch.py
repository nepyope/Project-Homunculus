import pygame
import serial
import time
import serial.tools.list_ports
from conchutils import *
import socket
import json
import threading
# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Servo and Sensor Visualizer")

# Colors and Fonts
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
FONT = pygame.font.SysFont('Arial', 20)

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65429     # Port to listen on (non-privileged ports are > 1023)
global held_down
def reset_servos(servo_values):
    for i in range(len(servo_values)):
        servo_values[i] = 55
        set_servo(i + 4, 55)
    return servo_values

def receive_data(conn):
    global held_down
    held_down = False
    while True:
        data = conn.recv(4096*16)
        if not data:
            break
        d = data.decode()
        print(d)
        #only consider the first dict
        d= d.split('}')[0] + '}'
        received_data = json.loads(d)
        # Update servo angles based on received data
        for i, angle in enumerate(received_data.get("servo_angles", [])):
            if 0 <= i < len(servo_values):
                servo_values[i] = angle
                if not held_down:
                    set_servo(i + 4, angle)
#list all ports

ports = serial.tools.list_ports.comports()
ser = serial.Serial(port=ports[0].device, baudrate=115200)

def set_servo(servo_num, angle):
    command = f"{servo_num} {angle}\n"
    ser.write(command.encode())

# Initialize filters and trackers for each sensor
sensor_filters = [MovingAverage(10) for _ in range(8)]
sensor_trackers = [SensorDataTracker() for _ in range(8)]

# Initial servo and sensor values
servo_values = [55 + i for i in range(4, 12)]
s_values = [sensor_trackers[6], sensor_trackers[1], sensor_trackers[2], sensor_trackers[4], sensor_trackers[3], sensor_trackers[7], sensor_trackers[5], sensor_trackers[0]]
button_values = [0, 0]  # Assuming two buttons


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    conn, addr = s.accept()
    with conn:
        print('Connected by', addr)

        threading.Thread(target=receive_data, args=(conn,)).start()
        for t in range(10000000000):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    if 300 <= y <= 400:
                        box_index = x // 100
                        if 0 <= box_index < 8:
                            relative_y = y - 300
                            servo_angle = get_angle_from_click(relative_y)
                            servo_values[box_index] = servo_angle
                            set_servo(box_index + 4, servo_angle)

            # Read data from Arduino
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').rstrip()
                values = line.split(',')
                if len(values) != 10:
                    continue
                raw_sensor_values = list(map(int, values[:8]))
                for i, value in enumerate(raw_sensor_values):
                    filtered_value = sensor_filters[i].add_value(value)
                    sensor_trackers[i].update(filtered_value)
                button_values = list(map(int, values[8:10]))


            # Drawing
            screen.fill(BLACK)
            for i in range(8):
                # Draw box for each servo and sensor
                box_rect = pygame.Rect(i * 100, 300, 80, 100)
                pygame.draw.rect(screen, WHITE, box_rect, 2)

                # Fill left half of the box based on servo angle
                angle_height = map_value(servo_values[i], 20, 90, 100, 0)
                servo_rect = pygame.Rect(i * 100, 300, 40, angle_height)
                pygame.draw.rect(screen, WHITE, servo_rect)

                sensor_rect = pygame.Rect(i * 100 + 40, 300, 40, s_values[i].value)
                pygame.draw.rect(screen, GREEN, sensor_rect)

                # Display servo angle and sensor reading
                angle_text = FONT.render(f"Angle: {servo_values[i]}", True, WHITE)
                sensor_text = FONT.render(f"{s_values[i].value}", True, WHITE)
                min_value, max_value = s_values[i].get_min_max()
                min_text = FONT.render(f"{min_value}", True, WHITE)
                max_text = FONT.render(f"{max_value}", True, WHITE)
                screen.blit(angle_text, (i * 100 + 10, 260))
                screen.blit(sensor_text, (i * 100 + 10, 410))
                screen.blit(min_text, (i * 100 + 10, 430))
                screen.blit(max_text, (i * 100 + 10, 450))

                # Display button state boxes
                button_color = WHITE if button_values[i % 2] else BLACK
                pygame.draw.rect(screen, button_color, (i * 100 + 10, 10, 20, 20))

            if button_values[0] == 1 and button_values[1] == 1:
                servo_values = reset_servos(servo_values)
                time.sleep(0.0333333)
                held_down = True
            else:
                held_down = False

            data_to_send = {
                "servo_values": servo_values,
                "s_values": [tracker.value for tracker in sensor_trackers],
                "button_values": button_values
            }
            json_data = json.dumps(data_to_send)
            conn.sendall(json_data.encode())

            pygame.display.flip()
            time.sleep(0.00001)
