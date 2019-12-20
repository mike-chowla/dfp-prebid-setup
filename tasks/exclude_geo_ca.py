#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys
import csv
import pprint
import re
import pdb
import argparse
import re
from builtins import input

from colorama import init

import settings
import dfp.create_orders
import dfp.get_line_items
import dfp.update_line_items
import dfp.create_custom_targeting
import dfp.get_custom_targeting

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

re_price = re.compile("(.+)_(\d+\.\d+)$")
re_ends_5 = re.compile("5$")

def convert_to_min_price(order_name):
  """
  Call all necessary DFP task to convert average price line items to min price
  """

  # Get the order.
  order = dfp.get_orders.get_order_by_name(order_name)

  if order == None:
    raise BadSettingException('Order Not Found {0}'.format(order_name))

  line_items = dfp.get_line_items.get_line_items_for_order(order.id)

  updated_line_items = []
  for li in line_items:
      if li['isArchived']:
          continue

      updated = False

      if 'targeting' in li:
          if 'geoTargeting' in li['targeting']:

              if li['targeting']['geoTargeting'] == None:
                  li['targeting']['geoTargeting'] = {
                    'excludedLocations': []
                  }

              if 'excludedLocations' in li['targeting']['geoTargeting']:
                  if len(li['targeting']['geoTargeting']['excludedLocations']) == 0:
                      ex_el = {
                      'id': 21137,
                      'type': 'STATE',
                      'canonicalParentId': 2840,
                      'displayName': 'California'
                      }

                      li['targeting']['geoTargeting']['excludedLocations'] = ex_el
                      updated = True
                      updated_line_items.append(li)

      if not updated:
          print("Error: Could not update line item {0}".format(li.name))

  line_item_ids = dfp.update_line_items.update_line_items(updated_line_items)

  logger.info("{0} line items were updated".format(len(line_item_ids)))
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

  parser = argparse.ArgumentParser()
  parser.add_argument('--order_name', help='Order Name to Use -- overrides settings.py value')
  parser.add_argument('--key_name', help='Targeting Key to Remove  -- overrides settings.py value')
  parser.add_argument('--no_confirm', dest='no_confirm', action='store_true')
  parser.set_defaults(no_confirm=False)
  args = parser.parse_args()

  order_name = None
  if args.order_name:
    order_name = args.order_name
  else:
    order_name = getattr(settings, 'DFP_ORDER_NAME', None)
    if order_name is None:
        raise MissingSettingException('DFP_ORDER_NAME')

  logger.info(
    u"""

    Going to convert an existing order to min price
      {name_start_format}Order{format_end}: {value_start_format}{order_name}{format_end}

""".format(
  order_name=order_name,
  name_start_format=color.BOLD,
  format_end=color.END,
  value_start_format=color.BLUE,
))

  if not args.no_confirm:
    ok = input('Is this correct? (y/n)\n')

    if ok != 'y':
      logger.info('Exiting.')
      return

  convert_to_min_price(
    order_name,
  )


if __name__ == '__main__':
  main()
