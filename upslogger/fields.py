import datetime

from upslogger import timezone

DATE_FIELDS = ['DATE', 'STARTTIME', 'XONBATT', 'XOFFBATT', 'END APC']



class Field(object):
    name = None
    def __init__(self, value, name=None):
        self.value = value
        if name is not None:
            self.name = name
    @classmethod
    def iter_subclass(cls):
        for _cls in cls.__subclasses__():
            yield _cls
            for subcls in _cls.iter_subclass():
                yield subcls
    @classmethod
    def find_by_name(cls, name):
        if cls.name == name:
            return cls
        for _cls in cls.__subclasses__():
            matched = _cls.find_by_name(name)
            if matched:
                return matched
    @classmethod
    def from_string(cls, s, name=None):
        _cls = cls
        if name is not None:
            _cls = cls.find_by_name(name)
            if _cls is None:
                _cls = cls
        if s == '-':
            s = None
        else:
            s = _cls.parse_string(s)
        return _cls(s, name)
    @classmethod
    def parse_string(cls, s):
        return s
    def to_string(self):
        if self.value is None:
            return '-'
        return str(self.value)
    def __repr__(self):
        return '<{self.name}: {self}>'.format(self=self)
    def __str__(self):
        return self.to_string()

class DateFieldBase(Field):
    @classmethod
    def find_by_name(cls, name):
        if name in DATE_FIELDS:
            return cls
    @classmethod
    def parse_string(cls, s):
        try:
            dt = timezone.parse_dt_str(s, 'local')
        except ValueError:
            dt = None
        return dt
    def to_string(self):
        if self.value is None:
            return '-'
        return self.value.strftime(timezone.DT_FMT)

class LineV(Field):
    name = 'LINEV'
    @classmethod
    def parse_string(cls, s):
        return float(s.lower().strip('volts'))

class LineFreq(Field):
    name = 'LINEFREQ'
    @classmethod
    def parse_string(cls, s):
        return float(s.lower().strip('hz'))
