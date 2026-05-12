class MovingAverage:
    def __init__(self, window_size):
        self.window_size = window_size
        self.values = []

    def add_value(self, value):
        self.values.append(value)
        if len(self.values) > self.window_size:
            self.values.pop(0)
        return self.average()

    def average(self):
        if self.values:
            return sum(self.values) / len(self.values)
        return 0

class SensorDataTracker:
    def __init__(self):
        self.min_value = float('inf')
        self.max_value = float('-inf')
        self.value = 0

    def update(self, value):
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)
        self.value = value
        if self.value != 0 and self.min_value != self.max_value:
            self.value = int((self.value - self.min_value) / (self.max_value - self.min_value) * 100)

    def get_min_max(self):
        return self.min_value, self.max_value

def map_value(value, min_in, max_in, min_out, max_out):
    return (value - min_in) * (max_out - min_out) / (max_in - min_in) + min_out

def get_angle_from_click(y_pos):
    return int(map_value(y_pos, 100, 0, 20, 90))

