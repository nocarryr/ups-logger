import datetime
import pytz

def test_apcaccessgen(tz_override, apcaccess_gen, apcaccess_available):
    from upslogger import apcdata
    assert apcdata.APC_HOSTPORT == apcaccess_gen.hostport
    assert not apcdata.LOG_FILENAME.startswith('~')

    data = apcdata.get_apc_status()
    gen_data = apcaccess_gen.get_template_dict()
    for field in data.values():
        if field.name not in gen_data:
            continue
        assert field.value == gen_data[field.name]

def test_linev(tz_override, apcaccess_gen, apcaccess_available):
    from upslogger import apcdata

    apcaccess_gen.LINEV = 110.0
    while apcaccess_gen.LINEV <= 120.0:
        data = apcdata.get_apc_linev()
        assert round(data['LINEV'].value, 1) == round(apcaccess_gen.LINEV, 1)
        assert data['DATE'].value == apcaccess_gen.DATE
        assert data['DATE'].value.tzinfo.zone == tz_override['local'].zone

        apcaccess_gen.LINEV += .1
        apcaccess_gen.DATE += datetime.timedelta(minutes=1)
