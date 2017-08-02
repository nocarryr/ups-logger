import os
import io

from upslogger.fields import Field

LOG_FILENAME = '~/.apclinev.log'
LOG_FIELDS = ['DATE', 'LINEV', 'LINEFREQ']

def log_linev(data, filename=None):
    if not filename:
        filename = LOG_FILENAME
    filename = os.path.expanduser(filename)
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            header = ['#fields:']
            header.extend(LOG_FIELDS)
            header = '\t'.join(header)
            f.write('{}\n'.format(header))
    s = '{}\n'.format('\t'.join([str(data[name]) for name in LOG_FIELDS]))
    with open(filename, 'a') as f:
        f.write(s)

def parse_logfile(filename=None):
    if not filename:
        filename = LOG_FILENAME
    filename = os.path.expanduser(filename)
    if not os.path.exists(filename):
        return None
    with open(filename, 'r') as f:
        s = f.read()
    fields = None
    l = []
    for line in s.splitlines():
        if fields is None:
            if line.startswith('#fields:'):
                fields = line.split('\t')[1:]
        else:
            vals = line.split('\t')
            d = {}
            for i, field_name in enumerate(fields):
                try:
                    val = vals[i]
                except IndexError:
                    val = '-'
                field = Field.from_string(val, field_name)
                d[field_name] = field
            l.append(d)
    if fields is None:
        fields = ['#fields:']
        fields.extend(LOG_FIELDS)
        lines = ['\t'.join(fields)]
        lines.extend(s.splitlines())
        with open(filename, 'w') as f:
            f.write('\n'.join(lines))
        return parse_logfile(filename)
    return l
