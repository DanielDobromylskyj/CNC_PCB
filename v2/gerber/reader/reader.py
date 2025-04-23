
def extract_line_data(data):
    output = {}

    started_reading_number = False
    current_value = ""
    current_name = ""

    for char in list(data):
        if char in "0123456789-.":
            started_reading_number = True
            current_value += char

        else:
            if started_reading_number:
                started_reading_number = False
                output[current_name] = current_value

                current_value = ""
                current_name = char
            else:
                current_name += char

    if current_name != "" and current_value != "":
        output[current_name] = current_value

    return output