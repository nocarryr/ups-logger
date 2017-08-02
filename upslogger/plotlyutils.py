import plotly.plotly as py
import plotly.graph_objs as go
from plotly.exceptions import PlotlyRequestError

from upslogger.logger import parse_logfile

class PlotlyRateLimitError(Exception):
    def __init__(self, original_error):
        self.message = original_error.message
        self.status_code = original_error.status_code
        self.content = original_error.content
    def __str__(self):
        return self.message

def get_graph_objs(filename=None):
    parsed = parse_logfile(filename)
    if not parsed:
        return

    volt_x = []
    volt_y = []
    freq_x = []
    freq_y = []
    for d in parsed:
        x = d['DATE'].value
        vy = d.get('LINEV')
        fy = d.get('LINEFREQ')
        if vy is not None and vy.value is not None:
            volt_x.append(x)
            volt_y.append(vy.value)
        if fy is not None and fy.value is not None:
            freq_x.append(x)
            freq_y.append(fy.value)


    return dict(
        voltage=go.Scatter(x=volt_x, y=volt_y, name='Line Voltage'),
        frequency=go.Scatter(x=freq_x, y=freq_y, name='Line Frequency'),
    )

def to_plotly(filename=None):
    data = get_graph_objs(filename)
    fig = dict(data=[data['voltage'], data['frequency']])
    try:
        py.iplot(fig, filename='techarts-apc')
    except PlotlyRequestError as e:
        tb = str(e).lower()
        if 'api' in tb and 'limit' in tb:
            raise PlotlyRateLimitError(e)
        else:
            raise
