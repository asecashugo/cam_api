import re

def test_match(plate_text):
    # print(f"Testing plate text: {plate_text}")
    return bool(re.fullmatch(r"\d{4}[A-Z]{3}", plate_text))

def extract_plate(plate_text):
    """
    Returns the plate text if it matches the format: 4 numbers followed by 3 letters (e.g., 1234ABC).
    Otherwise, returns an empty string.
    """
    plate_text = plate_text.replace(" ", "").upper()
    right_part = plate_text[-3:]
    left_part = plate_text[:-3]

    possible_left_parts = []
    possible_right_parts = []

    if len(left_part) < 4:
        return ""
    if len(left_part) > 4:
        possible_left_parts.append(left_part[-4:])
        possible_left_parts.append(left_part[:-4])
    else:
        possible_left_parts.append(left_part)
    
    if len(right_part) < 3:
        return ""
    if len(right_part) > 3:
        possible_right_parts.append(right_part[:3])
        possible_right_parts.append(right_part[3:])
    else:
        possible_right_parts.append(right_part)
    
    # combine all possible left and right parts
    for left in possible_left_parts:
        for right in possible_right_parts:
            plate_text = left + right
            plate_text = plate_text.replace(" ", "").upper()
            match = test_match(plate_text)
            if match:
                return plate_text
            else:
                print(f"🔴 {plate_text}")
            return ""
