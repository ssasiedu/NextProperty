# -*- coding: utf-8 -*-
"""Pluggable OTA adapter interface (middleware/API client pattern).

Each adapter implements `push_availability` and `push_rates` against one
OTA's real API. Adding a new OTA means writing one new adapter class and
registering it in ADAPTER_REGISTRY - no change to next_ota_channel.py or
the availability-ledger/booking logic is needed.

ASSUMPTION (stated per the brief, since no specific channel-manager API was
named): these ship as sandbox/mock adapters that log the payload instead of
calling a real endpoint, so the module installs and the sync cron runs
cleanly out of the box. Swap `BaseOtaAdapter._http_post` usage in a real
subclass for the actual Airbnb/Expedia/Booking.com API calls when
credentials are available.
"""
import logging

_logger = logging.getLogger(__name__)


class BaseOtaAdapter:
    def __init__(self, channel):
        self.channel = channel  # next.ota.channel recordset (singleton)

    def push_availability(self, availability_by_room):
        raise NotImplementedError

    def push_rates(self, rates_by_room_type):
        raise NotImplementedError

    def _http_post(self, url, payload):
        import requests
        return requests.post(url, json=payload, headers={
            'Authorization': 'Bearer %s' % self.channel.api_key,
        }, timeout=15)


class AirbnbAdapter(BaseOtaAdapter):
    def push_availability(self, availability_by_room):
        _logger.info('[Airbnb sandbox] push_availability for %s: %s rooms',
                      self.channel.external_listing_id, len(availability_by_room))

    def push_rates(self, rates_by_room_type):
        _logger.info('[Airbnb sandbox] push_rates for %s: %s room types',
                      self.channel.external_listing_id, len(rates_by_room_type))


class ExpediaAdapter(BaseOtaAdapter):
    def push_availability(self, availability_by_room):
        _logger.info('[Expedia sandbox] push_availability for %s: %s rooms',
                      self.channel.external_listing_id, len(availability_by_room))

    def push_rates(self, rates_by_room_type):
        _logger.info('[Expedia sandbox] push_rates for %s: %s room types',
                      self.channel.external_listing_id, len(rates_by_room_type))


class BookingComAdapter(BaseOtaAdapter):
    def push_availability(self, availability_by_room):
        _logger.info('[Booking.com sandbox] push_availability for %s: %s rooms',
                      self.channel.external_listing_id, len(availability_by_room))

    def push_rates(self, rates_by_room_type):
        _logger.info('[Booking.com sandbox] push_rates for %s: %s room types',
                      self.channel.external_listing_id, len(rates_by_room_type))


ADAPTER_REGISTRY = {
    'airbnb': AirbnbAdapter,
    'expedia': ExpediaAdapter,
    'booking_com': BookingComAdapter,
}


def get_adapter_class(channel_type):
    return ADAPTER_REGISTRY[channel_type]
