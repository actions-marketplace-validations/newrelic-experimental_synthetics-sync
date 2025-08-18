import requests
import json
import re
import sys
import os
from actions_toolkit import core

GRAPHQL_API = 'https://api.newrelic.com/graphql'
GRAPHQL_KEY =  os.getenv('NEW_RELIC_API_KEY')
WORKSPACE = os.getenv('GITHUB_WORKSPACE')

def main():
    changedFiles = readAndParseFile("changed_monitors.json")
    deletedFiles = readAndParseFile("deleted_monitors.json")
    inputs = getInputs()

    # Handle new/updated files
    if len(changedFiles) > 0:
        for monitor in changedFiles:
            m = getMonitor(monitor['name']) # Find monitor in NR based on filename
            if (m != 'none'):
                updateMonitor(m, monitor['script']) # Update if it exists
            else:
                if any(input == "" for input in inputs.values()):
                    print("Missing inputs to create new monitor for file: " + monitor['name'] +  ". Please review inputs on last step if you wish to create new monitors. Skipping creation of newly committed files.")
                else:
                    if ('SCRIPT_API' in monitor['script']):
                        monitor['monitorType'] = 'SCRIPT_API'
                    elif ('SCRIPT_BROWSER' in monitor['script']):
                        monitor['monitorType'] = 'SCRIPT_BROWSER'
                    else:
                        monitor['monitorType'] = 'undefined'

                    if monitor['monitorType'] != 'undefined':
                        createMonitor(monitor, inputs) # Create new if it doesnt exist AND inputs are valid
                    else:
                        print("`monitorType` not defined in script: " + monitor['name'] + ". Monitor will not be created. Please add monitorType as a comment within your new script and recommit.")
    else:
        print('No modified or new monitors found in push')

    # Handle deleted files
    if len(deletedFiles) > 0:
        for monitor in deletedFiles:
            m = getMonitor(monitor['name']) # Find monitor in NR based on filename
            if (m != 'none'):
                deleteMonitor(m) # Delete monitor
            else:
                print('Monitor not found. Please validate that monitor was not deleted outside of this action.')
    else:
        print('No deleted scripts found in push')


def readAndParseFile(fileName):
    monitorList = None
    formatted = []

    try:
        with open(fileName, "r") as f:
            monitorList = json.load(f)
    except FileNotFoundError:
        print(f"File '{fileName}' not found, continuing.")
        return formatted
    except json.JSONDecodeError:
        print(f"Could not parse JSON from '{fileName}'")
        return formatted
    
    if not monitorList:
        print(f"No monitors read from file {fileName}. Exiting")
        sys.exit(1)

    pattern = r"[^/]*(?=\.[^/]*$)" #remove file path and .js extension
    if (len(monitorList) > 0):
        for mon in monitorList:
            script = WORKSPACE + '/' + mon
            fileReader = open(script, 'r')
            scriptContent = fileReader.read()
            formattedMonitor = re.search(pattern, mon)
            if formattedMonitor:
                formatted.append({'name': formattedMonitor.group(0), 'script': scriptContent })
    else:
        print('No monitors found in file. Exiting')
        sys.exit(1)

    return formatted

def getInputs():
    # Inputs for creation of new monitor upon new script commit [optional]
    acctId = core.get_input('accountId', required=False)
    privateLocString = core.get_input('privateLocations', required=False)
    publicLocString = core.get_input('publicLocations', required=False)
    interval = core.get_input('interval', required=False)
    status = core.get_input('status', required=False)

    # Convert strings to arrays if inputs are not empty
    if privateLocString != "":
        privateLocations = eval(privateLocString)
    else:
        privateLocations = ""

    if publicLocString != "":
        publicLocations = eval(publicLocString)
    else:
        publicLocations = ""

    if (type(publicLocations) is str and type(privateLocations) is str): # Both pub/private locations are default empty string
        locations = ""
    elif (type(publicLocations) is str and type(privateLocations) is not str): # Only private locations configured
        locations = {'private': privateLocations}
    elif (type(publicLocations) is not str and type(privateLocations) is str): # Only public locations configured
        locations = {'public': publicLocations}
    else: # both public and private configured
        locations = {'private': privateLocations, 'public': publicLocations}

    createInputs = {'account': acctId, 'locations': locations, 'interval': interval, 'status': status}

    return createInputs


def getMonitor(name):
    vars = {}
    gql = f"""
        {{
          actor {{
            entitySearch(query: "domain='SYNTH' and name='{name}'") {{
              results {{
                entities {{
                  ... on SyntheticMonitorEntityOutline {{
                    name
                    monitorId
                    monitorType
                    guid
                    account {{
                      id
                      name
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
    """
    h = {'Content-Type': 'application/json', 'API-Key': GRAPHQL_KEY}
    try:
        r = requests.post(GRAPHQL_API, headers=h, json={'query': gql, 'variables': vars})
        resp = r.json()
        if ('errors' not in resp):
            if (len(resp['data']['actor']['entitySearch']['results']['entities']) > 0):
                monitorResp = resp['data']['actor']['entitySearch']['results']['entities'][0]
                return monitorResp
            else:
                print("No matching id found for monitor: " + name + '. Creating new monitor...')
        else:
            print("Error retrieving monitor: " + name + '. Skipping...')
            print(resp['errors'])
    except requests.exceptions.RequestException as e:
        print("Error retrieving monitor: " + name + ' Skipping...')
        print(e)
        return 'none'

    return 'none'


