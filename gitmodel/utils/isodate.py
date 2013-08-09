import re
import time
from datetime import datetime, time as dt_time
from dateutil import tz

ISO_DATE_RE = re.compile(r'^\d{4}-\d{1,2}-\d{1,2}$')
ISO_TIME_RE = re.compile(r'^(\d{1,2}:\d{2})(:(\d{2})(\.\d{1,5})?)?'
                         r'(Z|[+-]\d{1,2}:?\d{2}?)?$')
ISO_DATETIME_RE = re.compile(r'^(\d{4}-\d{1,2}-\d{1,2}[T\s]\d{1,2}:\d{2})(:'
                             r'(\d{2})(\.\d{1,6})?)?(Z|[+-]\d{1,2}:?'
                             r'\d{2}?)?$')
TZ_RE = re.compile(r'([+-])(\d{1,2}):?(\d{2})?')


class InvalidFormat(Exception):
    pass


class InvalidDate(Exception):
    pass


def parse_iso_date(value):
    #NEEDS-TEST
    if not ISO_DATE_RE.match(value):
        raise InvalidFormat('invalid ISO-8601 date: "{}"'.format(value))
    try:
        return datetime(*time.strptime(value, '%Y-%m-%d')[:3]).date()
    except ValueError:
        raise InvalidDate('invalid date: "{}"'.format(value))


def parse_tz(tzstr):
    #NEEDS-TEST
    # get tz data
    if tzstr is None:
        tzinfo = None
    elif tzstr == 'Z':
        tzinfo = tz.tzutc()
    else:
        # parse offset string
        s, h, m = TZ_RE.match(tzstr).groups()
        tzseconds = int(m and m or 0) * 60
        tzseconds += int(h) * 60 * 60
        if s == '-':
            tzseconds = tzseconds * -1
        tzinfo = tz.tzoffset(None, tzseconds)
    return tzinfo


def parse_iso_datetime(value):
    #NEEDS-TEST
    match = ISO_DATETIME_RE.match(value)
    if not match:
        raise InvalidFormat('invalid ISO-8601 date/time: "{}"'.format(value))

    # split out into datetime, secs, usecs, and tz
    dtstr = match.group(1)
    secs = match.group(3)
    usecs = match.group(4)
    tzstr = match.group(5)

    # replace the "T" if given
    dtstr = dtstr.replace('T', ' ')
    try:
        dt_args = time.strptime(dtstr, '%Y-%m-%d %H:%M')[:5]
    except ValueError:
        raise InvalidDate('invalid date: "{}"'.format(value))

    # append seconds, usecs, and tz
    dt_args += (int(secs) if secs else 0,)
    dt_args += (int(usecs.lstrip('.')) if usecs else 0,)
    dt_args += (parse_tz(tzstr),)

    try:
        return datetime(*dt_args)
    except ValueError:
        raise InvalidDate('invalid date: "{}"'.format(value))


def parse_iso_time(value):
    #NEEDS-TEST
    match = ISO_TIME_RE.match(value)
    if not match:
        raise InvalidFormat('invalid ISO-8601 time: "{}"'.format(value))

    # split out into time, secs, usecs, and tz
    tmstr = match.group(1)
    secs = match.group(3)
    usecs = match.group(4)
    tzstr = match.group(5)

    try:
        dt_args = time.strptime(tmstr, '%H:%M')[3:5]
    except ValueError:
        raise InvalidDate('invalid time: "{}"'.format(value))

    # append seconds, usecs, and tz
    dt_args += (int(secs) if secs else 0,)
    dt_args += (int(usecs) if usecs else 0,)
    dt_args += (parse_tz(tzstr),)

    try:
        return dt_time(*dt_args)
    except ValueError:
        raise InvalidDate('invalid date: "{}"'.format(value))
