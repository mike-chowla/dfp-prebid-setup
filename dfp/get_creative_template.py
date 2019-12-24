def get_creative_template_id(template_names):

    dfp_client = get_client()
    # Initialize appropriate service.
    creative_template_service = dfp_client.GetService(
      'CreativeTemplateService', version='v201911')

     # Create a statement to select creative templates.
    statement = ad_manager.StatementBuilder(version='v201911')

    # Retrieve a small amount of creative templates at a time, paging
    # through until all creative templates have been retrieved.
    while True:
        response = creative_template_service.getCreativeTemplatesByStatement(
            statement.ToStatement())
        if 'results' in response and len(response['results']):
        for creative_template in response['results']:
            # Print out some information for each creative template.
            print('Creative template with ID "%d" and name "%s" was found.\n' %
                (creative_template['id'], creative_template['name']))
        statement.offset += statement.limit
        else:
        break

    print('\nNumber of results found: %s' % response['totalResultSetSize'])