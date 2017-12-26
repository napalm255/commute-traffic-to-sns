#!/usr/bin/env python
"""Commute Traffic to SNS."""

from datetime import datetime
import logging
import os
import json
import requests
import boto3

SNS = boto3.client('sns')


def get_commute_duration(google_api_key, origin, destination, **kwargs):
    """Get commute duration."""
    # pylint: disable=unused-argument
    url = 'https://maps.googleapis.com/maps/api/distancematrix/json?'
    url_data = ('units=imperial&'
                'destinations=%s&'
                'origins=%s&'
                'departure_time=now&'
                'key=%s') % (destination, origin, google_api_key)
    query = requests.get(url + url_data)
    results = query.json()
    details = results['rows'][0]['elements'][0]
    data = {'timestamp': str(datetime.utcnow().strftime('%Y-%m-%d %H:%M:00')),
            'origin': str(origin),
            'destination': str(destination)}
    data.update(details)
    return data


def handler(event, context):
    """Lambda handler."""
    # pylint: disable=unused-argument
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.info(event)

    header = {'Content-Type': 'application/json'}
    try:
        if isinstance(event['body'], dict):
            logging.info('direct input')
            body = event['body']
        elif isinstance(event['body'], unicode):
            logging.info('api input')
            body = json.loads(event['body'])

        var = {'sns_topic_arn': os.environ['SNS_TOPIC_ARN'],
               'google_api_key': os.environ['GOOGLE_API_KEY'],
               'commute_routes': body['routes']}
        logging.info(var)
    except KeyError:
        return {'statusCode': 400,
                'body': {'status': 'ERROR',
                         'message': 'invalid input'},
                'headers': header}

    messages = list()
    for name, route in var['commute_routes'].iteritems():
        try:
            logging.info('route: %s', name)
            # commute duration
            logging.info('get commute duration')
            message = get_commute_duration(google_api_key=var['google_api_key'],
                                           origin=route['origin'],
                                           destination=route['destination'])
            logging.info(message)
            logging.info('recieved commute duration')
            # publish message
            logging.info('publish message')
            response = SNS.publish(
                TopicArn=var['sns_topic_arn'],
                Message=json.dumps({'default': json.dumps(message)}),
                MessageStructure='json'
            )
            logging.info('published message')
            # log message details
            messages.append({'statusCode': 200,
                             'body': {'status': 'OK',
                                      'response': response,
                                      'message': message},
                             'headers': header})
        # pylint: disable=broad-except
        except Exception as ex:
            messages.append({'statusCode': 400,
                             'body': {'status': 'ERROR',
                                      'error': ex,
                                      'message': message},
                             'headers': header})
    logging.info(messages)
    return {'statusCode': 200,
            'body': json.dumps({'status': 'OK',
                                'messages': messages}),
            'headers': header}
