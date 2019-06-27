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
from types import ModuleType

from colorama import init

import dfp.associate_line_items_and_creatives
import dfp.create_custom_targeting
import dfp.create_creatives
import dfp.create_line_items
import dfp.create_orders
import dfp.get_advertisers
import dfp.get_custom_targeting
import dfp.get_placements
import dfp.get_users
import dfp.get_device_categories
import dfp.get_root_ad_unit_id
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
from tasks.dfp_utils import (
  TargetingKeyGen,
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

class OpenWrapTargetingKeyGen(TargetingKeyGen):
    def __init__(self):

        super().__init__()

        # Get DFP key IDs for line item targeting.
        self.pwtpid_key_id = get_or_create_dfp_targeting_key('pwtpid', key_type='PREDEFINED')  # bidder
        self.pwtbst_key_id = get_or_create_dfp_targeting_key('pwtbst', key_type='PREDEFINED')  # is pwt
        self.pwtcep_key_id = get_or_create_dfp_targeting_key('pwtecp', key_type='FREEFORM') # price
        self.pwtplt_key_id = get_or_create_dfp_targeting_key('pwtplt', key_type='PREDEFINED') # platform

        # Instantiate DFP targeting value ID getters for the targeting keys.
        self.BidderValueGetter = DFPValueIdGetter('pwtpid')
        self.BstValueGetter = DFPValueIdGetter('pwtbst')
        self.PriceValueGetter = DFPValueIdGetter('pwtecp', match_type='PREFIX')
        self.PltValueGetter = DFPValueIdGetter('pwtplt')

        self.pwtbst_value_id = self.BstValueGetter.get_value_id("1")
        self.bidder_criteria = None
        self.price_els = None

        self.creative_type = None
        self.get_custom_targeting = []

    def set_bidder_value(self, bidder_code):
        print("Setting bidder value to {0}".format(bidder_code))

        if bidder_code == None:
            self.bidder_criteria = None
            return

        if isinstance(bidder_code, (list, tuple)):
            # Multiple biders for us to OR to other
            bidder_criteria = []
            for bc in bidder_code:
                value_id = self.BidderValueGetter.get_value_id(bc)
                custom_criteria = {
                    'xsi_type': 'CustomCriteria',
                    'keyId': self.pwtpid_key_id,
                    'valueIds': [value_id],
                    'operator': 'IS'
                }
                bidder_criteria.append(custom_criteria)

            self.bidder_criteria = {
                'xsi_type': 'CustomCriteriaSet',
                'logicalOperator': 'OR',
                'children': bidder_criteria
            }
        else:
            self.bidder_criteria  = {
                'xsi_type': 'CustomCriteria',
                'keyId': self.pwtpid_key_id,
                'valueIds': [self.BidderValueGetter.get_value_id(bidder_code) ],
                'operator': 'IS'
            }

    def set_creative_type(self, ct):
        self.creative_type = ct

    def set_custom_targeting(self, custom_targeting):
        self.custom_targeting = []

        if custom_targeting == None:
            return

        for cc in custom_targeting:
            key_id = get_or_create_dfp_targeting_key(cc[0], key_type='FREEFORM')
            value_getter = DFPValueIdGetter(cc[0])
            one_custom_criteria = None

            if isinstance(cc[2], (list, tuple)):
                value_criterias = []
                for val in cc[2]:
                    value_id = value_getter.get_value_id(val)
                    criteria = {
                        'xsi_type': 'CustomCriteria',
                        'keyId': key_id,
                        'valueIds': [value_id],
                        'operator': cc[1]
                    }
                    value_criterias.append(criteria)

                operator = 'OR'
                if cc[1] == 'IS_NOT':
                    operator = 'AND'

                one_custom_criteria = {
                    'xsi_type': 'CustomCriteriaSet',
                    'logicalOperator': operator,
                    'children': value_criterias
                }
            else:
                one_custom_criteria  = {
                    'xsi_type': 'CustomCriteria',
                    'keyId': key_id,
                    'valueIds': [value_getter.get_value_id(cc[2]) ],
                    'operator': cc[1]
                }

            self.custom_targeting.append(one_custom_criteria)

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
            'children': [pwt_bst_criteria]
        }

        if self.creative_type == "AMP":
            amp_value_id = self.PltValueGetter.get_value_id("amp")
            platform_criteria = {
                'xsi_type': 'CustomCriteria',
                'keyId': self.pwtplt_key_id,
                'valueIds': [amp_value_id],
                'operator': 'IS'
            }
            top_set['children'].append(platform_criteria)

        if self.bidder_criteria:
            top_set['children'].append(self.bidder_criteria)

        top_set['children'].append(price_set)

        if len(self.custom_targeting) > 0:
            #top_set['children'].append(self.custom_targeting[0])
            top_set['children'].extend(self.custom_targeting)

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

