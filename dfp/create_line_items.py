
from googleads import dfp

from dfp.client import get_client

def create_line_items(line_items):
  """
  Creates line items in DFP.

  Args:
    line_items (arr): an array of objects, each a line item configuration
  Returns:
    an array: an array of created line item IDs
  """
  dfp_client = get_client()
  line_item_service = dfp_client.GetService('LineItemService', version='v201802')
  line_items = line_item_service.createLineItems(line_items)

  # Return IDs of created line items.
  created_line_item_ids = []
  for line_item in line_items:
    created_line_item_ids.append(line_item['id'])
  return created_line_item_ids

def create_line_item_config(name, order_id, placement_ids, cpm_micro_amount,
  sizes, key_gen_obj, currency_code='USD', ad_unit_ids=None):
  """
  Creates a line item config object.

  Args:
    name (str): the name of the line item
    order_id (int): the ID of the order in DFP
    placement_ids (arr): an array of DFP placement IDs to target
    cpm_micro_amount (int): the currency value (in micro amounts) of the
      line item
    sizes (arr): an array of objects, each containing 'width' and 'height'
      keys, to set the creative sizes this line item will serve
    hb_bidder_key_id (int): the DFP ID of the `hb_bidder` targeting key
    hb_pb_key_id (int): the DFP ID of the `hb_pb` targeting key
    currency_code (str): the currency code (e.g. 'USD' or 'EUR')
  Returns:
    an object: the line item config
  """

  # Set up sizes.
  creative_placeholders = []

  for size in sizes:
    creative_placeholders.append({
      'size': size
    })

  top_set = key_gen_obj.get_dfp_targeting()

  # https://developers.google.com/doubleclick-publishers/docs/reference/v201802/LineItemService.LineItem
  line_item_config = {
    'name': name,
    'orderId': order_id,
    # https://developers.google.com/doubleclick-publishers/docs/reference/v201802/LineItemService.Targeting
    'targeting': {
      'inventoryTargeting': None,
      'customTargeting': top_set,
    },
    'startDateTimeType': 'IMMEDIATELY',
    'unlimitedEndDateTime': True,
    'lineItemType': 'PRICE_PRIORITY',
    'costType': 'CPM',
    'costPerUnit': {
      'currencyCode': currency_code,
      'microAmount': cpm_micro_amount
    },
    'creativeRotationType': 'EVEN',
    'primaryGoal': {
      'goalType': 'NONE'
    },
    'creativePlaceholders': creative_placeholders,
  }

  if placement_ids and len(placement_ids) > 0:
      line_item_config['targeting']['inventoryTargeting'] = { 'targetedPlacementIds': placement_ids }
  else:
      ad_unit_targeting = []
      for a in ad_unit_ids:
          ad_unit_targeting.append({"adUnitId": a, "includeDescendants": True })
      line_item_config['targeting']['inventoryTargeting'] = { 'targetedAdUnits': ad_unit_targeting }

  return line_item_config
