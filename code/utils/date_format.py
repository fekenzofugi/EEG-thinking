import datetime
from datetime import datetime


# Function to extract and format date from PRODUCT_ID
def format_date(product_id, start, end):
    date_string = product_id[start:end]
    date_object = datetime.strptime(date_string, "%Y%m%d").date()
    return date_object

# Function to find common dates for S1 and S2 and the highest date with its ID
def find_common_dates(data):
    s1_dates = set()
    s2_dates = set()
    highest_date = None
    highest_date_id = None

    # Separate S1 and S2 dates into sets and find the highest date
    for key, dt in data.items():
        if 'S1' in key:
            s1_dates.add(dt)
        elif 'S2' in key:
            s2_dates.add(dt)

        # Update the highest date and its ID
        if highest_date is None or dt > highest_date:
            highest_date = dt
            highest_date_id = key

    # Find the intersection of both sets
    common_dates = s1_dates.intersection(s2_dates)

    return common_dates, highest_date, highest_date_id