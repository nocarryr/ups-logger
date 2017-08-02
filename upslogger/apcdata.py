#! /usr/bin/env python

import os
import io
import time
import datetime
import subprocess
import shlex
import argparse
import json

from upslogger.logger import LOG_FILENAME, LOG_FIELDS, log_linev, parse_logfile
from upslogger import timezone
from upslogger.fields import Field, DateFieldBase
from upslogger.plotlyutils import PlotlyRateLimitError, to_plotly

APC_HOSTNAME = 'localhost'
APC_HOSTPORT = 3551

def get_apc_status(hostname=None, port=None):
    if hostname is None:
        hostname = APC_HOSTNAME
    if port is None:
        port = APC_HOSTPORT
    cmd_str = 'apcaccess status {}:{}'.format(hostname, port)
    s = subprocess.check_output(shlex.split(cmd_str))
    d = {}
    for line in s.splitlines():
        if ':' in line:
            key = line.split(':')[0].strip(' ')
            val = ':'.join(line.split(':')[1:]).strip(' ')
            field = Field.from_string(val, key)
            d[key] = field
    return d

def get_apc_linev(hostname=None, port=None):
    d = get_apc_status(hostname, port)
    r = {}
    for name in LOG_FIELDS:
        if name not in d:
            return None
    dt = d.get('DATE')
    if dt is None or dt.value is None:
        dt = timezone.now('local')
        d['DATE'] = DateFieldBase(dt, 'DATE')
    return d


def prepare_js_data(filename=None, **kwargs):
    dt_type = kwargs.pop('dt_dype', 'posix_ts')
    x_data_key = kwargs.pop('x_data_key', 'time')
    y_data_key = kwargs.pop('y_data_key', 'y')

    parsed = parse_logfile(filename)
    js_data = {}
    for d in parsed:
        dt_field = d['DATE']
        if dt_type == 'posix_ts':
            x = timezone.to_timestamp(dt_field.value)
        elif dt_type == 'js_ts':
            x = timezone.to_timestamp(dt_field.value) * 1000
        elif dt_type == 'isostr':
            x = str(dt_field)
        else:
            x = str(dt_field)
        for field in d.values():
            if field.name == 'DATE':
                continue
            if field.value is None:
                continue
            if field.name not in js_data:
                js_data[field.name] = {
                    'label':field.name.title(),
                    'values':[],
                }
            js_data[field.name]['values'].append({
                x_data_key:x,
                y_data_key:field.value
            })
    return js_data

def to_aws_epochjs(bucket_name, key_name, filename=None):
    import boto3
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    obj = bucket.Object(key_name)

    js_data = prepare_js_data(filename)
    js_data = list(js_data.values())

    s = json.dumps(js_data)
    fh = io.BytesIO(bytes(s))
    obj.upload_fileobj(
        fh,
        ExtraArgs={
            'ContentType':'application/json',
            'ACL':'public-read',
        }
    )
    fh.close()


def log_linev_interval(parsed_args):
    log_seconds = int(parsed_args.time_interval) * 60
    pl_enable = parsed_args.plotly
    pl_seconds = parsed_args.plotly_interval * 60
    epochjs_enable = parsed_args.epochjs
    epochjs_seconds = parsed_args.epochjs_interval
    print('Logging every {} minutes.  Press CTRL-C to quit'.format(parsed_args.time_interval))
    wait_interval = 1
    now = time.time()
    next_log_ts = now
    next_plot_ts = now
    next_epochjs_ts = now
    while True:
        try:
            now = time.time()
            if now >= next_log_ts:
                data = get_apc_linev()
                log_linev(data, parsed_args.logfile)
                next_log_ts += log_seconds
            if pl_enable and now >= next_plot_ts:
                try:
                    to_plotly(parsed_args.logfile)
                except PlotlyRateLimitError:
                    print('{}: plotly rate limit'.format(datetime.datetime.now()))
                next_plot_ts += pl_seconds
            if epochjs_enable and now >= next_epochjs_ts:
                to_aws_epochjs(parsed_args.aws_bucket, parsed_args.aws_keyname, parsed_args.logfile)
            time.sleep(wait_interval)
        except KeyboardInterrupt:
            break

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('-f', '--logfile', dest='logfile')
    p.add_argument('-t', '--time-interval', dest='time_interval',
                   help='Log every "t" minutes')
    p.add_argument('--plotly', dest='plotly', action='store_true')
    p.add_argument('--plotly-interval', dest='plotly_interval', type=int, default=30,
                   help='Update plotly every "t" minutes')
    p.add_argument('--epochjs', dest='epochjs', action='store_true',
                   help='Upload epochjs data to aws')
    p.add_argument('--epochjs-interval', dest='epochjs_interval', type=int, default=10)
    p.add_argument('--aws-bucket', dest='aws_bucket')
    p.add_argument('--aws-keyname', dest='aws_keyname')
    args = p.parse_args()
    if args.epochjs:
        if not args.aws_bucket or not args.aws_keyname:
            raise Exception('aws-bucket and aws-keyname parameters required')
    if args.plotly and not args.time_interval:
        to_plotly(args.logfile)
    if args.epochjs and not args.time_interval:
        to_aws_epochjs(args.aws_bucket, args.aws_keyname, args.logfile)
    if args.time_interval:
        log_linev_interval(args)
    elif args.logfile:
        log_linev(args.logfile)
    elif not args.plotly and not args.epochjs:
        d = get_apc_linev()
        print(d.get('LINEV'))
