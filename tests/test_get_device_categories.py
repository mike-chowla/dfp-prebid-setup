from unittest import TestCase

from googleads import ad_manager
from mock import MagicMock, Mock, patch

import settings
import dfp.get_device_categories

@patch('googleads.ad_manager.AdManagerClient.LoadFromStorage')
class DFPGetDeviceCategoriesTests(TestCase):

  def test_get_device_categories(self, mock_dfp_client):
    """
    Ensure it calls DFP once with correct user filter info.
    """
    mock_dfp_client.return_value = MagicMock()

    # Mock DFP response for device category fetch.
    (mock_dfp_client.return_value
    .GetDataDownloader.return_value
    .DownloadPqlResultToList) = MagicMock(
        return_value = [['id', 'devicecategoryname'], [30004, 'Connected TV'], [30000, 'Desktop'], [30003, 'Feature Phone'], [30006, 'Set Top Box'], [30001, 'Smartphone'], [30002, 'Tablet']]
    )

    devCatMap = dfp.get_device_categories.get_device_categories()
  
    expectedMap = {
        'Connected TV': 30004,
        'Desktop': 30000,
        'Feature Phone': 30003,
        'Set Top Box': 30006,
        'Smartphone': 30001, 
        'Tablet': 30002
    }

    self.assertEqual(devCatMap, expectedMap)