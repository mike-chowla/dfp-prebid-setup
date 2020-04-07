from unittest import TestCase

from googleads import ad_manager
from mock import MagicMock, Mock, patch

import settings
import dfp.get_device_capabilities

@patch('googleads.ad_manager.AdManagerClient.LoadFromStorage')
class DFPGetDeviceCapabilitiesTests(TestCase):

  def test_get_device_capabilities(self, mock_dfp_client):
    """
    Ensure it calls DFP once with correct user filter info.
    """
    mock_dfp_client.return_value = MagicMock()

    # Mock DFP response for device category fetch.
    (mock_dfp_client.return_value
    .GetDataDownloader.return_value
    .DownloadPqlResultToList) = MagicMock(
        return_value = [['id', 'devicecapabilityname'], [5005, 'Mobile Apps'], [5001, 'MRAID v1'], [5006, 'MRAID v2'], [5000, 'Phone calls']]
    )

    devCapMap = dfp.get_device_capabilities.get_device_capabilities()
  
    expectedMap = {
        'Mobile Apps': 5005,
        'MRAID v1': 5001,
        'MRAID v2': 5006,
        'Phone calls': 5000
    }

    self.assertEqual(devCapMap, expectedMap)
