import event_model


def test_documents():
    dn = event_model.DocumentNames
    for k in ('stop', 'start', 'descriptor',
              'event', 'bulk_events', 'datum',
              'resource', 'bulk_datum', 'event_page', 'datum_page'):
        assert dn(k) == getattr(dn, k)


def test_len():
    assert 10 == len(event_model.DocumentNames)


def test_schemas():
    for k in event_model.DocumentNames:
        assert k in event_model.SCHEMA_NAMES
        assert event_model.schemas[k]


def test_compose_run():
    # Compose each kind of document type. These calls will trigger
    # jsonschema.validate and ensure that the document-generation code composes
    # valid documents.
    bundle = event_model.compose_run()
    start_doc, compose_descriptor, compose_resource, compose_stop = bundle
    assert bundle.start_doc is start_doc
    assert bundle.compose_descriptor is compose_descriptor
    assert bundle.compose_resource is compose_resource
    assert bundle.compose_stop is compose_stop
    bundle = compose_descriptor(
        data_keys={'motor': {'shape': [], 'dtype': 'number', 'source': '...'},
                   'image': {'shape': [512, 512], 'dtype': 'number',
                             'source': '...', 'external': 'FILESTORE:'}},
        name='primary')
    descriptor_doc, compose_event = bundle
    assert bundle.descriptor_doc is descriptor_doc
    assert bundle.compose_event is compose_event
    bundle = compose_resource(
        spec='TIFF', root='/tmp', resource_path='stack.tiff',
        resource_kwargs={})
    resource_doc, compose_datum = bundle
    assert bundle.resource_doc is resource_doc
    assert bundle.compose_datum is compose_datum
    datum_doc = compose_datum(datum_kwargs={'slice': 5})
    event_doc = compose_event(
        data={'motor': 0, 'image': datum_doc['datum_id']},
        timestamps={'motor': 0, 'image': 0}, filled={'image': False},
        seq_num=1)
    assert 'descriptor' in event_doc
    compose_stop()


def test_round_trip_pagination():
    run_bundle = event_model.compose_run()
    desc_bundle = run_bundle.compose_descriptor(
        data_keys={'motor': {'shape': [], 'dtype': 'number', 'source': '...'},
                   'image': {'shape': [512, 512], 'dtype': 'number',
                             'source': '...', 'external': 'FILESTORE:'}},
        name='primary')
    res_bundle = run_bundle.compose_resource(
        spec='TIFF', root='/tmp', resource_path='stack.tiff',
        resource_kwargs={})
    datum_doc = res_bundle.compose_datum(datum_kwargs={'slice': 5})
    event_doc = desc_bundle.compose_event(
        data={'motor': 0, 'image': datum_doc['datum_id']},
        timestamps={'motor': 0, 'image': 0}, filled={'image': False},
        seq_num=1)

    # Round trip event -> event_page -> event.
    expected = event_doc
    actual = event_model.unpack_event_page_into_event(
        event_model.pack_event_into_event_page(expected))
    assert actual == expected

    # Round trip datum -> datum_page -> datum.
    expected = datum_doc
    actual = event_model.unpack_datum_page_into_datum(
        event_model.pack_datum_into_datum_page(expected))
    assert actual == expected


def test_bulk_events_to_event_page():
