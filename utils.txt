def clamp(value):
    if value > 180:
        return int(180)
    elif value < 0:
        return int(0)
    else:
        return int(value)


def map_range(value):
    input_min = 0
    input_max = 180
    output_min = 290
    output_max = 460

    # Ánh xạ giá trị từ phạm vi đầu vào thành phạm vi đầu ra
    output_value = ((value - input_min) / (input_max - input_min)) * (output_max - output_min) + output_min

    return int(output_value)


