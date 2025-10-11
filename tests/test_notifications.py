import unittest
from unittest.mock import patch, MagicMock
from message import send_email, send_sms, send_call

class TestNotificationSending(unittest.TestCase):
    @patch('message.smtplib.SMTP')
    def test_send_email(self, mock_smtp):
        # Should not raise error
        try:
            send_email('Test', None, 0.99)
        except Exception as e:
            self.fail(f"send_email raised Exception unexpectedly: {e}")
        self.assertTrue(mock_smtp.called)

    @patch('message.Client')
    def test_send_sms(self, mock_client):
        try:
            send_sms('Test', 0.99)
        except Exception as e:
            self.fail(f"send_sms raised Exception unexpectedly: {e}")
        self.assertTrue(mock_client.called)

    @patch('message.Client')
    def test_send_call(self, mock_client):
        try:
            send_call('Test', 0.99)
        except Exception as e:
            self.fail(f"send_call raised Exception unexpectedly: {e}")
        self.assertTrue(mock_client.called)

if __name__ == '__main__':
    unittest.main()
