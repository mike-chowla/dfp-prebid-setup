#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys
import csv
from builtins import input
from pprint import pprint

from colorama import init

import settings
import dfp.associate_line_items_and_creatives
import dfp.create_custom_targeting
import dfp.create_creatives
import dfp.create_line_items
import dfp.create_orders
import dfp.get_advertisers
import dfp.get_custom_targeting
import dfp.get_placements
import dfp.get_users
from dfp.exceptions import (
  BadSettingException,
  MissingSettingException
)
from tasks.price_utils import (
  get_prices_array,
  get_prices_summary_string,
  num_to_micro_amount,
  micro_amount_to_num,
  num_to_str,
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

class TargetingKeyGen():
    def __init__(self):
        pass

    def get_dfp_targeting(self):
        assert False
        return None

    def set_bidder_value(self, bidder_code):
        assert False
        return None

    def set_price_value(self, price_str):
        assert False
        return None

class OpenWrapTargetingKeyGen():
    def __init__(self):

        super().__init__()

        # Get DFP key IDs for line item targeting.
        self.pwtpid_key_id = get_or_create_dfp_targeting_key('pwtpid')  # bidder
        self.pwtbst_key_id = get_or_create_dfp_targeting_key('pwtbst')  # is pwt
        self.pwtcep_key_id = get_or_create_dfp_targeting_key('pwtecp')  # price

        # Instantiate DFP targeting value ID getters for the targeting keys.
        self.BidderValueGetter = DFPValueIdGetter('pwtpid')
        self.BstValueGetter = DFPValueIdGetter('pwtbst', match_type='PREFIX')
        self.PriceValueGetter = DFPValueIdGetter('pwtecp')

        self.pwtbst_value_id = self.BstValueGetter.get_value_id("1")
        self.bidder_value_id = None
        self.price_els = None

    def set_bidder_value(self, bidder_code):
        print("Setting bidder value to {0}".format(bidder_code))
        self.bidder_value_id = self.BidderValueGetter.get_value_id(bidder_code)
        return self.bidder_value_id

    def set_price_value(self, price_obj):
        self.price_els = self.process_price_bucket(price_obj['start'], price_obj['end'], price_obj['granularity'])
        return self.price_els

    def get_dfp_targeting(self):

        # is PWT
        pwt_bst_criteria = {
            'xsi_type': 'CustomCriteria',
            'keyId': self.pwtbst_key_id,
            'valueIds': [self.pwtbst_value_id ],
            'operator': 'IS'
        }

        # Bidder
        pwt_bidder_criteria = {
            'xsi_type': 'CustomCriteria',
            'keyId': self.pwtpid_key_id,
            'valueIds': [self.bidder_value_id ],
            'operator': 'IS'
        }

        # Generate Ids for all the price elements
        price_value_ids = []
        for p in self.price_els:
            value_id = self.PriceValueGetter.get_value_id(p)
            custom_criteria = {
                'xsi_type': 'CustomCriteria',
                'keyId': self.pwtcep_key_id ,
                'valueIds': [value_id],
                'operator': 'IS'
            }
            price_value_ids.append(custom_criteria)

        price_set = {
            'xsi_type': 'CustomCriteriaSet',
            'logicalOperator': 'OR',
            'children': price_value_ids
        }

        top_set = {
            'xsi_type': 'CustomCriteriaSet',
            'logicalOperator': 'AND',
            'children': [pwt_bst_criteria, pwt_bidder_criteria, price_set]
        }

        return top_set

    def process_price_bucket(self, start_index, end_index, granu):

        subCustomValueArray = []
        sub_granu = None

        if granu < 0.10:
            sub_granu = 0.01
        elif granu < 1:
            sub_granu = 0.10
        else:
            sub_granu = 1.00

        # if granu is .20 then $r=0 if .25 then $r=5
        r = granu * 100 % 1
        k = start_index

        while round(k,2) < round(end_index,2):

            logger.debug("k: %f  end_index: %f", k, end_index)
            # if k=1.25 then reminder is 5>0 and for .20 its 0
            if round(k*100) % 10 > 0 or sub_granu == 0.01:
                if r >= 0:
                    #suppose start_index=0.33 and $end=0.40
                    end = None
                    if sub_granu < 0.10:
                        end = k+(granu*100)%10/100
                    else:
                        end = k+(10-(round(k*100)%10))/100

                    if end >= end_index:
                        end = end_index

                    if k == 0 and sub_granu == 0.01:
                        k = 0.01

                    v = k
                    while round(v,2) < round(end,2):
                        v_str = "{0:.2f}".format(v)
                        logger.debug("----First---- Custom criteria for Line Item is =  %s", v_str)
                        subCustomValueArray.append(v_str);
                        v = v + 0.01

                    if end + 0.10 <= end_index:
                        k = k + (10-(round(k*100)%10))/100
                    else:
                        k = end

                else: # if r >= 0:
                    logger.debug("----Second---- Custom criteria for Line Item is =  %f", k)
                    subCustomValueArray.append(k);
                    k = k + sub_granu;
            else: # if round(k*100)%10) > 0 or sub_granu == 0.01
                if r > 0 and round(k+sub_granu,2) > round(end_index,2):
                    # To create the custom value from 10 to granularity which can .5, so 10-14
                    g = None
                    if granu > 1:
                        g = 0.10
                    else:
                        g = 0.01

                    v = k
                    while round(v,2) < round(end_index,2):
                        temp = v
                        if granu > 1:
                            temp = round(temp, 1)
                        else:
                            temp = round(temp, 2)
                        #CreatePubmaticLineItems::lineItemLogger("--V=".$g."--\n");

                        if v+g > end_index and round(v+g,2) != round(end_index,2):
                            subCustomValueArray.append("{0:.2f}".format(temp))
                            logger.debug("----Third---- Custom criteria for Line Item is =  %.2f", subCustomValueArray[-1])
                            g = 0.01
                            v = v + g
                            continue

                        if (g == 0.10):
                            subCustomValueArray.append("{0:.1f}".format(v))
                        else:
                            subCustomValueArray.append("{0:.2f}".format(v))

                        logger.debug("----Third---- Custom criteria for Line Item is =  %s", subCustomValueArray[-1])
                        v = v + g

                    k = k + sub_granu
                elif k == 0: # if r > 0 and round(k+sub_granu,2) > round(end_index,2)
                    vEnd = None
                    if sub_granu < 0.10:
                        vEnd = granu
                    else:
                        vEnd = 0.10

                    v = 0.01
                    while v <= vEnd-0.01:
                        subCustomValueArray.append(str(round(v,2)))
                        logger.debug("----Fourth---- Custom criteria for Line Item is =  %s", subCustomValueArray[-1])
                        v = v + 0.01

                    k = k + vEnd
                else:
                    if sub_granu != 1:
                        k = round(k,1)

                    if ((round(k*10)) % 10 != 0 or sub_granu ==0.10) and (round(k+sub_granu,2) <= round(end_index,2)):
                        subCustomValueArray.append(str(round(k,2)))
                        logger.debug("----fifth----1 Custom criteria for Line Item is =  %s", subCustomValueArray[-1])
                    elif (k+sub_granu > end_index and granu == 1) or (granu> 1 and k + sub_granu >end_index):
                        subCustomValueArray.append("{0:.1f}".format(k))
                        logger.debug("----fifth----2 Custom criteria for Line Item is =  %s", subCustomValueArray[-1])
                    elif sub_granu == 0.10 and round(k+sub_granu,2) > round(end_index,2) and end_index*100%10 >0:
                        subCustomValueArray.append("{0:.2f}".format(k))
                        logger.debug("----fifth----2.5 Custom criteria for Line Item is =  %s", subCustomValueArray[-1])
                    else:
                        subCustomValueArray.append("{0}.".format(k))
                        logger.debug("----fifth----3 Custom criteria for Line Item is =  %s", subCustomValueArray[-1])

                    if k >= 1 and round(k*10)%10==0 and k+sub_granu <= end_index: #if $k=2 and end range is 2.57 then it should not increment to 3 while granu is 1
                        k = k+sub_granu
                    elif sub_granu == 0.10 and (round(k+sub_granu,2) > round(end_index,2) and end_index*100%10 > 0): #$end_index*100%10>0 and $sub_granu==0.10 and $k+$sub_granu>$end_index)
                        k = k + 0.01
                    else:
                        k = round(k,2) + 0.10

                    if (round(k,2) != round(end_index,2)) and (round(k+0.10,2) != round (end_index,2)) and ((k+0.10 > end_index and granu == 1) or (k + 0.10 > end_index and granu>1)):
                        subCustomValueArray.append("{0:.2f}".format(k))
                        logger.debug("----fifth----4 Custom criteria for Line Item is =  %s", subCustomValueArray[-1])
                        k = k + 0.01

        return subCustomValueArray

def setup_partner(user_email, advertiser_name, order_name, placements,
    sizes, bidder_code, prices, num_creatives, currency_code):
  """
  Call all necessary DFP tasks for a new Prebid partner setup.
  """

  # Get the user.
  user_id = dfp.get_users.get_user_id_by_email(user_email)

  # Get the placement IDs.
  placement_ids = dfp.get_placements.get_placement_ids_by_name(placements)

  # Get (or potentially create) the advertiser.
  advertiser_id = dfp.get_advertisers.get_advertiser_id_by_name(
    advertiser_name)

  # Create the order.
  order_id = dfp.create_orders.create_order(order_name, advertiser_id, user_id)

  # Create creatives.
  creative_configs = dfp.create_creatives.create_duplicate_creative_configs(
      bidder_code, order_name, advertiser_id, num_creatives, creative_file="creative_snippet_openwrap.html")
  creative_ids = dfp.create_creatives.create_creatives(creative_configs)

  # Create line items.
  line_items_config = create_line_item_configs(prices, order_id,
    placement_ids, bidder_code, sizes, OpenWrapTargetingKeyGen(),
    currency_code)

  logger.info("Creating line items...")
  line_item_ids = dfp.create_line_items.create_line_items(line_items_config)

  # Associate creatives with line items.
  dfp.associate_line_items_and_creatives.make_licas(line_item_ids,
    creative_ids, size_overrides=sizes)

  logger.info("""

    Done! Please review your order, line items, and creatives to
    make sure they are correct. Then, approve the order in DFP.

    Happy bidding!

  """)

class DFPValueIdGetter(object):
  """
  A class to bulk fetch DFP values by key and then create new values as needed.
  """

  def __init__(self, key_name, *args, **kwargs):
    """
    Args:
      key_name (str): the name of the DFP key
    """
    self.key_name = key_name
    self.match_type = 'EXACT'

    if 'match_type' in kwargs:
        self.match_type = kwargs['match_type']

    self.key_id = dfp.get_custom_targeting.get_key_id_by_name(key_name)
    self.existing_values = dfp.get_custom_targeting.get_targeting_by_key_name(
      key_name)
    super(DFPValueIdGetter, self).__init__()

  def _get_value_id_from_cache(self, value_name):
    val_id = None
    for value_obj in self.existing_values:
      if value_obj['name'] == value_name:
        val_id = value_obj['id']
        break
    return val_id

  def _create_value_and_return_id(self, value_name):
    return dfp.create_custom_targeting.create_targeting_value(value_name,
      self.key_id)

  def get_value_id(self, value_name):
    """
    Get the DFP custom value ID, or create it if it doesn't exist.

    Args:
      value_name (str): the name of the DFP value
    Returns:
      an integer: the ID of the DFP value
    """
    val_id = self._get_value_id_from_cache(value_name)
    if not val_id:
      val_id = self._create_value_and_return_id(value_name)
    return val_id



def get_or_create_dfp_targeting_key(name):
  """
  Get or create a custom targeting key by name.

  Args:
    name (str)
  Returns:
    an integer: the ID of the targeting key
  """
  key_id = dfp.get_custom_targeting.get_key_id_by_name(name)
  if key_id is None:
    key_id = dfp.create_custom_targeting.create_targeting_key(name)
  return key_id

def create_line_item_configs(prices, order_id, placement_ids, bidder_code,
  sizes, key_gen_obj, currency_code):
  """
  Create a line item config for each price bucket.

  Args:
    prices (array)
    order_id (int)
    placement_ids (arr)
    bidder_code (str)
    sizes (arr)
    key_gen_obj (obj)
    currency_code (str)
  Returns:
    an array of objects: the array of DFP line item configurations
  """

  # The DFP targeting value ID for this `hb_bidder` code.
  key_gen_obj.set_bidder_value(bidder_code)

  line_items_config = []
  for price in prices:

    price_str = num_to_str(price['rate'])

    # Autogenerate the line item name.
    line_item_name = u'{bidder_code}: OW ${price}'.format(
      bidder_code=bidder_code,
      price=price_str
    )

    # The DFP targeting value ID for this `hb_pb` price value.
    key_gen_obj.set_price_value(price)

    config = dfp.create_line_items.create_line_item_config(
      name=line_item_name,
      order_id=order_id,
      placement_ids=placement_ids,
      cpm_micro_amount=num_to_micro_amount(price['rate']),
      sizes=sizes,
      key_gen_obj=key_gen_obj,
      currency_code=currency_code,
    )

    line_items_config.append(config)

  return line_items_config

def get_calculated_rate(start_rate_range, end_rate_range, rate_id):

    if(start_rate_range == 0 and rate_id == 2):
        rate_id = 1

    if rate_id == 2:
        return start_rate_range
    else:
        return round(start_rate_range + end_rate_range / 2.0, 2)


def load_price_csv(filename):
    buckets = []
    with open(filename, 'r') as csvfile:
        preader = csv.reader(csvfile)
        next(preader)  # skip header row
        for row in preader:
                print(row)
                order_name = row[0]
                advertiser = row[1]
                start_range = float(row[2])
                end_range = float(row[3])
                granularity = row[4]
                rate_id = int(row[5])

                if granularity != "-1":
                    granularity = float(granularity)
                    i = start_range
                    while i < end_range:
                        a = round(i + granularity,2)
                        if a > end_range:
                            a = end_range

                        if round(i,2) != (a,2):
                             buckets.append({
                                'start': i,
                                'end': a,
                                'granularity': granularity,
                                'rate': get_calculated_rate(i, a, rate_id)
                             })
                        i = a
                else:
                     buckets.append({
                        'start': start_range,
                        'end': end_range,
                        'granularity': 1.0,
                        'rate': get_calculated_rate(i, a, rate_id)
                     })

    return buckets


def check_price_buckets_validity(price_buckets):
  """
  Validate that the price_buckets object contains all required keys and the
  values are the expected types.

  Args:
    price_buckets (object)
  Returns:
    None
  """

  try:
    pb_precision = price_buckets['precision']
    pb_min = price_buckets['min']
    pb_max = price_buckets['max']
    pb_increment = price_buckets['increment']
  except KeyError:
    raise BadSettingException('The setting "PREBID_PRICE_BUCKETS" '
      'must contain keys "precision", "min", "max", and "increment".')

  if not (isinstance(pb_precision, int) or isinstance(pb_precision, float)):
    raise BadSettingException('The "precision" key in "PREBID_PRICE_BUCKETS" '
      'must be a number.')

  if not (isinstance(pb_min, int) or isinstance(pb_min, float)):
    raise BadSettingException('The "min" key in "PREBID_PRICE_BUCKETS" '
      'must be a number.')

  if not (isinstance(pb_max, int) or isinstance(pb_max, float)):
    raise BadSettingException('The "max" key in "PREBID_PRICE_BUCKETS" '
      'must be a number.')

  if not (isinstance(pb_increment, int) or isinstance(pb_increment, float)):
    raise BadSettingException('The "increment" key in "PREBID_PRICE_BUCKETS" '
      'must be a number.')

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

  placements = getattr(settings, 'DFP_TARGETED_PLACEMENT_NAMES', None)
  if placements is None:
    raise MissingSettingException('DFP_TARGETED_PLACEMENT_NAMES')
  elif len(placements) < 1:
    raise BadSettingException('The setting "DFP_TARGETED_PLACEMENT_NAMES" '
      'must contain at least one DFP placement ID.')

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
    len(placements)
  )

  bidder_code = getattr(settings, 'PREBID_BIDDER_CODE', None)
  if bidder_code is None:
    raise MissingSettingException('PREBID_BIDDER_CODE')

  price_buckets_csv = getattr(settings, 'OPENWRAP_BUCKET_CSV', None)
  if price_buckets_csv is None:
    raise MissingSettingException('OPENWRAP_BUCKET_CSV')

  prices = load_price_csv(price_buckets_csv)

  prices_summary = []
  for p in prices:
      prices_summary.append(p['rate'])

  logger.info(
    u"""

    Going to create {name_start_format}{num_line_items}{format_end} new line items.
      {name_start_format}Order{format_end}: {value_start_format}{order_name}{format_end}
      {name_start_format}Advertiser{format_end}: {value_start_format}{advertiser}{format_end}

    Line items will have targeting:
      {name_start_format}hb_pb{format_end} = {value_start_format}{prices_summary}{format_end}
      {name_start_format}hb_bidder{format_end} = {value_start_format}{bidder_code}{format_end}
      {name_start_format}placements{format_end} = {value_start_format}{placements}{format_end}

    """.format(
      num_line_items = len(prices),
      order_name=order_name,
      advertiser=advertiser_name,
      user_email=user_email,
      prices_summary=prices_summary,
      bidder_code=bidder_code,
      placements=placements,
      sizes=sizes,
      name_start_format=color.BOLD,
      format_end=color.END,
      value_start_format=color.BLUE,
    ))

  ok = input('Is this correct? (y/n)\n')

  if ok != 'y':
    logger.info('Exiting.')
    return

  setup_partner(
    user_email,
    advertiser_name,
    order_name,
    placements,
    sizes,
    bidder_code,
    prices,
    num_creatives,
    currency_code,
  )

if __name__ == '__main__':
  main()
