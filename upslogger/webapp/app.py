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
    key_map = {'LINEV':'line_voltage', 'LINEFREQ':'frequency'}
    parsed = parse_logfile()
    data = {}
    for d in parsed:
        x = timezone.as_timezone(d['DATE'].value, 'UTC')
        ts = timezone.to_timestamp(x)
        x = x.replace(tzinfo=None)
        if ts not in data:
            data[ts] = {'date':x}
        for parse_key, data_key in key_map.items():
            value = d.get(parse_key)
            if value is not None:
                value = value.value
            data[ts][data_key] = value
    return data

data_src = ColumnDataSource(
    data={
        'date':[],
        'line_voltage':[],
        'frequency':[],
        'offset_applied':[],
        'timestamp':[],
    },
)

def update_data_src(*args):
    data = get_data()
    result = {'timestamp':[]}
    timestamps = set(data.keys())
    timestamps -= set(data_src.data['timestamp'])
    for ts in sorted(timestamps):
        result['timestamp'].append(ts)
        for data_key, value in data[ts].items():
            if data_key not in result:
                result[data_key] = []
            result[data_key].append(value)
    if not len(result['timestamp']):
        return
    result['offset_applied'] = [False] * len(result['timestamp'])
    data_src.stream(result)

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
