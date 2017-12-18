"""Commute Traffic to SNS."""

import logging
import json
import boto3

SNS = boto3.client('sns')


def handler(event, context):
    """Lambda handler."""
    # pylint: disable=unused-argument
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    logger.info(event)

    # vars
    topic_arn = event['topic_arn']
    message = {"foo": "bar"}

    logger.info(message)
    response = SNS.publish(
        TopicArn=topic_arn,
        Message=json.dumps({'default': json.dumps(message)}),
        MessageStructure='json'
    )
    return {'statusCode': 200,
            'body': json.dumps(response),
            'headers': {'Content-Type': 'application/json'}}
