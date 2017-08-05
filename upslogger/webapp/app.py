import os
os.environ.update({
    #'BOKEH_DEV':'true',
    'BOKEH_MINIFIED':'false',
    'BOKEH_LOG_LEVEL':'debug',
    'BOKEH_PY_LOG_LEVEL':'debug',
    'BOKEH_PRETTY':'true',
})
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, HoverTool, Button, CustomJS
from bokeh.plotting import figure, curdoc

from upslogger.logger import parse_logfile
from upslogger import timezone


def get_data():
    parsed = parse_logfile()
    volt_x = []
    volt_y = []
    freq_x = []
    freq_y = []
    for d in parsed:
        x = timezone.as_timezone(d['DATE'].value, 'UTC')
        x = x.replace(tzinfo=None)
        vy = d.get('LINEV')
        fy = d.get('LINEFREQ')
        if vy is not None and vy.value is not None:
            volt_x.append(x)
            volt_y.append(vy.value)
        if fy is not None and fy.value is not None:
            freq_x.append(x)
            freq_y.append(fy.value)
    return {
        'Voltage':{'date':volt_x, 'line_voltage':volt_y},
        'Frequency':{'date':freq_x, 'frequency':freq_y},
    }

data_src = ColumnDataSource(data={'date':[], 'line_voltage':[], 'offset_applied':[]})
datetimes_sent = []

def update_data_src(*args):
    global datetimes_sent
    data = get_data()
    d = {'date':[], 'line_voltage':[]}
    for dt, y in zip(data['Voltage']['date'], data['Voltage']['line_voltage']):
        ts = timezone.to_timestamp(timezone.make_aware(dt, 'UTC'))
        if ts in datetimes_sent:
            continue
        d['date'].append(dt)
        d['line_voltage'].append(y)
        datetimes_sent.append(ts)
    d['offset_applied'] = [False] * len(d['date'])
    if not len(d['date']):
        return
    data_src.stream(d)

hover = HoverTool(
    tooltips=[
        ('date', '@date{%a %x %X}'),
        ('line_voltage', '@line_voltage{%05.1f Hz}'),
    ],
    formatters={
        'date':'datetime',
        'line_voltage':'printf',
    },
    mode='vline',
)

p = figure(width=800, height=350, x_axis_type="datetime", toolbar_location='right')
p.add_tools(hover)
r = p.line('date', 'line_voltage', source=data_src)

p.title.text = "Line Voltage"
p.legend.location = "top_left"
p.grid.grid_line_alpha=0
p.xaxis.axis_label = 'Date'
p.yaxis.axis_label = 'Voltage'

callback = CustomJS(args=dict(source=data_src), code="""
    var now = new Date(),
        utcOffset = now.getTimezoneOffset() * 60 * 1000;
    for (i=0; i<source.data.date.length; i++){
        if (!source.data.offset_applied[i]){
            source.data.date[i] = source.data.date[i] - utcOffset;
        }
    }
    console.log(source.data);

""")
data_src.js_on_change('stream', callback)

btn = Button(label='Update')
btn.on_click(update_data_src)

curdoc().add_root(column(btn, p))
