
from googleads import ad_manager
from googleads import oauth2
from googleads.common import ZeepServiceProxy

import os
import settings
import cgi_settings

def client_from_cgi():
    import yaml
    from zeep.cache import SqliteCache

    oauth2_client = oauth2.GoogleRefreshTokenClient(
        cgi_settings.DFP_CGI_FIELDS["DFP_OAUTH_CLIENT_ID"], 
        cgi_settings.DFP_CGI_FIELDS["DFP_OAUTH_CLIENT_SECRET"], 
        cgi_settings.DFP_CGI_FIELDS["DFP_OAUTH_REFRESH_TOKEN"])
    
    ad_manager_client = ad_manager.AdManagerClient(
            oauth2_client, cgi_settings.DFP_CGI_FIELDS["DFP_OAUTH_APPLICATION_NAME"],
            network_code=int(cgi_settings.DFP_CGI_FIELDS["DFP_NETWORK_CODE"]),
            cache=ZeepServiceProxy.NO_CACHE)
    return ad_manager_client
    


def get_client():
  if cgi_settings.DFP_CGI_FIELDS and "DFP_OAUTH_REFRESH_TOKEN" in cgi_settings.DFP_CGI_FIELDS:
    return client_from_cgi()
  else:
    return ad_manager.AdManagerClient.LoadFromStorage(settings.GOOGLEADS_YAML_FILE)
