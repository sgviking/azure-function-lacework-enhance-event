import logging
import azure.functions as func
import requests
import json
import os
from laceworksdk import LaceworkClient


def main(req: func.HttpRequest) -> func.HttpResponse:

    def get_event(event_id, account, api_key, api_secret):
        logging.info('{0} tenant event {1} received'.format(account, event_id))
        logging.info('Creating Lacework client')

        lacework_client = LaceworkClient(
            api_key=api_key,
            api_secret=api_secret,
            account=account
        )
        
        event = lacework_client.events.get(event_id).get('data', [{}])[0]
        event = dict((k.lower(), v) for k,v in event.items())
        return event


    logging.info('Event alert received from Lacework')
    try:
        req_body = req.get_json()
    except ValueError:
        pass
    else:
        EVENT_ID = req_body.get('event_id')

    API_KEY = os.getenv("LW_API_KEY")
    API_SECRET = os.getenv("LW_API_SECRET")
    ACCOUNT = req_body.get("lacework_account")
    HEADERS = { 'Content-Type': 'application/json'}

    if not EVENT_ID:
        logging.info('Could not pull the event_id')
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass an event for a personalized response.",
             status_code=200
        )

    if EVENT_ID == '0':
        logging.info('Lacework test event received')
        return func.HttpResponse(body=json.dumps(req_body), headers=HEADERS)

    RESPONSE = get_event(EVENT_ID, ACCOUNT, API_KEY, API_SECRET)
    return func.HttpResponse(body=json.dumps(RESPONSE), headers=HEADERS)