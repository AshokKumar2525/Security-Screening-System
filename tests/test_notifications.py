import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from message import send_email, send_sms, send_call

class TestNotificationSending(unittest.TestCase):
    
    @patch('message.smtplib.SMTP')
    @patch('message.MIMEImage')
    @patch('message.cv2.imencode', return_value=(True, np.ones((1, 2), dtype=np.uint8)))
    def test_send_email(self, mock_imencode, mock_mimeimage, mock_smtp):
        try:
            # Frame is None, but cv2.imencode is mocked
            send_email('Test', None, 0.99)
        except Exception as e:
            self.fail(f"send_email raised Exception unexpectedly: {e}")
        self.assertTrue(mock_smtp.called)
        self.assertTrue(mock_mimeimage.called)
        self.assertTrue(mock_imencode.called)

    @patch('message.client', autospec=True)
    def test_send_sms(self, mock_client):
        mock_client.messages.create.return_value = MagicMock()
        try:
            send_sms('Test', 0.99)
        except Exception as e:
            self.fail(f"send_sms raised Exception unexpectedly: {e}")
        self.assertTrue(mock_client.messages.create.called)

    @patch('message.client', autospec=True)
    def test_send_call(self, mock_client):
        mock_client.calls.create.return_value = MagicMock()
        try:
            send_call('Test', 0.99)
        except Exception as e:
            self.fail(f"send_call raised Exception unexpectedly: {e}")
        self.assertTrue(mock_client.calls.create.called)


if __name__ == '__main__':
    unittest.main()
