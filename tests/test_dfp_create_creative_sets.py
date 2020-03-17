import os
from unittest import TestCase
from mock import MagicMock, Mock, patch

import settings
import dfp.create_creative_sets


@patch('googleads.ad_manager.AdManagerClient.LoadFromStorage')
class DFPCreateCreativeSetsTests(TestCase):

  def test_create_creative_sets_items_call(self, mock_dfp_client):
    """
    Ensure it calls DFP once with creative info.
    """

    mock_dfp_client.return_value = MagicMock()

    creative_set_configs = dfp.create_creative_sets.create_creative_set_config( 
        creative_ids = [1],
        sizes = [
            {
                "width": '300',
                "height": '250'
            }
        ],
        prefix='axmsfl',
      )
    

    dfp.create_creative_sets.create_creative_sets(creative_set_configs)

    (mock_dfp_client.return_value
      .GetService.return_value
      .createCreativeSet.assert_called_once_with(creative_set_configs[0])
    )


  def test_create_creative_sets_returns_ids(self, mock_dfp_client):
    """
    Ensure it returns the IDs of created creative sets.
    """

    # Mock DFP response after creating line items.
    (mock_dfp_client.return_value
      .GetService.return_value
      .createCreativeSet) = MagicMock(return_value=        
        # Approximate shape of DFP creative set response.
        {
          'id': 16273849,
        }
      )

    creative_set_configs = [{}] # Mock does not matter.
    self.assertEqual(
      dfp.create_creative_sets.create_creative_sets(creative_set_configs),
      [16273849]
    )

  def test_create_creative_set_config(self, mock_dfp_client):

    creative_set_configs = dfp.create_creative_sets.create_creative_set_config( 
        creative_ids = [1,2],
        sizes = [
            {
                "width": '300',
                "height": '250'
            },
            {
                "width": '300',
                "height": '20'
            }
        ],
        prefix='axmsfl',
      )
    
    expected_config = [
        {
            'name': 'axmsfl_300x250',
            'masterCreativeId': 1
        }, 
        {
            'name': 'axmsfl_300x20',
            'masterCreativeId': 2
        }
    ]
    
    self.assertEqual(creative_set_configs, expected_config )
   