import logging
import azure.functions as func
import requests
import json
import os
from laceworksdk import LaceworkClient


def main(req: func.HttpRequest) -> func.HttpResponse:

    def get_alert(alert_id, api_key, api_secret, account, subaccount=None):
        logging.info('{0} tenant alert {1} received'.format(account, alert_id))
        logging.info('Creating Lacework client')

        lacework_client = LaceworkClient(
            api_key=api_key,
            api_secret=api_secret,
            account=account,
            subaccount=subaccount
        )
        
        alert = lacework_client.alerts.get_details(alert_id, "Details").get('data', [{}])
        alert = dict((k.lower(), v) for k,v in alert.items())
        return alert

    logging.info('Alert received from Lacework')
    try:
        req_body = req.get_json()
    except ValueError:
        pass
    else:
        ALERT_ID = req_body.get('event_id')

    API_KEY = os.getenv("LW_API_KEY")
    API_SECRET = os.getenv("LW_API_SECRET")
    ACCOUNT = os.getenv("LW_ACCOUNT")
    SUBACCOUNT = req_body.get("lacework_account")
    HEADERS = { 'Content-Type': 'application/json'}

    if not API_KEY and not API_SECRET and not ACCOUNT:
        logging.info('Set the LW_ACCOUNT, LW_API_SECRET, and LW_API_KEY environmental variables.}')
        return func.HttpResponse(
             "This HTTP triggered function executed successfully.",
             status_code=200
        )

    if not ALERT_ID:
        logging.info('Could not pull the event_id')
        return func.HttpResponse(
             "This HTTP triggered function executed successfully.",
             status_code=200
        )

    if ALERT_ID == '0':
        logging.info('Lacework test alert received')
        return func.HttpResponse(body=json.dumps(req_body), headers=HEADERS)

    RESPONSE = get_alert(ALERT_ID, API_KEY, API_SECRET, ACCOUNT, SUBACCOUNT)
    return func.HttpResponse(body=json.dumps(RESPONSE), headers=HEADERS)
