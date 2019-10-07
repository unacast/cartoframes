import pytest

from cartoframes.data.observatory.repository.category_repo import \
    CategoryRepository
from cartoframes.data.observatory.repository.repo_client import RepoClient
from cartoframes.exceptions import DiscoveryException

from ..examples import (db_category1, db_category2, test_categories,
                        test_category1)

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


class TestCategoryRepo(object):

    @patch.object(RepoClient, 'get_categories')
    def test_get_all(self, mocked_repo):
        # Given
        mocked_repo.return_value = [db_category1, db_category2]
        repo = CategoryRepository()

        # When
        categories = repo.get_all()

        # Then
        mocked_repo.assert_called_once_with()
        assert categories == test_categories

        id1 = db_category1['id']
        assert categories.loc[id1] == test_category1

    @patch.object(RepoClient, 'get_categories')
    def test_get_all_when_empty(self, mocked_repo):
        # Given
        mocked_repo.return_value = []
        repo = CategoryRepository()

        # When
        categories = repo.get_all()

        # Then
        mocked_repo.assert_called_once_with()
        assert categories is None

    @patch.object(RepoClient, 'get_categories')
    def test_get_by_id(self, mocked_repo):
        # Given
        mocked_repo.return_value = [db_category1, db_category2]
        requested_id = test_category1['id']
        repo = CategoryRepository()

        # When
        category = repo.get_by_id(requested_id)

        # Then
        mocked_repo.assert_called_once_with('id', requested_id)
        assert category == test_category1

    @patch.object(RepoClient, 'get_categories')
    def test_get_by_id_unknown_fails(self, mocked_repo):
        # Given
        mocked_repo.return_value = []
        requested_id = 'unknown_id'
        repo = CategoryRepository()

        # Then
        with pytest.raises(DiscoveryException):
            repo.get_by_id(requested_id)
