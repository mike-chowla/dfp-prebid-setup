'''
    This script will attempt to open your webbrowser,
    perform OAuth 2 authentication and print your access token.

    It depends on two libraries: oauth2client and gflags.

    To install dependencies from PyPI:

    $ pip install python-gflags oauth2client

    Then run this script:

    $ python get_oauth2_token.py

    This is a combination of snippets from:
    https://developers.google.com/api-client-library/python/guide/aaa_oauth
'''

from oauth2client.client import OAuth2WebServerFlow
from oauth2client import tools
from oauth2client.file import Storage
import argparse

CLIENT_ID = '<INSERT CLIENT ID HERE>'
CLIENT_SECRET = '<INSERT CLIENT SECRET HERE>'

parser = argparse.ArgumentParser(parents=[tools.argparser])
flags = parser.parse_args()

flow = OAuth2WebServerFlow(client_id=CLIENT_ID,
                           client_secret=CLIENT_SECRET,
                           scope='https://www.googleapis.com/auth/dfp',
                           redirect_uri='http://example.com/auth_return',
                           access_type='offline',
                           prompt='consent')

storage = Storage('creds.data')

credentials = tools.run_flow(flow, storage, flags)

print ("access_token: %s" % credentials.access_token)
print ("refresh_token: %s" % credentials.refresh_token)
