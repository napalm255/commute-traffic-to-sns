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
    data = {'timestamp': str(datetime.utcnow().isoformat()),
            'origin': str(origin),
            'destination': str(destination)}
    data.update(details)
    return data


def handler(event, context):
    """Lambda handler."""
    # pylint: disable=unused-argument
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.info(event)

    header = {'Content-Type': 'application/json'}
    body = json.loads(event['body'])

    try:
        var = {'sns_topic_arn': os.environ['SNS_TOPIC_ARN'],
               'google_api_key': os.environ['GOOGLE_API_KEY'],
               'origin': body['origin'],
               'destination': body['destination']}
        logging.info(var)
    except KeyError:
        return {'statusCode': 400,
                'body': {'status': 'ERROR',
                         'message': 'invalid input. required fields: %s' % var.keys()},
                'headers': header}

    message = get_commute_duration(**var)
    logger.info(message)

    try:
        response = SNS.publish(
            TopicArn=var['sns_topic_arn'],
            Message=json.dumps({'default': json.dumps(message)}),
            MessageStructure='json'
        )
    except KeyError:
        return {'statusCode': 400,
                'body': {'status': 'ERROR',
                         'message': 'invalid input. required fields: %s' % var.keys()},
                'headers': header}

    return {'statusCode': 200,
            'body': json.dumps({'status': 'OK',
                                'message': response}),
            'headers': header}
