import os
import cgi
import cgitb
import pprint
import dfp.get_orders
import cgi_settings
import yaml
import json
from oauth2client.client import credentials_from_code

cgitb.enable()

form = cgi.FieldStorage()

cgi_settings.DFP_CGI_FIELDS["DFP_NETWORK_CODE"] = form["DFP_NETWORK_CODE"].value

with open(os.environ["DFP_YAML_TEMPLATE"], 'r') as stream:
  gl_settings = yaml.safe_load(stream);
  cgi_settings.DFP_CGI_FIELDS["DFP_OAUTH_CLIENT_ID"] = gl_settings['ad_manager']['client_id']
  cgi_settings.DFP_CGI_FIELDS["DFP_OAUTH_CLIENT_SECRET"] = gl_settings['ad_manager']['client_secret']
  cgi_settings.DFP_CGI_FIELDS["DFP_OAUTH_APPLICATION_NAME"] = gl_settings['ad_manager']['application_name']

  creds = credentials_from_code(client_id=gl_settings['ad_manager']['client_id'], 
                                client_secret=gl_settings['ad_manager']['client_secret'], 
                                code=form["DFP_OAUTH_AUTH_CODE"].value,
                                scope="https://www.googleapis.com/auth/dfp",
                                redirect_uri='http://mike.pubmatic.com/OpenWrapLineItems/oauthTokenManager.html')

cgi_settings.DFP_CGI_FIELDS["DFP_OAUTH_REFRESH_TOKEN"] = creds.refresh_token


task = form["task"].value

if task == "get_orders":
    dfp.get_orders.main()
else:
    print("Error: Unkown Task {0}".format(task))