def setup_partner(user_email, advertiser_name, advertiser_type, order_name, placements,
    sizes, bidder_code, prices, creative_type, num_creatives, currency_code,
    custom_targeting, same_adv_exception, device_categories, roadblock_type):
  """
  Call all necessary DFP tasks for a new Prebid partner setup.
  """

  # Get the user.
  user_id = dfp.get_users.get_user_id_by_email(user_email)

  # Get the placement IDs.
  placement_ids = None
  ad_unit_ids = None
  if len(placements) > 0:
      placement_ids = dfp.get_placements.get_placement_ids_by_name(placements)
  else:
      # Run of network
      root_id = dfp.get_root_ad_unit_id.get_root_ad_unit_id()
      ad_unit_ids = [ root_id ]

  # Get the device category IDs
  device_category_ids = None
  if device_categories != None:
      device_category_ids = []
      if isinstance(device_categories, str):
          device_categories = (device_categories)

      dc_map = dfp.get_device_categories.get_device_categories()

      for dc in device_categories:
          if dc in dc_map:
              device_category_ids.append(dc_map[dc])
          else:
              raise BadSettingException("Invalid Device Cagetory: " . dc)

  # Get (or potentially create) the advertiser.
  advertiser_id = dfp.get_advertisers.get_advertiser_id_by_name(
    advertiser_name, advertiser_type)

  # Create the order.
  order_id = dfp.create_orders.create_order(order_name, advertiser_id, user_id)

  # Create creatives.
  bidder_str = bidder_code
  if bidder_str == None:
      bidder_str = "All"
  elif isinstance(bidder_str, (list, tuple)):
      bidder_str = "_".join(bidder_str)

  creative_file = "creative_snippet_openwrap.html"
  use_safe_frame = False
  if creative_type == "WEB":
    creative_file = "creative_snippet_openwrap.html"
  elif creative_type == "WEB_SAFEFRAME":
    creative_file = "creative_snippet_openwrap_sf.html"
    use_safe_frame = True
  elif creative_type == "AMP":
    creative_file = "creative_snippet_openwrap_amp.html"
  elif creative_type == "IN_APP":
    creative_file = "creative_snippet_openwrap_in_app.html"
  elif creative_type == "UNIVERSAL":
    creative_file = "creative_snippet_openwrap_universal.html"

  creative_configs = dfp.create_creatives.create_duplicate_creative_configs(
      bidder_str, order_name, advertiser_id, num_creatives, creative_file=creative_file, safe_frame=use_safe_frame)
  creative_ids = dfp.create_creatives.create_creatives(creative_configs)

  # Create line items.
  line_items_config = create_line_item_configs(prices, order_id,
    placement_ids, bidder_code, sizes, OpenWrapTargetingKeyGen(),
    currency_code, custom_targeting, creative_type, same_adv_exception=same_adv_exception,ad_unit_ids=ad_unit_ids,
    device_category_ids=device_category_ids, roadblock_type=roadblock_type)
    
  logger.info("Creating line items...")
  #pp = pprint.PrettyPrinter(indent=4)
  #pp.pprint(line_items_config)
  line_item_ids = dfp.create_line_items.create_line_items(line_items_config)

  # Associate creatives with line items.
  dfp.associate_line_items_and_creatives.make_licas(line_item_ids,
    creative_ids, size_overrides=sizes)

  logger.info("""

    Done! Please review your order, line items, and creatives to
    make sure they are correct. Then, approve the order in DFP.

    Happy bidding!

  """)

def create_line_item_configs(prices, order_id, placement_ids, bidder_code,
  sizes, key_gen_obj, currency_code, custom_targeting, creative_type,
  ad_unit_ids=None, same_adv_exception=False, device_category_ids=None,
  roadblock_type='ONE_OR_MORE'):
  """
  Create a line item config for each price bucket.

  Args:
    prices (array)
    order_id (int)
    placement_ids (arr)
    bidder_code (str or arr)
    sizes (arr)
    key_gen_obj (obj)
    currency_code (str)
    custom_targeting (arr)
    ad_unit_ids (arr)
    same_adv_exception(bool)
    device_category_ids (int)
    roadblock_type (str)
  Returns:
    an array of objects: the array of DFP line item configurations
  """

  # The DFP targeting value ID for this `hb_bidder` code.
  key_gen_obj.set_bidder_value(bidder_code)
  key_gen_obj.set_creative_type(creative_type)
  key_gen_obj.set_custom_targeting(custom_targeting)

  line_items_config = []
  for price in prices:

    price_str = num_to_str(price['rate'], precision=3)

    # Remove trailing zero if exists
    if re.match("\d+\.\d{2}0",price_str):
        price_str = price_str[0:-1]

    bidder_str = bidder_code
    if bidder_str == None:
        bidder_str = "All"
    elif isinstance(bidder_str, (list, tuple)):
        bidder_str = "_".join(bidder_str)

    # Autogenerate the line item name.
    line_item_name = u'{bidder_code}: OW ${price}'.format(
      bidder_code=bidder_str,
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
      ad_unit_ids=ad_unit_ids,
      same_adv_exception=same_adv_exception,
      device_categories=device_category_ids,
      roadblock_type=roadblock_type
    )

    line_items_config.append(config)

  return line_items_config

