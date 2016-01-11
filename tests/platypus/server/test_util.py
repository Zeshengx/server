import platypus.server.util
import six
from unittest import TestCase


class UtilTest(TestCase):
    def test_merge(self):

        # Create test datasets to use in the merge operation.
        A = {
            "m0": {"type": "HobbyKing"},
            "m1": {
                "v": 1.0,
                "type": "HobbyKing",
                "enabled": False
            },
            "m2": "test_motor",
            "s0": "test_sensor"
        }

        B = {
            "m0": {"v": 2.0},
            "m1": {
                "v": 3.0,
                "enabled": None,
                "comment": "test_attr"
            },
            "s0": None,
            "s1": {"type": "sensor"}
        }

        # Merge B into A using utility function.
        platypus.server.util.merge(A, B)

        # Make sure the correct keys are in the result.
        self.assertEqual(A["m0"]["type"], "HobbyKing")
        self.assertEqual(A["m0"]["v"], 2.0)

        self.assertEqual(A["m1"]["v"], 3.0)
        self.assertEqual(A["m1"]["type"], "HobbyKing")
        self.assertNotIn("enabled", A["m1"])
        self.assertEqual(A["m1"]["comment"], "test_attr")

        self.assertEqual(A["m2"], "test_motor")
        self.assertNotIn("s0", A)

        self.assertEqual(A["s1"]["type"], "sensor")

    def test_ObservableDict(self):
        # Initial data to use within the controller.
        data = {
            "m0": {"type": "HobbyKing"},
            "m1": {
                "v": 1.0,
                "type": "SeaKing",
                "enabled": False,
                "meta": {
                    "min": 0.0,
                    "max": 1.0
                }
            },
            "m2": "test_motor",
            "s0": "test_sensor"
        }

        # Create the controller object.
        c = platypus.server.util.ObservableDict(entries=data)

        # Check that initial data is accessible.
        six.assertCountEqual(self, c.keys(), ('m0', 'm1', 'm2', 's0'))

        six.assertCountEqual(self, c['m0'].keys(), ('type',))
        self.assertEqual(c['m0']['type'], 'HobbyKing')

        six.assertCountEqual(self, c['m1'].keys(), ('v', 'type', 'enabled', 'meta'))
        self.assertEqual(c['m1']['v'], 1.0)
        self.assertEqual(c['m1']['type'], 'SeaKing')
        self.assertEqual(c['m1']['enabled'], False)
        self.assertEqual(c['m1']['meta']['min'], 0.0)
        self.assertEqual(c['m1']['meta']['max'], 1.0)

        self.assertEqual(c['m2'], 'test_motor')
        self.assertEqual(c['s0'], 'test_sensor')

        # Create observers and try to change some data.
        base_was_updated = [False]
        leaf_was_updated = [False]
        should_not_be_updated = [False]

        def base_observer(key, old_value, new_value):
            base_was_updated[0] = True
            self.assertEqual(key, ('m1', 'meta', 'min'))
            self.assertEqual(old_value, 0.0)
            self.assertEqual(new_value, -1.0)

        def leaf_observer(key, old_value, new_value):
            leaf_was_updated[0] = True
            self.assertEqual(key, ('min',))
            self.assertEqual(old_value, 0.0)
            self.assertEqual(new_value, -1.0)

        def unobserver(key, old_value, new_value):
            self.fail("This observer should not have been called.")

        c.observe('m1', base_observer)
        c['m1']['meta'].observe('min', leaf_observer)
        c.observe('m1', unobserver)
        c.unobserve('m1', unobserver)

        # Change the value using the merge mechanism.
        c.merge({'m1': {'meta': {'min': -1.0}}})

        self.assertEqual(c['m1']['meta']['min'], -1.0)
        self.assertTrue(base_was_updated[0])
        self.assertTrue(leaf_was_updated[0])
        self.assertFalse(should_not_be_updated[0])

        # Reset the observer flags.
        base_was_updated = [False]
        leaf_was_updated = [False]
        should_not_be_updated = [False]
