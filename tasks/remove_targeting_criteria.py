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


def remove_targeting_criteria(order_name, key_name):
  """
  Call all necessary DFP task to remove targeting key from all line items in order
  """

  # Get the order.
  order = dfp.get_orders.get_order_by_name(order_name)

  if order == None:
    raise BadSettingException('Order Not Found {0}'.format(order_name))

  key_id = dfp.get_custom_targeting.get_key_id_by_name(key_name)
  if key_id == None:
    raise BadSettingException('Targeting Key Not Found {0}'.format(key_name))

  line_items = dfp.get_line_items.get_line_items_for_order(order.id)

  updated_line_items = []
  for li in line_items:
      if li['isArchived']:
          continue

      updated = False

      if 'targeting' in li:
          if 'customTargeting' in li['targeting']:
              cust_target = li['targeting']['customTargeting']

              if 'logicalOperator' in cust_target and 'children' in cust_target and len(cust_target['children']) > 0:
                  to_update = cust_target['children'][0]
                  if 'logicalOperator' in to_update and to_update['logicalOperator'] == 'AND' and 'children' in to_update:
                      top_set = []                     
                      for crit in to_update.children:
                          indexExchange_there = False    
                          ix_already_there = False   
                        
                          if crit['keyId'] == key_id:
                            # Skip this criteria and mark the line item as updated
                            updated = True
                          else:
                            top_set.append(crit)
                          

                      if updated:
                        # We need to update the criteria in the acutal line item object
                        li['targeting']['customTargeting']['children'][0]['children'] = top_set
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

  targeting_key_name = None
  if args.key_name:
    targeting_key_name = args.key_name
  else:
    targeting_key_name = getattr(settings, 'DFP_TARGETING_KEY_NAME', None)
    if targeting_key_name is None:
        raise MissingSettingException('DFP_TARGETING_KEY_NAME')

  logger.info(
    u"""

    Going to remove targeting key ffrom an existing order
      {name_start_format}Order{format_end}: {value_start_format}{order_name}{format_end}
      {name_start_format}Targeting Key Name{format_end}: {value_start_format}{targeting_key_name}{format_end}

""".format(
  order_name=order_name,
  targeting_key_name=targeting_key_name,
  name_start_format=color.BOLD,
  format_end=color.END,
  value_start_format=color.BLUE,
))

  if not args.no_confirm:
    ok = input('Is this correct? (y/n)\n')

    if ok != 'y':
      logger.info('Exiting.')
      return

  remove_targeting_criteria(
    order_name,
    targeting_key_name
  )


if __name__ == '__main__':
  main()