def get_calculated_rate(start_rate_range, end_rate_range, rate_id):

    if(start_rate_range == 0 and rate_id == 2):
        rate_id = 1

    if rate_id == 2:
        return start_rate_range
    else:
        return round((start_rate_range + end_rate_range) / 2.0, 3)


def load_price_csv_from_file(filename):
    with open(filename, 'r') as csvfile:
        return load_price_csv_from_stream(csvfile)
        
def load_price_csv_from_stream(csvfile):
    buckets = []
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

def get_setting(settings_obj, setting_name, setting_default):
    if isinstance(settings_obj, ModuleType):
        return getattr(settings_obj, setting_name, setting_default)
    else:
        if setting_name in settings_obj:
            return settings_obj[setting_name]
        else:
            return setting_default
    
def main():
  """
  Validate the settings and ask for confirmation from the user. Then,
  start all necessary DFP tasks.
  """

  parser = argparse.ArgumentParser()
  parser.add_argument('--yaml_file', help='Use .yaml config instead of settings.py')
  parser.add_argument('--generate_yaml', help='Output Config as a YAML file')
  args = parser.parse_args()
    
  if args.yaml_file:
    from yaml import safe_load
    with open(args.yaml_file, 'r') as stream:
        settings = safe_load(stream)
  else:
    import settings
    
  if args.generate_yaml:
    from yaml import dump
    
    settings_dict = {}
    for s in dir(settings): 
        if not s.startswith('__'):
            settings_dict[s] = getattr(settings, s, None)
            
    with open(args.generate_yaml, 'w') as outfile:
        dump(settings_dict, outfile, default_flow_style=False)
        return
    
  run(settings)


