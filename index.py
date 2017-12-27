#!/usr/bin/env python
"""Commute Traffic to SNS."""
# pylint: disable=broad-except

from __future__ import print_function
import sys
import os
import logging
import json
from datetime import datetime
import requests
import boto3


# logging configuration
logging.getLogger().setLevel(logging.DEBUG)

try:
    SNS = boto3.client('sns')
    SNS_TOPIC_ARN = os.environ['COMMUTE_SNS_TOPIC_ARN']
    logging.info('sns: initialized sns client')
except KeyError:
    logging.error('sns: missing topic arn')
except Exception as ex:
    logging.error('sns: could not connect to SNS. (%s)', ex)
    sys.exit()

try:
    SSM = boto3.client('ssm')

    PREFIX = '/commute/config'
    PARAMS = SSM.get_parameters_by_path(Path=PREFIX, Recursive=True,
                                        WithDecryption=True)
    logging.debug('ssm: parameters(%s)', PARAMS)

    CONFIG = dict()
    for param in PARAMS['Parameters']:
        key = param['Name'].replace('%s/' % PREFIX, '')
        CONFIG.update({key: param['Value']})
    logging.debug('ssm: config(%s)', CONFIG)

    logging.info('ssm: successfully gathered parameters')
except Exception as ex:
    logging.error('ssm: could not connect to SSM. (%s)', ex)
    sys.exit()

try:
    # ensure google api key
    assert 'google-api-key' in CONFIG
    assert CONFIG['google-api-key']
    # ensure routes
    assert 'routes' in CONFIG
    assert CONFIG['routes']
    # load routes json string
    CONFIG['routes'] = json.loads(CONFIG['routes'])
except ValueError as ex:
    logging.error('ssm: misconfigured routes. (%s)', ex)
    sys.exit()
except AssertionError as ex:
    logging.error('ssm: missing parameters. (%s)', ex)
    sys.exit()


def output(message, header=None, code=200):
    """Return output object."""
    logging.info('handler: output')
    if not header:
        header = {'Content-Type': 'application/json',
                  'Access-Control-Allow-Origin': '*'}
    logging.info('%s (%s)', message, header)
    return {'statusCode': code,
            'body': json.dumps({'status': 'OK',
                                'message': message}),
            'headers': header}


def get_commute_duration(origin, destination):
    """Get commute duration."""
    logging.info('get commute duration: start')
    url = 'https://maps.googleapis.com/maps/api/distancematrix/json?'
    url_data = ('units=imperial&'
                'destinations=%s&'
                'origins=%s&'
                'departure_time=now&'
                'key=%s') % (destination, origin, CONFIG['google-api-key'])
    query = requests.get(url + url_data)
    results = query.json()
    details = results['rows'][0]['elements'][0]
    data = {'timestamp': str(datetime.utcnow().strftime('%Y-%m-%d %H:%M:00')),
            'origin': str(origin),
            'destination': str(destination)}
    data.update(details)
    logging.info('get commute duration: end')
    return data


def handler(event, context):
    """Lambda handler."""
    # pylint: disable=unused-argument
    logging.info('event: %s', event)

    messages = list()
    for name, route in CONFIG['routes'].iteritems():
        try:
            logging.info('commute route name: %s', name)
            logging.debug('commute route: %s;%s', route['origin'], route['destination'])
            # commute duration
            message = get_commute_duration(origin=route['origin'],
                                           destination=route['destination'])
            logging.debug('commute duration data: %s', message)
            # publish message
            logging.info('publish message')
            response = SNS.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=json.dumps({'default': json.dumps(message)}),
                MessageStructure='json'
            )
            logging.debug('message response: %s', response)
            # log message details
            messages.append(output({'data': message, 'response': response}))
            logging.info('publish message succeeded')
        except Exception as ex:
            messages.append(output('publish message failed (%s)' % ex, code=400))

    logging.debug(messages)
    return output(messages)


if __name__ == '__main__':
    print(handler(None, None))
