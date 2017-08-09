import os
import datetime
os.environ.update({
    #'BOKEH_DEV':'true',
    'BOKEH_MINIFIED':'false',
    'BOKEH_LOG_LEVEL':'debug',
    'BOKEH_PY_LOG_LEVEL':'debug',
    'BOKEH_PRETTY':'true',
})
from bokeh.layouts import column, row, widgetbox
from bokeh.models import ColumnDataSource, HoverTool, Button, CustomJS, Range1d
from bokeh.models.widgets import DateRangeSlider
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
        ('line_voltage', '@line_voltage{%05.1f v}'),
        ('frequency', '@frequency{%04.1f Hz}'),
    ],
    formatters={
        'date':'datetime',
        'line_voltage':'printf',
        'frequency':'printf',
    },
    mode='vline',
)

now = timezone.now('UTC').replace(tzinfo=None)
DT_RANGE = (now - datetime.timedelta(days=7), now)

p1 = figure(
    x_axis_type='datetime', plot_width=400, plot_height=350,
    toolbar_location='right', x_range=Range1d(*DT_RANGE),
    sizing_mode='stretch_both',
)
p1.add_tools(hover)
r = p1.line('date', 'line_voltage', source=data_src)

p1.title.text = "Line Voltage"
p1.legend.location = "top_left"
p1.xaxis.axis_label = 'Date'
p1.yaxis.axis_label = 'Voltage'

p2 = figure(
    x_axis_type='datetime', plot_width=400, plot_height=350,
    x_range=p1.x_range, toolbar_location='right',
    sizing_mode='stretch_both',
)
p2.add_tools(hover)
r2 = p2.line('date', 'frequency', source=data_src)
p2.title.text = 'Line Frequency'
p2.legend.location = 'top_left'
p2.xaxis.axis_label = 'Date'
p2.yaxis.axis_label = 'Frequency'

source_js_callback = CustomJS(args=dict(source=data_src), code="""
    var now = new Date(),
        utcOffset = now.getTimezoneOffset() * 60 * 1000;
    for (i=0; i<source.data.date.length; i++){
        if (!source.data.offset_applied[i]){
            source.data.date[i] = source.data.date[i] - utcOffset;
        }
    }
    console.log(source.data);

""")
data_src.js_on_change('stream', source_js_callback)

btn = Button(label='Update')
btn.on_click(update_data_src)



date_widget = DateRangeSlider(
    title='Date Range',
    value=DT_RANGE,
    start=DT_RANGE[0],
    end=DT_RANGE[1],
)

def source_py_callback(attr, old, new):
    if not len(data_src.data['date']):
        return
    min_dt = min(data_src.data['date'])
    max_dt = max(data_src.data['date'])
    date_widget.start = min_dt
    date_widget.end = max_dt
    date_widget.value = (min_dt, max_dt)


data_src.on_change('data', source_py_callback)

# date_widget_js_callback = CustomJS(code="""
#     var d0 = new Date(cb_obj.value[0]),
#         d1 = new Date(cb_obj.value[1]);
#     console.log(d0, d1);
# """)
# date_widget.js_on_change('value', date_widget_js_callback)

def date_widget_py_callback(attr, old, new):
    global DT_RANGE
    _dt_range = []
    for dt in new:
        if not isinstance(dt, datetime.datetime):
            dt = datetime.datetime.utcfromtimestamp(dt/1000.)
        dt = dt.replace(tzinfo=None)
        _dt_range.append(dt)
    DT_RANGE = tuple(_dt_range)
    p1.x_range.start = _dt_range[0]
    p1.x_range.end = _dt_range[1]

date_widget.on_change('value', date_widget_py_callback)


wid_box = widgetbox(btn, date_widget, sizing_mode='scale_width')

pl_row = row(p1, p2, sizing_mode='stretch_both')

curdoc().add_root(column(pl_row, wid_box, sizing_mode='stretch_both'))