def run(settings, csv_file_stream=None, no_confirm=False):
  user_email = get_setting(settings, 'DFP_USER_EMAIL_ADDRESS', None)
  if user_email is None:
    raise MissingSettingException('DFP_USER_EMAIL_ADDRESS')

  advertiser_name = get_setting(settings, 'DFP_ADVERTISER_NAME', None)
  if advertiser_name is None:
    raise MissingSettingException('DFP_ADVERTISER_NAME')
    
  advertiser_type = get_setting(settings, 'DFP_ADVERTISER_TYPE', "AD_NETWORK")
  if advertiser_type != "ADVERTISER" and advertiser_type != "AD_NETWORK":
    raise BadSettingException('DFP_ADVERTISER_TYPE')

  order_name = get_setting(settings, 'DFP_ORDER_NAME', None)
  if order_name is None:
    raise MissingSettingException('DFP_ORDER_NAME')

  num_placements = 0
  placements = get_setting(settings, 'DFP_TARGETED_PLACEMENT_NAMES', None)
  if placements is None:
    placements = []

  # if no placements are specified, we wil do run of network which is
  #   effectively one placement
  num_placements = len(placements)
  if num_placements == 0:
      num_placements = 1

  sizes = get_setting(settings, 'DFP_PLACEMENT_SIZES', None)
  if sizes is None:
    raise MissingSettingException('DFP_PLACEMENT_SIZES')
  elif len(sizes) < 1:
    raise BadSettingException('The setting "DFP_PLACEMENT_SIZES" '
      'must contain at least one size object.')

  currency_code = get_setting(settings, 'DFP_CURRENCY_CODE', 'USD')

  # How many creatives to attach to each line item. We need at least one
  # creative per ad unit on a page. See:
  # https://github.com/kmjennison/dfp-prebid-setup/issues/13
  num_creatives = (
    get_setting(settings, 'DFP_NUM_CREATIVES_PER_LINE_ITEM', None) or
    num_placements
  )

  creative_type = get_setting(settings, 'OPENWRAP_CREATIVE_TYPE', None)
  if creative_type is None:
    creative_type = "WEB"
  elif creative_type not in ["WEB", "WEB_SAFEFRAME", "AMP", "IN_APP", "UNIVERSAL"]:
    raise BadSettingException('Unknown OPENWRAP_CREATIVE_TYPE: {0}'.format(creative_type))

  bidder_code = get_setting(settings, 'PREBID_BIDDER_CODE', None)
  if bidder_code is not None and not isinstance(bidder_code, (list, tuple, str)):
    raise BadSettingException('PREBID_BIDDER_CODE')

  same_adv_exception = get_setting(settings, 'DFP_SAME_ADV_EXCEPTION', False)
  if not isinstance(same_adv_exception, bool):
      raise BadSettingException('DFP_SAME_ADV_EXCEPTION')

  device_categories = get_setting(settings, 'DFP_DEVICE_CATEGORIES', None)
  if device_categories is not None and not isinstance(device_categories, (list, tuple, str)):
       raise BadSettingException('DFP_DEVICE_CATEGORIES')

  roadblock_type = get_setting(settings, 'DFP_ROADBLOCK_TYPE', 'ONE_OR_MORE')
  if roadblock_type not in ('ONE_OR_MORE', 'AS_MANY_AS_POSSIBLE'):
      raise BadSettingException('DFP_ROADBLOCK_TYPE')

  custom_targeting = get_setting(settings, 'OPENWRAP_CUSTOM_TARGETING', None)
  if custom_targeting != None:
      if not isinstance(custom_targeting, (list, tuple)):
          raise BadSettingException('OPENWRAP_CUSTOM_TARGETING')

      for ct in custom_targeting:
         if len(ct) != 3:
             raise BadSettingException('OPENWRAP_CUSTOM_TARGETING')

         if ct[1] != "IS" and ct[1] != "IS_NOT":
             raise BadSettingException('OPENWRAP_CUSTOM_TARGETING')

         if not isinstance(ct[2], (list, tuple, str)):
             raise BadSettingException('OPENWRAP_CUSTOM_TARGETING')

  if csv_file_stream != None:
    prices = load_price_csv_from_stream(csv_file_stream)
  else:
    price_buckets_csv = get_setting(settings, 'OPENWRAP_BUCKET_CSV', None)
    if price_buckets_csv is None:
        raise MissingSettingException('OPENWRAP_BUCKET_CSV')

    prices = load_price_csv_from_file(price_buckets_csv)

  prices_summary = []
  for p in prices:
      prices_summary.append(p['rate'])

  logger.info(
    u"""

    Going to create {name_start_format}{num_line_items}{format_end} new line items.
      {name_start_format}Order{format_end}: {value_start_format}{order_name}{format_end}
      {name_start_format}Advertiser{format_end}: {value_start_format}{advertiser}{format_end}
      {name_start_format}Advertiser Type{format_end}: {value_start_format}{advertiser_type}{format_end}

    Line items will have targeting:
      {name_start_format}hb_pb{format_end} = {value_start_format}{prices_summary}{format_end}
      {name_start_format}hb_bidder{format_end} = {value_start_format}{bidder_code}{format_end}
      {name_start_format}placements{format_end} = {value_start_format}{placements}{format_end}
      {name_start_format}creative_type{format_end} = {value_start_format}{creative_type}{format_end}
      {name_start_format}custom targeting{format_end} = {value_start_format}{custom_targeting}{format_end}
      {name_start_format}same advertiser exception{format_end} = {value_start_format}{same_adv_exception}{format_end}
      {name_start_format}device categories{format_end} = {value_start_format}{device_categories}{format_end}
      {name_start_format}roadblock type{format_end} = {value_start_format}{roadblock_type}{format_end}
    """.format(
      num_line_items = len(prices),
      order_name=order_name,
      advertiser=advertiser_name,
      advertiser_type=advertiser_type,
      user_email=user_email,
      prices_summary=prices_summary,
      bidder_code=bidder_code,
      placements=placements,
      creative_type=creative_type,
      sizes=sizes,
      custom_targeting=custom_targeting,
      same_adv_exception=same_adv_exception,
      device_categories=device_categories,
      roadblock_type=roadblock_type,
      name_start_format=color.BOLD,
      format_end=color.END,
      value_start_format=color.BLUE,
    ))

  if no_confirm != True:
    ok = input('Is this correct? (y/n)\n')

    if ok != 'y':
        logger.info('Exiting.')
        return

  setup_partner(
    user_email,
    advertiser_name,
    advertiser_type,
    order_name,
    placements,
    sizes,
    bidder_code,
    prices,
    creative_type,
    num_creatives,
    currency_code,
    custom_targeting,
    same_adv_exception,
    device_categories,
    roadblock_type
  )


if __name__ == '__main__':
  main()
