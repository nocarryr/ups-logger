import datetime

def test_timezone(tz_override):
    from upslogger import timezone
    if timezone.TZ is not None:
        timezone.TZ = None

    tz = timezone.get_local_timezone()
    assert tz == tz_override['local'] == timezone.TZ

    now = datetime.datetime.utcnow()
    nowtz = timezone.now()
    nowutc = timezone.UTC.localize(now)

    # equality checks will likely fail by a few microseconds
    td = nowtz - nowutc
    assert 0 <= td.total_seconds() <= .5

    now = timezone.make_aware(now, 'UTC')
    assert now == nowutc

    nowtz1 = timezone.as_timezone(now, tz_override['local'])
    nowtz2 = timezone.as_timezone(now, tz_override['apc'])
    nowtz3 = timezone.as_timezone(now, 'local')

    assert now == nowtz1 == nowtz2 == nowtz3
    assert nowtz1.tzinfo.zone == tz_override['local'].zone
    assert nowtz2.tzinfo.zone == tz_override['apc'].zone
    assert nowtz3.tzinfo.zone == tz_override['local'].zone
    assert now.tzinfo.zone == 'UTC'

    ts_utc = timezone.to_timestamp(now)
    ts_tz1 = timezone.to_timestamp(nowtz1)
    ts_tz2 = timezone.to_timestamp(nowtz2)
    ts_tz3 = timezone.to_timestamp(nowtz3)

    epoch = timezone.UTC.localize(datetime.datetime(1970, 1, 1))
    td = now - epoch
    assert ts_utc == ts_tz1 == ts_tz2 == ts_tz3 == td.total_seconds()


    DT_FMT1 = '%Y-%m-%d %H:%M:%S %z'
    DT_FMT2 = '%Y-%m-%d %H:%M:%SZ%z'
    dt_dict = {
        'utc':now.replace(microsecond=0),
        'tz1':nowtz1.replace(microsecond=0),
        'tz2':nowtz2.replace(microsecond=0),
        'tz3':nowtz3.replace(microsecond=0),
    }

    for fmt in [DT_FMT1, DT_FMT2]:
        for key, dt in dt_dict.items():
            dt_str = dt.strftime(fmt)
            for tz in ['UTC', tz_override['local'].zone, tz_override['apc'].zone]:
                parsed_dt = timezone.parse_dt_str(dt_str, tz)
                assert parsed_dt == dt
                assert parsed_dt.tzinfo.zone == tz
