#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys

from googleads import ad_manager

from dfp.client import get_client


logger = logging.getLogger(__name__)


def get_line_items_for_order(order_id):
  """
  Gets line items for an order.

  Args:
    order_id(str): the id of the DFP orderrd
  Returns:
    array of line item objects
  """

  dfp_client = get_client()
  line_item_service = dfp_client.GetService('LineItemService', version='v201811')

  statement = (ad_manager.StatementBuilder()
               .Where('orderId = :order_id')
               .WithBindVariable('order_id', order_id))

  # Retrieve a small amount of line items at a time, paging
  # through until all line items have been retrieved.
  line_items = []
  while True:
    response = line_item_service.getLineItemsByStatement(statement.ToStatement(
    ))
    if 'results' in response and len(response['results']):
      for line_item in response['results']:
        # Print out some information for each line item.
        print('Line item with ID "%d" and name "%s" was found.\n' %
              (line_item['id'], line_item['name']))
        line_items.append(line_item)
      statement.offset += statement.limit
    else:
      break

    return line_items

def main():
  if len(sys.argv) > 1:
       li = get_line_items_for_order(int(sys.argv[1]))
       if len(li) > 0:
           print(li[0])
  else:
      print("No Order Id")
  pass

if __name__ == '__main__':
  main()
