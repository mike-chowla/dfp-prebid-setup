#creative type constants
WEB="WEB"
WEB_SAFEFRAME="WEB_SAFEFRAME"
AMP="AMP"
IN_APP="IN_APP"
NATIVE="NATIVE"
VIDEO="VIDEO"
JW_PLAYER="JWPLAYER"

#video specific creative params
VIDEO_VAST_URL = 'https://ow.pubmatic.com/cache?uuid=%%PATTERN:pwtcid%%'
VIDEO_DURATION = 1000

#JW Player specific creative params
JWP_VAST_URL = 'https://vpb-cache.jwplayer.com/cache?uuid=%%PATTERN:vpb_pubmatic_key%%'
JWP_DURATION = 60000

# Maxmimum Line Items Per Order - GAM LIMIT
LINE_ITEMS_LIMIT = 450

# Number of Line Itmes to create a in a single call
#  GAM API can timeout if we try create too many
#  at once
LINE_ITEMS_BATCH_SIZE = 225
