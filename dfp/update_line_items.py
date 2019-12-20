
from googleads import ad_manager

from dfp.client import get_client

def update_line_items(line_items):
  """
  Updates line items in DFP.

  Args:
    line_items (arr): an array of objects, each a line item configuration
  Returns:
    an array: an array of updated line item IDs
  """
  dfp_client = get_client()
  line_item_service = dfp_client.GetService('LineItemService', version='v201908')
  line_items = line_item_service.updateLineItems(line_items)

  # Return IDs of created line items.
  updated_line_item_ids = []
  for line_item in line_items:
    updated_line_item_ids.append(line_item['id'])
  return updated_line_item_ids
