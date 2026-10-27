import unittest
from unittest import mock

from monitor import device as device_mod


class _FakeBulk:
    def __init__(self):
        self.usbdev = object()
        self.released = False

    def release(self):
        self.released = True


class _FakeKraken:
    description = "NZXT Kraken Z53"

    def __init__(self):
        self.bulk_device = _FakeBulk()
        self.disconnected = False

    def disconnect(self):
        self.disconnected = True

    def connect(self):
        pass

    def initialize(self):
        pass

    def set_screen(self, *args):
        pass


class TestDeviceLifecycle(unittest.TestCase):
    def test_close_device_disposes_bulk_usb_handle(self):
        """liquidctl KrakenZ3.disconnect() 只關閉 HID，必須額外釋放 PyUSB bulk handle，否則 fd 洩漏且介面被佔用 (EBUSY)。"""
        dev = _FakeKraken()
        bulk = dev.bulk_device
        with mock.patch.object(device_mod, "_dispose_usb") as dispose:
            device_mod.close_device(dev)
        self.assertTrue(dev.disconnected)
        self.assertTrue(bulk.released)
        dispose.assert_called_once_with(bulk.usbdev)
        self.assertIsNone(dev.bulk_device)

    def test_reconnect_releases_old_bulk_handle(self):
        old = _FakeKraken()
        old_bulk = old.bulk_device
        new = _FakeKraken()
        with mock.patch.object(device_mod, "_dispose_usb") as dispose, \
             mock.patch.object(device_mod, "find_kraken_device", return_value=new), \
             mock.patch.object(device_mod.time, "sleep"):
            result = device_mod.reconnect_device(old)
        self.assertIs(result, new)
        self.assertTrue(old_bulk.released)
        dispose.assert_called_once_with(old_bulk.usbdev)

    def test_close_device_tolerates_errors(self):
        dev = _FakeKraken()
        dev.disconnect = mock.Mock(side_effect=OSError("gone"))
        dev.bulk_device.release = mock.Mock(side_effect=OSError("gone"))
        with mock.patch.object(device_mod, "_dispose_usb", side_effect=OSError("gone")):
            device_mod.close_device(dev)  # must not raise


if __name__ == "__main__":
    unittest.main()
