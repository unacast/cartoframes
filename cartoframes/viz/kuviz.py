from copy import deepcopy
from warnings import warn
import time

from carto.kuvizs import KuvizManager
from carto.exceptions import CartoException

from ..auth import get_default_credentials
from .source import Source
from ..utils.columns import normalize_name
from ..data.clients.auth_api_client import AuthAPIClient

from warnings import filterwarnings
filterwarnings("ignore", category=FutureWarning, module="carto")

DEFAULT_PUBLIC = 'default_public'


class KuvizPublisher(object):
    def __init__(self, credentials=None):
        self.kuviz = None
        self._maps_api_key = DEFAULT_PUBLIC

        self._credentials = credentials or get_default_credentials()
        self._auth_client = _create_auth_client(self._credentials)
        self._layers = []

    @staticmethod
    def all(credentials=None):
        auth_client = _create_auth_client(credentials or get_default_credentials())
        km = _get_kuviz_manager(auth_client)
        kuvizs = km.all()
        return [kuviz_to_dict(kuviz) for kuviz in kuvizs]

    def get_layers(self):
        return self._layers

    def set_layers(self, layers, name, table_name=None):
        self._sync_layers(layers, table_name)
        self._manage_maps_api_key(name)
        self._add_layers_credentials()

    def publish(self, html, name, password=None):
        self.kuviz = _create_kuviz(html=html, name=name, auth_client=self._auth_client, password=password)
        return kuviz_to_dict(self.kuviz)

    def update(self, data, name, password):
        if not self.kuviz:
            raise CartoException('The map has not been published. Use the `publish` method.')

        self.kuviz.data = data
        self.kuviz.name = name
        self.kuviz.password = password
        self.kuviz.save()

        return kuviz_to_dict(self.kuviz)

    def delete(self):
        if self.kuviz:
            self.kuviz.delete()
            warn("Publication '{n}' ({id}) deleted".format(n=self.kuviz.name, id=self.kuviz.id))
            self.kuviz = None
            return True
        return False

    def _sync_layers(self, layers, table_name=None):
        for idx, layer in enumerate(layers):
            if layer.source.dataset.is_local():
                table_name = normalize_name("{name}_{idx}".format(name=table_name, idx=idx))
                layer = self._sync_layer(layer, table_name)
            else:
                layer = deepcopy(layer)
            self._layers.append(layer)

    def _sync_layer(self, layer, table_name):
        layer.source.dataset.upload(table_name=table_name, credentials=self._credentials)
        layer.source = Source(table_name, credentials=self._credentials)
        warn('Table `{}` created. In order to publish the map, you will need to create a new Regular API '
             'key with permissions to Maps API and the table `{}`. You can do it from your CARTO dashboard or '
             'using the Auth API. You can get more info at '
             'https://carto.com/developers/auth-api/guides/types-of-API-Keys/'.format(table_name, table_name))

        return layer

    def _manage_maps_api_key(self, name):
        non_public_datasets = [layer.source.dataset
                               for layer in self._layers
                               if not layer.source.dataset.is_public()]

        if len(non_public_datasets) > 0:
            api_key_name = '{}_{}_api_key'.format(name, int(time.time() * 1000))
            auth_api_client = AuthAPIClient(self._credentials)
            self._maps_api_key = auth_api_client.create_api_key(non_public_datasets, api_key_name, ['maps'])

    def _add_layers_credentials(self):
        for layer in self._layers:
            layer.credentials = {
                'username': layer.source.dataset.credentials.username,
                'api_key': self._maps_api_key,
                'base_url': layer.source.dataset.credentials.base_url
            }


def _create_kuviz(html, name, auth_client, password=None):
    km = _get_kuviz_manager(auth_client)
    return km.create(html=html, name=name, password=password)


def _create_auth_client(credentials):
    return credentials.get_api_key_auth_client()


def _get_kuviz_manager(auth_client):
    return KuvizManager(auth_client)


def kuviz_to_dict(kuviz):
    return {'id': kuviz.id, 'url': kuviz.url, 'name': kuviz.name, 'privacy': kuviz.privacy}
