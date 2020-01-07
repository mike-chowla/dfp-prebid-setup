[![Build Status](https://travis-ci.org/kmjennison/dfp-prebid-setup.svg?branch=master)](https://travis-ci.org/kmjennison/dfp-prebid-setup)

# Setup Tool for Prebid, Openwrap and GAM (previously DFP)
An automated line item generator for [Prebid.js](http://prebid.org/), Openwrap and Google Ad Manager (previously DFP)

## Overview
When setting up Prebid/Openwrap, your ad ops team often has to create [hundreds of line items](http://prebid.org/adops.html) in Google Ad Manager (GAM).

This tool automates setup for new header bidding partners. You define the advertiser, placements or ad units, and Prebid/Openwrap settings; then, it creates an order with one line item per price level, attaches creatives, sets placement and/or ad units, and Prebid/Openwrap key-value targeting.

While this tool covers typical use cases, it might not fit your needs. Check out the [limitations](#limitations) before you dive in.

_Note: Doubleclick for Publishers (DFP) was recently renamed to Google Ad Manager (GAM), so this repository may refer to GAM as DFP._

## Getting Started

### Requirements
* Python version >= 3.6 and a basic knowledge of Python
* Access to create a service account in the Google Developers Console
* Admin access to your Google Ad Manager account

### Creating Google Credentials
_You will need credentials to access your GAM account programmatically. This summarizes steps from [GAM docs](https://developers.google.com/ad-manager/docs/authentication) and the Google Ads Python libary [auth guide](https://github.com/googleads/googleads-python-lib)._

1. If you haven't yet, sign up for a [GAM account](https://admanager.google.com/).
2. Create Google developer credentials
   * Go to the [Google Developers Console Credentials page](https://console.developers.google.com/apis/credentials).
   * On the **Credentials** page, select **Create credentials**, then select **Service account key**.
   * Select **New service account**, and select JSON key type. You can leave the role blank.
   * Click **Create** to download a file containing a `.json` private key.
3. Enable API access to GAM
   * Sign into your [GAM account](https://admanager.google.com/). You must have admin rights.
   * In the **Admin** section, select **Global settings**
   * Ensure that **API access** is enabled.
   * Click the **Add a service account user** button.
     * Use the service account email for the Google developer credentials you created above.
     * Set the role to "Administrator".
     * Click **Save**.

### Setting Up

#### Pre-requisites
* Installing Python. Python version 3.6 or higher is required.
* Installing pip. 

#### Steps
1. Clone this repository.
2. Install Python dependencies
   * Run `pip install -r requirements.txt`
3. Rename key
   * Rename the Google credentials key you previously downloaded (`[something].json`) to `key.json` and move it to the root of this repository
4. Make a copy of `googleads.example.yaml` and name it `googleads.yaml`.
5. In `googleads.yaml`, set the required fields:
   * `application_name` is the name of the Google project you created when creating the service account credentials. It should appear in the top-left of the [credentials page](https://console.developers.google.com/apis/credentials).
   * `network_code` is your GAM network number; e.g., for `https://admanager.google.com/12398712#delivery`, the network code is `12398712`.

### Verifying Setup
Let's try it out! From the top level directory, run

`python -m dfp.get_orders`

and you should see all of the orders in your GAM account.

## Creating Line Items for OpenWrap

Modify the following mandatory settings in `settings.py`:

Setting | Description | Type
------------ | ------------- | -------------
`DFP_ORDER_NAME` | What you want to call your new GAM order | string
`DFP_USER_EMAIL_ADDRESS` | The email of the GAM user who will be the trafficker for the created order | string
`DFP_ADVERTISER_NAME` | The name of the GAM advertiser for the created order | string
`DFP_TARGETED_PLACEMENT_NAMES` | The names of GAM placements the line items should target.  Use empty array for `Run Of Network` | array of strings
`DFP_PLACEMENT_SIZES` | The creative sizes for the targeted placements | array of objects (e.g., `[{'width': '728', 'height': '90'}]`)
`PREBID_BIDDER_CODE` | The value of [`pwtpid`](https://github.com/PubMatic/OpenWrap#wrapper-keys-sent-to-dfp) for this partner.  Set to `None` to generate line items for all partners.  Use array of strings if the line should match multiple partners | string or array of strings.
`OPENWRAP_CREATIVE_TYPE` | Which type of creative to use.  Options are WEB, WEB_SAFEFRAME, AMP, IN_APP | string
`OPENWRAP_BUCKET_CSV` | CSV that that list buckets and price granularity; used to set `pwtecp` targeting for each line item | string

Then, from the root of the repository, run:

`python -m tasks.add_new_openwrap_partner`

You should be all set! Review your order, line items, and creatives to make sure they are correct. Then, approve the order in DFP.

*Note: GAM might show a "Needs creatives" warning on the order for ~15 minutes after order creation. Typically, the warning is incorrect and will disappear on its own.*

## Additional optional settings

Setting | Description | Type | Default
------------ | ------------- | ------------- | -------------
`DFP_CREATE_ADVERTISER_IF_DOES_NOT_EXIST` | Whether we should create the advertiser with `DFP_ADVERTISER_NAME` in GAM if it does not exist | bool | `False`
`DFP_USE_EXISTING_ORDER_IF_EXISTS` | Whether we should modify an existing order if one already exists with name `DFP_ORDER_NAME` | bool | `False`
`DFP_NUM_CREATIVES_PER_LINE_ITEM` | The number of duplicate creatives to attach to each line item. Due to GAM limitations, this should be equal to or greater than the number of ad units you serve on a given page. | int | the length of setting `DFP_TARGETED_PLACEMENT_NAMES`
`DFP_CURRENCY_CODE` | The currency to use in line items | string | `'USD'`
`DFP_SAME_ADV_EXCEPTION` | Whether to set the "Same Advertiser Exception" on line items. Currently it only works for OpenWrap | bool | `False`
`DFP_DEVICE_CATEGORIES` | Sets device category targetting for a Line item. Valid Values are: 'Connected TV', 'Desktop', 'Feature Phone', 'Set Top Box', 'Smartphone', 'Tablet' | string or array of string | None
`DFP_ROADBLOCK_TYPE` |This option is equivalent to 'Display Creatives' in old LI tool. Valid values are: 'ONE_OR_MORE', 'AS_MANY_AS_POSSIBLE' | string | None
`LINE_ITEM_PREFIX` | The prefix to be added in line-item name | string | None
`OPENWRAP_CUSTOM_TARGETING` | Array of additional targeting rules per line item | array of arrays e.g.: `[("a", "IS", ("1", "2", "3")), ("b", "IS_NOT", ("4", "5", "6"))]` | None
`CURRENCY_EXCHANGE` | This option is equivalent to 'Currency Module' in old LI tool. This option if set, will convert the rate to network's currency equivalent | bool | `False`


## Creating Line Items for Prebid

Modify the following settings in `settings.py`:

Setting | Description | Type
------------ | ------------- | -------------
`DFP_ORDER_NAME` | What you want to call your new GAM order | string
`DFP_USER_EMAIL_ADDRESS` | The email of the GAM user who will be the trafficker for the created order | string
`DFP_ADVERTISER_NAME` | The name of the GAM advertiser for the created order | string
`DFP_TARGETED_AD_UNIT_NAMES` | The names of GAM ad units the line items should target | array of strings
`DFP_TARGETED_PLACEMENT_NAMES` | The names of GAM placements the line items should target | array of strings
`DFP_PLACEMENT_SIZES` | The creative sizes for the targeted placements | array of objects (e.g., `[{'width': '728', 'height': '90'}]`)
`PREBID_BIDDER_CODE` | The value of [`hb_bidder`](http://prebid.org/dev-docs/publisher-api-reference.html#module_pbjs.bidderSettings) for this partner | string
`PREBID_PRICE_BUCKETS` | The [price granularity](http://prebid.org/dev-docs/publisher-api-reference.html#module_pbjs.setPriceGranularity); used to set `hb_pb` for each line item | object

Then, from the root of the repository, run:

`python -m tasks.add_new_prebid_partner`

You should be all set! Review your order, line items, and creatives to make sure they are correct. Then, approve the order in GAM.

*Note: GAM might show a "Needs creatives" warning on the order for ~15 minutes after order creation. Typically, the warning is incorrect and will disappear on its own.*

## Additional Settings

In most cases, you won't need to modify these settings.

Setting | Description | Default
------------ | ------------- | -------------
`DFP_CREATE_ADVERTISER_IF_DOES_NOT_EXIST` | Whether we should create the advertiser with `DFP_ADVERTISER_NAME` in GAM if it does not exist | `False`
`DFP_USE_EXISTING_ORDER_IF_EXISTS` | Whether we should modify an existing order if one already exists with name `DFP_ORDER_NAME` | `False`
`DFP_NUM_CREATIVES_PER_LINE_ITEM` | The number of duplicate creatives to attach to each line item. Due to GAM limitations, this should be equal to or greater than the number of ad units you serve on a given page. | the length of setting `DFP_TARGETED_PLACEMENT_NAMES`
`DFP_CURRENCY_CODE` | The currency to use in line items. | `'USD'`
`DFP_LINE_ITEM_FORMAT` | The format for the line item names. | `u'{bidder_code}: HB ${price}'`

## Limitations

* This tool does not modify existing orders or line items, it only creates them. If you need to make a change to an order, it's easiest to archive the existing order and recreate it. But you can add new line items in the exisiting order if the flag DFP_USE_EXISTING_ORDER_IF_EXISTS is set.
