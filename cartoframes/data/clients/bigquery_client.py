from __future__ import absolute_import

import os
import appdirs
import csv
import tqdm
import pandas as pd

from google.auth.exceptions import RefreshError
from google.cloud import bigquery, storage, bigquery_storage_v1beta1 as bigquery_storage
from google.oauth2.credentials import Credentials as GoogleCredentials

from carto.exceptions import CartoException
from ...auth import get_default_credentials
from ...core.logger import log
from ...utils.utils import timelogger


_USER_CONFIG_DIR = appdirs.user_config_dir('cartoframes')
_GCS_CHUNK_SIZE = 25 * 1024 * 1024  # 25MB. This must be a multiple of 256 KB per the API specification.


def refresh_clients(func):
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except RefreshError:
            self._init_clients()
            try:
                return func(self, *args, **kwargs)
            except RefreshError:
                raise CartoException('Something went wrong accessing data. '
                                     'Please, try again in a few seconds or contact support for help.')
    return wrapper


class BigQueryClient(object):

    def __init__(self, project, credentials):
        self._project = project
        self._credentials = credentials or get_default_credentials()
        self._bucket = 'carto-do-{username}'.format(username=self._credentials.username)

        self.bq_client = None
        self.gcs_client = None
        self.bq_storage_client = None

        self._init_clients()

    def _init_clients(self):
        google_credentials = GoogleCredentials(self._credentials.get_do_token())

        self.bq_client = bigquery.Client(
            project=self._project,
            credentials=google_credentials
        )

        self.gcs_client = storage.Client(
            project=self._project,
            credentials=google_credentials
        )

        self.bq_storage_client = bigquery_storage.BigQueryStorageClient(
            credentials=google_credentials
        )

    @refresh_clients
    def query(self, query, **kwargs):
        return self.bq_client.query(query, **kwargs)

    def upload_dataframe(self, dataframe, schema, tablename, project, dataset):
        self._upload_dataframe_to_GCS(dataframe, tablename)
        self._import_from_GCS_to_BQ(schema, tablename, project, dataset)

    @timelogger
    def download_to_file(self, job, file_path=None, fail_if_exists=False, column_names=None, progress_bar=True):
        if not file_path:
            file_name = '{}.csv'.format(job.job_id)
            file_path = os.path.join(_USER_CONFIG_DIR, file_name)

        if fail_if_exists and os.path.isfile(file_path):
            raise CartoException('The file `{}` already exists.'.format(file_path))

        try:
            rows = self._download_by_bq_storage_api(job)
        except Exception:
            log.debug('Cannot download using BigQuery Storage API, fallback to standard')
            rows = job.result()

        _rows_to_file(rows, file_path, column_names, progress_bar)

        return file_path

    @timelogger
    def download_to_dataframe(self, job):
        try:
            rows = self._download_by_bq_storage_api(job)
            data = list(rows)
            return pd.DataFrame(data)
        except Exception:
            log.debug('Cannot download using BigQuery Storage API, fallback to standard')
            return job.to_dataframe()

    def _download_by_bq_storage_api(self, job):
        table_ref = job.destination.to_bqstorage()

        parent = 'projects/{}'.format(self._project)
        session = self.bq_storage_client.create_read_session(
            table_ref,
            parent,
            requested_streams=1,
            format_=bigquery_storage.enums.DataFormat.AVRO,
            # We use a LIQUID strategy because we only read from a
            # single stream. Consider BALANCED if requested_streams > 1
            sharding_strategy=(bigquery_storage.enums.ShardingStrategy.LIQUID),
        )

        reader = self.bq_storage_client.read_rows(
            bigquery_storage.types.StreamPosition(stream=session.streams[0])
        )

        return reader.rows(session)

    @refresh_clients
    @timelogger
    def _upload_dataframe_to_GCS(self, dataframe, tablename):
        log.debug('Uploading to GCS')

        bucket = self.gcs_client.bucket(self._bucket)
        blob = bucket.blob(tablename, chunk_size=_GCS_CHUNK_SIZE)
        dataframe.to_csv(tablename, index=False, header=False)
        try:
            blob.upload_from_filename(tablename)
        finally:
            os.remove(tablename)

    @refresh_clients
    @timelogger
    def _import_from_GCS_to_BQ(self, schema, tablename, project, dataset):
        log.debug('Importing to BQ from GCS')

        dataset_ref = self.bq_client.dataset(dataset, project=project)
        table_ref = dataset_ref.table(tablename)
        schema_wrapped = [bigquery.SchemaField(column, dtype) for column, dtype in schema.items()]

        job_config = bigquery.LoadJobConfig()
        job_config.schema = schema_wrapped
        job_config.source_format = bigquery.SourceFormat.CSV
        uri = 'gs://{bucket}/{tablename}'.format(bucket=self._bucket, tablename=tablename)

        job = self.bq_client.load_table_from_uri(
            uri, table_ref, job_config=job_config
        )

        job.result()

    def _get_table_column_names(self, project, dataset, table):
        table_info = self._get_table(project, dataset, table)
        return [field.name for field in table_info.schema]

    @refresh_clients
    def _get_table(self, project, dataset, table):
        full_table_name = '{}.{}.{}'.format(project, dataset, table)
        return self.bq_client.get_table(full_table_name)


def _rows_to_file(rows, file_path, column_names=None, progress_bar=True):
    if progress_bar:
        pb = tqdm.tqdm_notebook(total=rows.total_rows)

    with open(file_path, 'w') as csvfile:
        csvwriter = csv.writer(csvfile)

        if column_names:
            csvwriter.writerow(column_names)

        for row in rows:
            csvwriter.writerow(row.values())
            if progress_bar:
                pb.update(1)
