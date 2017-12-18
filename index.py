"""Commute Traffic to SNS."""

from time import time
import logging
import requests
import json
import boto3

SNS = boto3.client('sns')


def get_duration(api_key, origin, destination):
    """Get duration."""
    url = 'https://maps.googleapis.com/maps/api/distancematrix/json?'
    url_data = ('units=imperial&'
                'destinations=%s&'
                'origins=%s&'
                'departure_time=now&'
                'key=%s') % (destination, origin, api_key)
    query = requests.get(url + url_data)
    results = query.json()
    details = results['rows'][0]['elements'][0]
    data = {'timestamp': str(time()),
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

    body = json.loads(event['body'])

    # vars
    api_key = body['google_api']
    topic_arn = body['topic_arn']
    origin = body['origin']
    destination = body['destination']

    message = get_duration(api_key, origin, destination)
    logger.info(message)

    response = SNS.publish(
        TopicArn=topic_arn,
        Message=json.dumps({'default': json.dumps(message)}),
        MessageStructure='json'
    )
    return {'statusCode': 200,
            'body': json.dumps(response),
            'headers': {'Content-Type': 'application/json'}}
