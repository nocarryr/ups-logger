import datetime
import pytz

def test_log_linev(apcaccess_gen):
    from upslogger.apcdata import get_apc_linev
    from upslogger.logger import log_linev, LOG_FILENAME
    from upslogger import timezone
    from upslogger.timezone import DT_FMT
    timezone.TZ = apcaccess_gen.tz

    LOG_FIELDS = ['DATE', 'LINEV', 'LINEFREQ']

    lines_expected = [
        '\t'.join(['#fields:'] + LOG_FIELDS)
    ]

    def append_gendata():
        d = {getattr(apcaccess_gen, attr) for attr in LOG_FIELDS}
        line = '\t'.join([
            apcaccess_gen.DATE.strftime(DT_FMT),
            '{:5.1f}'.format(apcaccess_gen.LINEV),
            '{:4.1f}'.format(apcaccess_gen.LINEFREQ),
        ])
        lines_expected.append(line)


    apcaccess_gen.LINEV = 110.0
    apcaccess_gen.LINEFREQ = 59.0
    apcaccess_gen.DATE = apcaccess_gen.DATE.replace(minute=10, second=0)
    while apcaccess_gen.LINEV <= 120.0:
        append_gendata()
        data = get_apc_linev()
        log_linev(data)
        apcaccess_gen.LINEV += .1
        if apcaccess_gen.LINEFREQ >= 61:
            apcaccess_gen.LINEFREQ = 59.0
        else:
            apcaccess_gen.LINEFREQ += .1
        apcaccess_gen.DATE += datetime.timedelta(seconds=1)

    with open(LOG_FILENAME, 'r') as f:
        s = f.read()
    for gen_line, log_line in zip(lines_expected, s.splitlines()):
        assert gen_line == log_line

def test_log_parser(existing_logfile):
    from upslogger.logger import parse_logfile

    dt = datetime.datetime(2017, 8, 3, 14, 10, 0)
    dt = pytz.timezone('US/Central').localize(dt)

    linev = 110.0
    linefreq = 59.0

    parsed = parse_logfile(str(existing_logfile))

    for d in parsed:
        assert d['DATE'].value == dt
        assert round(d['LINEV'].value, 1) == round(linev, 1)
        assert round(d['LINEFREQ'].value, 1) == round(linefreq, 1)

        dt += datetime.timedelta(seconds=1)
        linev += .1
        if linefreq >= 61:
            linefreq = 59.0
        else:
            linefreq += .1
