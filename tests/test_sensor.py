import json
from unittest import TestCase

from custom_components.ferroamp.sensor import IntValFerroampSensor


class TestIntValFerroampSensor(TestCase):
    def setUp(self):
        self.sensor = IntValFerroampSensor("Test", "soc", "PERCENTAGE", "mdi:battery", "id", "name", 30, 'config')

    def test_update_state_from_event(self):
        event = json.loads("{ \"soc\": { \"val\": \"90.00\"}}")
        self.sensor.update_state_from_events([event])

        self.assertEqual(90, self.sensor.state)
