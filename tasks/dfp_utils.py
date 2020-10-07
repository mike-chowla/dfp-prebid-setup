import dfp.get_custom_targeting

class TargetingKeyGen():
    def __init__(self):
        pass

    def get_dfp_targeting(self):
        assert False
        return None

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
                    'keyId': self.bidder_key_id,
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
                'keyId': self.bidder_key_id,
                'valueIds': [self.BidderValueGetter.get_value_id(bidder_code) ],
                'operator': 'IS'
            }

    def set_price_value(self, price_str):
        assert False
        return None

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
      self.key_id, match_type=self.match_type)

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

def get_or_create_dfp_targeting_key(name, key_type='FREEFORM'):
  """
  Get or create a custom targeting key by name.

  Args:
    name (str)
  Returns:
    an integer: the ID of the targeting key
  """
  key_id = dfp.get_custom_targeting.get_key_id_by_name(name)
  if key_id is None:
    key_id = dfp.create_custom_targeting.create_targeting_key(name, key_type=key_type)
  return key_id
