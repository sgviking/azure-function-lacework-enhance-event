import logging
import azure.functions as func
import requests
import json
import os
from laceworksdk import LaceworkClient


def main(req: func.HttpRequest) -> func.HttpResponse:
    def get_csp_info(alert):
        entityMap = alert.get('entitymap')
        # Azure alerts have information in entityMap->AzureIdentity
        if entityMap.get('AzureIdentity', False):
            alert['azure_principal'] = entityMap['AzureIdentity'][0].get('KEY', {}).get('principal_id')
            alert['azure_subscription_id'] = entityMap['AzureIdentity'][0].get('PROPS', {}).get('subscription_list', [])[0].get('subscription_id')
            alert['azure_tenant_id'] = entityMap['AzureIdentity'][0].get('PROPS', {}).get('subscription_list', [])[0].get('tenant_id')
            return alert

        # GCP alerts have information in entityMap->GcpIdentity and entityMap->Project
        if entityMap.get('GcpIdentity', False) and entityMap.get('Project', False):
            alert['gcp_principal_email'] = entityMap['GcpIdentity'][0].get('KEY', {}).get('principal_email')
            alert['gcp_organization_id'] = entityMap['Project'][0].get('KEY', {}).get('organization_id')
            alert['gcp_organization_name'] = entityMap['Project'][0].get('KEY', {}).get('organization_name')
            alert['gcp_project_id'] = entityMap['Project'][0].get('KEY', {}).get('project_id')
            return alert

        # AWS compliance alerts have information in entityMap->RecId
        if entityMap.get('RecId', False):
            alert['aws_account_id'] = entityMap['RecId'][0].get('PROPS', {}).get('account_id')
            alert['aws_account_alias'] = entityMap['RecId'][0].get('PROPS', {}).get('account_alias')
            return alert

        # AWS CloudTrail alerts have information in entityMap->CT_User
        if entityMap.get('CT_User', False):
            alert['aws_account_id'] = entityMap['CT_User'][0].get('KEY', {}).get('account')
            alert['aws_principal_id'] = entityMap['CT_User'][0].get('KEY', {}).get('principalId')
            alert['aws_username'] = entityMap['CT_User'][0].get('KEY', {}).get('username')
            return alert

        # AWS host alerts have information in entityMap->Machine
        if entityMap.get('Machine', False):
            alert['aws_account_id'] = entityMap['Machine'][0].get('PROPS', {}).get('tags', {}).get('Account')
            alert['ic:site_id'] = entityMap['Machine'][0].get('PROPS', {}).get('tags', {}).get('ic:siteid')
            alert['ic:vcs_account_id'] = entityMap['Machine'][0].get('PROPS', {}).get('tags', {}).get('ic:vcs-account-id')
            alert['site_id'] = entityMap['Machine'][0].get('PROPS', {}).get('tags', {}).get('siteid')
            alert['vcs_account_id'] = entityMap['Machine'][0].get('PROPS', {}).get('tags', {}).get('vcs-account-id')
            return alert

        return alert

    def get_alert(alert_id, api_key, api_secret, account, subaccount=None):
        logging.info('{0} tenant alert {1} received'.format(account, alert_id))
        logging.info('Creating Lacework client')

        lacework_client = LaceworkClient(
            api_key=api_key,
            api_secret=api_secret,
            account=account,
            subaccount=subaccount
        )

        alert = lacework_client.alerts.get_details(alert_id, "Details").get('data', {})
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
    ALERT_LINK = "https://{0}.lacework.net/ui/investigation/monitor/AlertInbox/{1}/details?accountName={2}".format(ACCOUNT, ALERT_ID, SUBACCOUNT)

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
    RESPONSE = get_csp_info(RESPONSE)
    RESPONSE.update( (('lw_account', ACCOUNT), ('alert_url', ALERT_LINK) , ('lw_subaccount', SUBACCOUNT)) )

    return func.HttpResponse(body=json.dumps(RESPONSE), headers=HEADERS)
