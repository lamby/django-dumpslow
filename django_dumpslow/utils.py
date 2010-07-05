import re
import datetime

def parse_interval(val):
    match = re.match(r'^(\d+)([smhdwy])$', val)
    if not match:
        raise ValueError()

    unit = {
        's': 'seconds',
        'm': 'minutes',
        'h': 'hours',
        'd': 'days',
        'w': 'weeks',
    }[match.group(2)]

    return datetime.timedelta(**{unit: int(match.group(1))})
