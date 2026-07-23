import numpy as np

def create_labels(number_of_windows, window_size, theft_intervals):
    y = np.zeros(number_of_windows, dtype=np.int8)
    for i in range(number_of_windows):
        window_start = i
        window_end = i + window_size - 1
        for theft_start, theft_end in theft_intervals:
            overlap = (window_start <= theft_end and window_end >= theft_start)
            if overlap:
                y[i] = 1
                break
    return y

# def create_labels(number_of_windows, window_size, theft_intervals, min_overlap=0.3):
#     y = np.zeros(number_of_windows, dtype=np.int8)
#     for i in range(number_of_windows):
#         window_start, window_end = i, i + window_size - 1
#         for theft_start, theft_end in theft_intervals:
#             overlap = min(window_end, theft_end) - max(window_start, theft_start) + 1
#             if overlap > 0 and overlap / window_size >= min_overlap:
#                 y[i] = 1
#                 break
#     return y