def updateMonitor(monitor, script):
        vars = {"guid": monitor['guid'], "script": script}
        type = None

        if (monitor['monitorType'] == 'SCRIPT_BROWSER'):
            type = 'syntheticsUpdateScriptBrowserMonitor'
        elif (monitor['monitorType'] == 'SCRIPT_API'):
            type = 'syntheticsUpdateScriptApiMonitor'


        if (type != None):
            gql = f"""
                mutation ($guid: EntityGuid!, $script: String!) {{
                  {type}(guid: $guid, monitor: {{script: $script}}) {{
                    errors {{
                      description
                      type
                    }}
                    monitor {{
                      guid
                      name
                      status
                    }}
                  }}
                }}
            """
            h = {'Content-Type': 'application/json', 'API-Key': GRAPHQL_KEY}
            try:
                r = requests.post(GRAPHQL_API, headers=h, json={'query': gql, 'variables': vars})
                resp = r.json()
                if ('errors' in resp):
                    print("Error updating monitor: " + monitor['name'] + '. Skipping...')
                    print(resp['errors'])
                elif (len(resp['data'][type]['errors']) > 0):
                    print("Error updating monitor: " + monitor['name'] + '. Skipping...')
                    print(resp['data'][type]['errors'])
                else:
                    print("Successfully updated monitor: " + resp['data'][type]['monitor']['name'] + ". Monitor is currently " + resp['data'][type]['monitor']['status'])
            except requests.exceptions.RequestException as e:
                print("Error updating monitor: " + monitor['name'] + '. Skipping...')
                print(e)
        else:
            print('Type for monitor:' + monitor['name'] + 'is ' + monitor['monitorType'] + ". Scripted API or Browser are only accepted types. Skipping update...")


def createMonitor(monitor, inputs):
        type = None

        if (monitor['monitorType'] == 'SCRIPT_BROWSER'):
            type = 'syntheticsCreateScriptBrowserMonitor'
        elif (monitor['monitorType'] == 'SCRIPT_API'):
            type = 'syntheticsCreateScriptApiMonitor'

        if (type != None): # Monitor Type required
            vars = {"account": int(inputs['account']), "locations": inputs['locations'], "name": monitor['name'], "interval": inputs['interval'], "script": monitor['script'], "status": inputs['status']}
            gql = f"""
                mutation($account: Int!, $locations: SyntheticsScriptedMonitorLocationsInput!, $name: String!, $interval: SyntheticsMonitorPeriod!, $script: String!, $status: SyntheticsMonitorStatus! ) {{
                    {type}(accountId: $account, monitor: {{locations: $locations, name: $name, period: $interval, script: $script, status: $status}}) {{
                    errors {{
                        description
                        type
                    }}
                    monitor {{
                        guid
                        name
                        status
                    }}
                    }}
                }}
            """
            h = {'Content-Type': 'application/json', 'API-Key': GRAPHQL_KEY}
            try:
                r = requests.post(GRAPHQL_API, headers=h, json={'query': gql, 'variables': vars})
                resp = r.json()
                if ('errors' in resp):
                    print("Error creating monitor: " + monitor['name'] + '. Skipping...')
                    print(resp['errors'])
                elif (len(resp['data'][type]['errors']) > 0):
                    print("Error creating monitor: " + monitor['name'] + '. Skipping...')
                    print(resp['data'][type]['errors'])
                else:
                    print("Successfully created new monitor: " + resp['data'][type]['monitor']['name'] + ". Monitor is currently " + resp['data'][type]['monitor']['status'])
            except requests.exceptions.RequestException as e:
                print("Error creating monitor: " + monitor['name'] + '. Skipping...')
                print(e)
        else:
            print('Type for monitor:' + monitor['name'] + 'is ' + monitor['monitorType'] + ". Scripted API or Browser are only accepted types. Skipping create...")


def deleteMonitor(monitor):
    vars = {"guid": monitor['guid']}
    gql = """
    mutation($guid: EntityGuid!) {
        syntheticsDeleteMonitor(guid: $guid) {
            deletedGuid
        }
    }
    """
    h = {'Content-Type': 'application/json', 'API-Key': GRAPHQL_KEY}
    try:
        r = requests.post(GRAPHQL_API, headers=h, json={'query': gql, 'variables': vars})
        resp = r.json()
        print(resp)
        if ('errors' in resp):
            print("Error deleting monitor: " + monitor['name'] + '. Skipping...')
            print(resp['errors'])
        else:
            print("Successfully deleted monitor: " + monitor['name'] + " with guid: " + resp['data']['syntheticsDeleteMonitor']['deletedGuid'] + ".")
    except requests.exceptions.RequestException as e:
        print("Error deleting monitor: " + monitor['name'] + '. Skipping...')
        print(e)

if __name__ == '__main__':
    main()
