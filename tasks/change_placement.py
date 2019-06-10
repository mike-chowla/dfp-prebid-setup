#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys
import csv
import pprint
import re
import argparse
from builtins import input

from colorama import init

import settings
import dfp.get_orders
import dfp.get_line_items
import dfp.get_placements
import dfp.get_root_ad_unit_id
import dfp.update_line_items

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


def change_placements(order_name, placements):
  """
  Call all necessary DFP task to change placements on an order
  """

  # Get the order.
  order = dfp.get_orders.get_order_by_name(order_name)

  if order == None:
    raise BadSettingException('Order Not Found {0}'.format(order_name))

  # Get the placement IDs.
  placement_ids = None
  ad_unit_ids = None
  if len(placements) > 0:
      placement_ids = dfp.get_placements.get_placement_ids_by_name(placements)
  else:
      # Run of network
      root_id = dfp.get_root_ad_unit_id.get_root_ad_unit_id()
      ad_unit_ids = [ root_id ]    
    
  line_items = dfp.get_line_items.get_line_items_for_order(order.id)

  updated_line_items = []
  pp = pprint.PrettyPrinter(indent=4)

  for li in line_items:
      updated = False
        
      if li.isArchived:
            continue
      
      if 'targeting' in li:
          if 'inventoryTargeting' in li['targeting']:
              li['targeting']['inventoryTargeting']['targetedAdUnits'] = []
              li['targeting']['inventoryTargeting']['excludedAdUnits'] = []
              li['targeting']['inventoryTargeting']['targetedPlacementIds'] = placement_ids
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
  parser.add_argument('--placement', help='Placement-- overrides settings.py value')
  parser.add_argument('--no_confirm', dest='no_confirm', action='store_true')
  parser.set_defaults(no_confirm=False)
  args = parser.parse_args()

  order_name = getattr(settings, 'DFP_ORDER_NAME', None)
  if order_name is None:
    raise MissingSettingException('DFP_ORDER_NAME')

  num_placements = 0
  placements = getattr(settings, 'DFP_TARGETED_PLACEMENT_NAMES', None)
  if placements is None:
    placements = []

  # if no placements are specified, we wil do run of network which is
  #   effectively one placement
  num_placements = len(placements)
  if num_placements == 0:
      num_placements = 1
    
  logger.info(
    u"""

    Going to change placement
      {name_start_format}Order{format_end}: {value_start_format}{order_name}{format_end}
      {name_start_format}Placements{format_end}: {value_start_format}{placements}{format_end}

  """.format(
    order_name=order_name,
    placements=placements,
    name_start_format=color.BOLD,
    format_end=color.END,
    value_start_format=color.BLUE,
  ))

  ok = input('Is this correct? (y/n)\n')

  if ok != 'y':
    logger.info('Exiting.')
    return

  change_placements(
    order_name,
    placements
  )

if __name__ == '__main__':
  main()
