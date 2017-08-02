import datetime
import pytz
import tzlocal

DT_FMT = '%Y-%m-%d %H:%M:%S %z'
UTC = utc = pytz.utc
TZ = None
POSIX_EPOCH = utc.localize(datetime.datetime(1970, 1, 1))

def get_local_timezone():
    global TZ
    if TZ is None:
        TZ = tzlocal.get_localzone()
    return TZ

def timezone(tz=None):
    if tz is None:
        tz = get_local_timezone()
    elif isinstance(tz, str):
        if tz == 'local':
            tz = get_local_timezone()
        else:
            tz = pytz.timezone(tz)
    return tz

def make_aware(dt, tz=None):
    tz = timezone(tz)
    return tz.localize(dt)

def as_timezone(dt, tz=None):
    tz = timezone(tz)
    if dt.tzinfo == tz:
        return dt
    return tz.normalize(dt)

def now(tz=None):
    dt = datetime.datetime.utcnow()
    dt = make_aware(dt, UTC)
    return as_timezone(dt, tz)

def parse_dt_str(dt_str, tz=None):
    if 'Z' in dt_str:
        dt_str = ' '.join(dt_str.split('Z'))
    dt_l = dt_str.split(' ')
    dt = datetime.datetime.strptime(' '.join(dt_l[:2]), ' '.join(DT_FMT.split(' ')[:2]))
    if dt_l[2].startswith('-') or dt_l[2].startswith('+'):
        offset_s = dt_l[2]
        off_h, off_m  = int(offset_s[1:3]), int(offset_s[3:])
        offset = datetime.timedelta(hours=off_h, minutes=off_m)
        if dt_l[2].startswith('-'):
            dt += offset
        else:
            dt -= offset
    dt = make_aware(dt, UTC)
    return as_timezone(dt, tz)

def to_timestamp(dt):
    dt = as_timezone(dt, UTC)
    td = dt - POSIX_EPOCH
    return td.total_seconds()
