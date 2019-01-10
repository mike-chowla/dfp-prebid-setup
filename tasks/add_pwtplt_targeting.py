#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys
import csv
import pprint
import re
import pdb
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

from tasks.dfp_utils import (
  DFPValueIdGetter,
  get_or_create_dfp_targeting_key
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


def add_pwtplt_targeting(order_name):
  """
  Call all necessary DFP task to add pwtplt targeting
  """

  # Get the order.
  order = dfp.get_orders.get_order_by_name(order_name)

  if order == None:
    raise BadSettingException('Order Not Found {0}'.format(order_name))

  pwtplt_key_id = get_or_create_dfp_targeting_key('pwtplt', key_type='PREDEFINED') # platform
  PltValueGetter = DFPValueIdGetter('pwtplt')
  display_value_id = PltValueGetter.get_value_id("display")

  platform_criteria = {
      'xsi_type': 'CustomCriteria',
      'keyId': pwtplt_key_id,
      'valueIds': [display_value_id],
      'operator': 'IS'
  }

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
                          if crit['keyId'] != pwtplt_key_id:
                              top_set.append(crit)
                      top_set.append(platform_criteria)

                      # We need to update the criteria in the acutal line item object
                      li['targeting']['customTargeting']['children'][0]['children'] = top_set
                      updated_line_items.append(li)
                      updated = True

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

  order_name = getattr(settings, 'DFP_ORDER_NAME', None)
  if order_name is None:
    raise MissingSettingException('DFP_ORDER_NAME')

  logger.info(
    u"""

    Going to add pwtplt=display targeting to existing order
      {name_start_format}Order{format_end}: {value_start_format}{order_name}{format_end}

""".format(
  order_name=order_name,
  name_start_format=color.BOLD,
  format_end=color.END,
  value_start_format=color.BLUE,
))

  ok = input('Is this correct? (y/n)\n')

  if ok != 'y':
    logger.info('Exiting.')
    return

  add_pwtplt_targeting(
    order_name,
  )


if __name__ == '__main__':
  main()
