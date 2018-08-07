#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys
import csv
import pprint
import re
from builtins import input

from colorama import init

import settings
import dfp.associate_line_items_and_creatives
import dfp.create_creatives
import dfp.create_orders
import dfp.get_advertisers
import dfp.get_users
import dfp.get_line_items
import dfp.remove_creatives_from_line_items
from dfp.exceptions import (
  BadSettingException,
  MissingSettingException
)

# Colorama for cross-platform support for colored logging.
# https://github.com/kmjennison/dfp-prebid-setup/issues/9
init()

# Configure logging.
if 'DISABLE_LOGGING' in os.environ and os.environ['DISABLE_LOGGING'] == 'true':
  logging.disable(logging.CRITICAL)
  logging.getLogger('googleads').setLevel(logging.CRITICAL)
  logging.getLogger('oauth2client').setLevel(logging.CRITICAL)
else:
  FORMAT = '%(message)s'
  logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=FORMAT)
  logging.getLogger('googleads').setLevel(logging.ERROR)
  logging.getLogger('oauth2client').setLevel(logging.ERROR)
  logging.getLogger(__name__).setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


def redo_creatives(user_email, advertiser_name, order_name,
    sizes, bidder_code, num_creatives):
  """
  Call all necessary DFP task to reset creatives on an order
  """

  # Get (or potentially create) the advertiser.
  advertiser_id = dfp.get_advertisers.get_advertiser_id_by_name(
    advertiser_name)

  # Get the order.
  order = dfp.get_orders.get_order_by_name(order_name)

  if order == None:
    raise BadSettingException('Order Not Found {0}'.format(order_name))

  line_items = dfp.get_line_items.get_line_items_for_order(order.id)

  # Remove Existing LICAs
  logger.info("-- Removing existing cretive associatings")
  for li in line_items:
      n = dfp.remove_creatives_from_line_items.remove_licas(li.id)
      logger.info("Line Item {0} - Removed {1} licas".format(li.name, n))

  # Create creatives.
  bidder_str = bidder_code
  if bidder_str == None:
      bidder_str = "All"
  elif isinstance(bidder_str, (list, tuple)):
      bidder_str = "_".join(bidder_str)

  creative_configs = dfp.create_creatives.create_duplicate_creative_configs(
      bidder_str, order_name, advertiser_id, num_creatives, creative_file="creative_snippet_openwrap.html")
  creative_ids = dfp.create_creatives.create_creatives(creative_configs)

  # Associate creatives with line items.
  line_item_ids = []
  for li in line_items:
      line_item_ids.append(li.id)
      
  dfp.associate_line_items_and_creatives.make_licas(line_item_ids,
    creative_ids, size_overrides=sizes)

  logger.info("""

    Done! Please review your order, line items, and creatives to
    make sure they are correct. Then, approve the order in DFP.

    Happy bidding!

  """)

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

def main():
  """
  Validate the settings and ask for confirmation from the user. Then,
  start all necessary DFP tasks.
  """

  user_email = getattr(settings, 'DFP_USER_EMAIL_ADDRESS', None)
  if user_email is None:
    raise MissingSettingException('DFP_USER_EMAIL_ADDRESS')

  advertiser_name = getattr(settings, 'DFP_ADVERTISER_NAME', None)
  if advertiser_name is None:
    raise MissingSettingException('DFP_ADVERTISER_NAME')

  order_name = getattr(settings, 'DFP_ORDER_NAME', None)
  if order_name is None:
    raise MissingSettingException('DFP_ORDER_NAME')

  sizes = getattr(settings, 'DFP_PLACEMENT_SIZES', None)
  if sizes is None:
    raise MissingSettingException('DFP_PLACEMENT_SIZES')
  elif len(sizes) < 1:
    raise BadSettingException('The setting "DFP_PLACEMENT_SIZES" '
      'must contain at least one size object.')

  currency_code = getattr(settings, 'DFP_CURRENCY_CODE', 'USD')

  # How many creatives to attach to each line item. We need at least one
  # creative per ad unit on a page. See:
  # https://github.com/kmjennison/dfp-prebid-setup/issues/13
  num_creatives = (
    getattr(settings, 'DFP_NUM_CREATIVES_PER_LINE_ITEM', None) or
    1
  )

  bidder_code = getattr(settings, 'PREBID_BIDDER_CODE', None)
  if bidder_code is not None and not isinstance(bidder_code, (list, tuple, str)):
    raise BadSettingException('PREBID_BIDDER_CODE')


  logger.info(
    u"""

    Going to redo creatives
      {name_start_format}Order{format_end}: {value_start_format}{order_name}{format_end}
      {name_start_format}Advertiser{format_end}: {value_start_format}{advertiser}{format_end}

    Creatives will have :
       {name_start_format}size{format_end} = {value_start_format}{sizes}{format_end}
""".format(
  order_name=order_name,
  advertiser=advertiser_name,
  user_email=user_email,
  sizes=sizes,
  name_start_format=color.BOLD,
  format_end=color.END,
  value_start_format=color.BLUE,
))

  ok = input('Is this correct? (y/n)\n')

  if ok != 'y':
    logger.info('Exiting.')
    return

  redo_creatives(
    user_email,
    advertiser_name,
    order_name,
    sizes,
    bidder_code,
    num_creatives,
  )


if __name__ == '__main__':
  main()
