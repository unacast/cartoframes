import unittest

from cartoframes.data.clients.auth_api_client import AuthAPIClient
from cartoframes.data import Dataset


try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

TOKEN_MOCK = '1234'


class APIKeyMock():
    def __init__(self, name):
        self.name = name
        self.token = TOKEN_MOCK
        self.type = None
        self.created_at = None
        self.updated_at = None
        self.grants = None


class APIKeyManagerMock():
    def create(self, name, **kwargs):
        return APIKeyMock(name)


class TestSQLClient(unittest.TestCase):
    @patch('cartoframes.data.clients.auth_api_client._get_api_key_manager')
    def test_instantiation(self, get_api_key_manager_mock):
        get_api_key_manager_mock.return_value = APIKeyManagerMock()

        auth_api_client = AuthAPIClient()

        assert isinstance(auth_api_client, AuthAPIClient)
        assert isinstance(auth_api_client._api_key_manager, APIKeyManagerMock)

    @patch('cartoframes.data.clients.auth_api_client._get_api_key_manager')
    def test_create_api_key(self, get_api_key_manager_mock):
        get_api_key_manager_mock.return_value = APIKeyManagerMock()

        dataset = Dataset('fake_table')
        api_key_name = 'fake_name'

        auth_api_client = AuthAPIClient()
        token = auth_api_client.create_api_key([dataset], api_key_name)

        assert token == TOKEN_MOCK

    @patch('cartoframes.data.clients.auth_api_client._get_api_key_manager')
    def test_create_api_key_several_datasets(self, get_api_key_manager_mock):
        get_api_key_manager_mock.return_value = APIKeyManagerMock()

        dataset = Dataset('fake_table')
        api_key_name = 'fake_name'

        auth_api_client = AuthAPIClient()
        token = auth_api_client.create_api_key([dataset, dataset, dataset], api_key_name)

        assert token == TOKEN_MOCK
