class SimpleMovingQuantile:
    def __init__(self, window_size, num_sensors, quantile):
        """
        https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/quantile.htm
        
        Initialize the SimpleMovingQuantile class.

        Parameters:
        window_size (int): The number of data points to consider in the moving quantile.
        num_sensors (int): The number of sensors providing data.
        quantile (float): The quantile to calculate (between 0 and 1).
        """
        self.window_size = window_size
        self.num_sensors = num_sensors
        self.quantile = quantile
        self.data_queues = [[] for _ in range(num_sensors)]
        self.sorted_windows = [[] for _ in range(num_sensors)]
    
    def bisect_left(self, a, x, lo=0, hi=None):
        if lo < 0:
            raise ValueError('lo must be non-negative')
        if hi is None:
            hi = len(a)
        while lo < hi:
            mid = (lo + hi) // 2
            if a[mid] < x:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def insort(self, a, x, lo=0, hi=None):
        lo = self.bisect_left(a, x, lo, hi)
        a.insert(lo, x)
        
    def update_quantile(self, new_values):
        #print('num: ',self.num_sensors)
        for i in range(self.num_sensors):
            if len(self.data_queues[i]) == self.window_size:
                oldest_value = self.data_queues[i].pop(0)
                index = self.bisect_left(self.sorted_windows[i], oldest_value)
                self.sorted_windows[i].pop(index)

            self.data_queues[i].append(new_values[i])
            self.insort(self.sorted_windows[i], new_values[i])

        quantiles = []
        for i in range(self.num_sensors):
            n = len(self.sorted_windows[i])
            quantile_index = int(self.quantile * (n - 1))
            quantiles.append(self.sorted_windows[i][quantile_index])
        
        return quantiles
"""
# Example usage:
sensor_data = [
    [1, 10, 100],  # Measurements at time t0: sensor 1 = 1, sensor 2 = 10, sensor 3 = 100
    [2, 11, 101],  # Measurements at time t1
    [3, 12, 102],  # Measurements at time t2
    [4, 13, 103],  # Measurements at time t3
    [5, 14, 104],  # Measurements at time t4
    [6, 15, 105],  # Measurements at time t5
]

# Initialize the SimpleMovingQuantile class with a window size of 3, 3 sensors, and 0.5 quantile (median)
smq_calculator = SimpleMovingQuantile(window_size=3, num_sensors=3, quantile=0.5)

# Update the SMQ with each set of sensor data and print the results
for data in sensor_data:
    smq = smq_calculator.update_smq(data)
    print(f"Updated SMQ values: {smq}")
"""