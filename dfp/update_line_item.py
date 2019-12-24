#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from googleads import ad_manager

from dfp.client import get_client



logger = logging.getLogger(__name__)

def update_line_item_rate(line_item_id, rate):

  dfp_client = get_client()
  line_item_service = dfp_client.GetService('LineItemService', version='v201911')

  # Create statement object to get line item.
  statement = (ad_manager.StatementBuilder(version='v201911')
               .Where(('id = :id '))
               .WithBindVariable('id', int(line_item_id)))

  # Get line items by statement.
  response = line_item_service.getLineItemsByStatement(
      statement.ToStatement())
  print(response)
  if 'results' in response and len(response['results']):
    # Update each local line item by changing its delivery rate type.
    updated_line_items = []
    for line_item in response['results']:
      if not line_item['isArchived']:
        line_item['costPerUnit']['microAmount'] = rate
        updated_line_items.append(line_item)

    # Update line items remotely.
    line_items = line_item_service.updateLineItems(updated_line_items)
    if line_items:
      for line_item in line_items:
        print('Line item with id "%s", belonging to order id "%s", named '
              '"%s", and rate "%s" was updated.'
              % (line_item['id'], line_item['orderId'], line_item['name'],
                  line_item['costPerUnit']['microAmount']))
    else:
      print('No line items were updated.')
  else:
    print('No line items found to update.')

def main():
    print("update line items")

if __name__ == '__main__':
  main()

