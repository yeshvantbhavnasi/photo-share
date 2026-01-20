"""
Unit tests for Lambda index.py - main handler and helper functions
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal
import base64


class TestGetUserIdFromEvent:
    """Tests for get_user_id_from_event function"""

    def test_extracts_user_id_from_jwt_claims(self):
        """Should extract user ID from HTTP API JWT authorizer claims"""
        from index import get_user_id_from_event

        event = {
            'requestContext': {
                'authorizer': {
                    'jwt': {
                        'claims': {
                            'sub': 'user-abc-123'
                        }
                    }
                }
            }
        }

        result = get_user_id_from_event(event)
        assert result == 'user-abc-123'

    def test_extracts_user_id_from_rest_api_claims(self):
        """Should extract user ID from REST API Cognito authorizer claims"""
        from index import get_user_id_from_event

        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-xyz-789'
                    }
                }
            }
        }

        result = get_user_id_from_event(event)
        assert result == 'user-xyz-789'

    def test_decodes_jwt_from_authorization_header(self):
        """Should decode JWT token from Authorization header"""
        from index import get_user_id_from_event

        # Create a valid JWT token
        header = {'alg': 'RS256'}
        payload = {'sub': 'decoded-user-id'}

        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        token = f"{header_b64}.{payload_b64}.signature"

        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            },
            'requestContext': {}
        }

        result = get_user_id_from_event(event)
        assert result == 'decoded-user-id'

    def test_handles_lowercase_authorization_header(self):
        """Should handle lowercase 'authorization' header"""
        from index import get_user_id_from_event

        header = {'alg': 'RS256'}
        payload = {'sub': 'lowercase-header-user'}

        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        token = f"{header_b64}.{payload_b64}.signature"

        event = {
            'headers': {
                'authorization': f'Bearer {token}'
            },
            'requestContext': {}
        }

        result = get_user_id_from_event(event)
        assert result == 'lowercase-header-user'

    def test_returns_none_for_missing_auth(self):
        """Should return None when no authentication is present"""
        from index import get_user_id_from_event

        event = {
            'headers': {},
            'requestContext': {}
        }

        result = get_user_id_from_event(event)
        assert result is None

    def test_returns_none_for_invalid_token(self):
        """Should return None for invalid JWT token"""
        from index import get_user_id_from_event

        event = {
            'headers': {
                'Authorization': 'Bearer invalid.token'
            },
            'requestContext': {}
        }

        result = get_user_id_from_event(event)
        assert result is None


class TestIsPhotoVisible:
    """Tests for is_photo_visible function"""

    def test_visible_photo_returns_true(self, sample_photo):
        """Should return True for a visible photo"""
        from index import is_photo_visible

        result = is_photo_visible(sample_photo)
        assert result is True

    def test_hidden_photo_returns_false(self, sample_photo):
        """Should return False for a hidden photo"""
        from index import is_photo_visible

        sample_photo['hidden'] = True
        result = is_photo_visible(sample_photo)
        assert result is False

    def test_metadata_file_returns_false(self, sample_photo):
        """Should return False for macOS metadata files"""
        from index import is_photo_visible

        sample_photo['filename'] = '.DS_Store'
        result = is_photo_visible(sample_photo)
        assert result is False

    def test_non_photo_sk_returns_false(self, sample_photo):
        """Should return False for non-PHOTO# sort keys"""
        from index import is_photo_visible

        sample_photo['sk'] = 'ALBUM#album-001'
        result = is_photo_visible(sample_photo)
        assert result is False


class TestCorsResponse:
    """Tests for cors_response function"""

    def test_returns_correct_status_code(self):
        """Should return the specified status code"""
        from index import cors_response

        response = cors_response(200, {'message': 'OK'})
        assert response['statusCode'] == 200

    def test_includes_cors_headers(self):
        """Should include CORS headers"""
        from index import cors_response

        response = cors_response(200, {})
        headers = response['headers']

        assert headers['Access-Control-Allow-Origin'] == '*'
        assert 'Authorization' in headers['Access-Control-Allow-Headers']
        assert 'GET' in headers['Access-Control-Allow-Methods']

    def test_serializes_decimal_values(self):
        """Should properly serialize Decimal values"""
        from index import cors_response

        body = {'count': Decimal(42), 'price': Decimal('19.99')}
        response = cors_response(200, body)
        parsed = json.loads(response['body'])

        assert parsed['count'] == 42
        assert parsed['price'] == 19.99


class TestCreateAlbumIfNotExists:
    """Tests for create_album_if_not_exists function"""

    @patch('index.photos_table')
    def test_creates_new_album(self, mock_table):
        """Should create a new album when it doesn't exist"""
        from index import create_album_if_not_exists

        mock_table.get_item.return_value = {}

        result = create_album_if_not_exists('new-album', 'My Album', 'user-123')

        assert result is True
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]['Item']
        assert call_args['albumId'] == 'new-album'
        assert call_args['name'] == 'My Album'

    @patch('index.photos_table')
    def test_returns_false_for_existing_album(self, mock_table):
        """Should return False when album already exists"""
        from index import create_album_if_not_exists

        mock_table.get_item.return_value = {
            'Item': {
                'pk': 'USER#user-123',
                'sk': 'ALBUM#existing-album'
            }
        }

        result = create_album_if_not_exists('existing-album', 'My Album', 'user-123')

        assert result is False
        mock_table.put_item.assert_not_called()


class TestGetAlbums:
    """Tests for get_albums function"""

    @patch('index.photos_table')
    @patch('index.get_first_valid_photo')
    def test_returns_albums_for_user(self, mock_cover, mock_table):
        """Should return all albums for a user"""
        from index import get_albums

        mock_table.query.side_effect = [
            # First call: get user's albums
            {
                'Items': [
                    {
                        'pk': 'USER#user-123',
                        'sk': 'ALBUM#album-1',
                        'name': 'Album 1',
                        'createdAt': '2024-01-15T10:00:00Z'
                    },
                    {
                        'pk': 'USER#user-123',
                        'sk': 'ALBUM#album-2',
                        'name': 'Album 2',
                        'createdAt': '2024-01-16T10:00:00Z'
                    }
                ]
            },
            # Second and third calls: count photos in each album
            {'Items': [{'sk': 'PHOTO#p1'}, {'sk': 'PHOTO#p2'}]},
            {'Items': [{'sk': 'PHOTO#p3'}]}
        ]
        mock_cover.return_value = 'https://test.cloudfront.net/thumb.jpg'

        result = get_albums(user_id='user-123')

        assert len(result) == 2
        assert result[0]['id'] == 'album-2'  # Sorted by date, newest first
        assert result[1]['id'] == 'album-1'


class TestValidateShareLink:
    """Tests for validate_share_link function"""

    @patch('index.share_links_table')
    @patch('index.get_album_photos')
    def test_valid_share_link(self, mock_get_photos, mock_table):
        """Should return album data for valid share link"""
        from index import validate_share_link

        mock_table.get_item.return_value = {
            'Item': {
                'linkId': 'valid-token',
                'albumId': 'album-001',
                'accessCount': Decimal(5)
            }
        }
        mock_get_photos.return_value = {
            'albumId': 'album-001',
            'photos': []
        }

        album_data, error = validate_share_link('valid-token')

        assert error is None
        assert album_data['albumId'] == 'album-001'
        assert 'shareLink' in album_data
        mock_table.update_item.assert_called()  # Access count incremented

    @patch('index.share_links_table')
    def test_invalid_share_link(self, mock_table):
        """Should return error for invalid share link"""
        from index import validate_share_link

        mock_table.get_item.return_value = {}

        album_data, error = validate_share_link('invalid-token')

        assert album_data is None
        assert error == 'Invalid share link'

    @patch('index.share_links_table')
    def test_expired_share_link(self, mock_table):
        """Should return error for expired share link"""
        from index import validate_share_link

        mock_table.get_item.return_value = {
            'Item': {
                'linkId': 'expired-token',
                'albumId': 'album-001',
                'expiresAt': '2020-01-01T00:00:00Z'  # Expired date
            }
        }

        album_data, error = validate_share_link('expired-token')

        assert album_data is None
        assert 'expired' in error.lower()


class TestHidePhoto:
    """Tests for hide_photo function"""

    @patch('index.photos_table')
    def test_hides_existing_photo(self, mock_table):
        """Should hide an existing photo"""
        from index import hide_photo

        mock_table.scan.return_value = {
            'Items': [{
                'pk': 'ALBUM#album-001',
                'sk': 'PHOTO#photo-001',
                'photoId': 'photo-001'
            }]
        }
        mock_table.query.return_value = {'Items': []}

        result = hide_photo('photo-001', 'user-123')

        assert result['photoId'] == 'photo-001'
        assert result['hidden'] is True
        mock_table.update_item.assert_called()

    @patch('index.photos_table')
    def test_raises_error_for_missing_photo(self, mock_table):
        """Should raise error when photo not found"""
        from index import hide_photo

        mock_table.scan.return_value = {'Items': []}
        mock_table.query.return_value = {'Items': []}

        with pytest.raises(ValueError, match='Photo not found'):
            hide_photo('nonexistent-photo', 'user-123')


class TestUpdateAlbum:
    """Tests for update_album function"""

    @patch('index.photos_table')
    def test_updates_album_name(self, mock_table):
        """Should update album name"""
        from index import update_album

        mock_table.get_item.return_value = {
            'Item': {
                'pk': 'USER#user-123',
                'sk': 'ALBUM#album-001',
                'name': 'Old Name'
            }
        }

        result = update_album('album-001', {'name': 'New Name'}, 'user-123')

        assert result['updated'] is True
        assert result['name'] == 'New Name'
        mock_table.update_item.assert_called()

    @patch('index.photos_table')
    def test_raises_error_for_missing_album(self, mock_table):
        """Should raise error when album not found"""
        from index import update_album

        mock_table.get_item.return_value = {}

        with pytest.raises(ValueError, match='Album not found'):
            update_album('nonexistent', {'name': 'Test'}, 'user-123')

    @patch('index.photos_table')
    def test_raises_error_for_empty_updates(self, mock_table):
        """Should raise error when no valid updates provided"""
        from index import update_album

        mock_table.get_item.return_value = {
            'Item': {'pk': 'USER#user-123', 'sk': 'ALBUM#album-001'}
        }

        with pytest.raises(ValueError, match='No valid updates'):
            update_album('album-001', {}, 'user-123')


class TestLambdaHandler:
    """Tests for the main lambda_handler function"""

    @patch('index.get_user_id_from_event')
    def test_options_request_returns_cors(self, mock_get_user):
        """Should handle OPTIONS preflight requests"""
        from index import lambda_handler

        event = {'httpMethod': 'OPTIONS', 'path': '/albums'}
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200

    @patch('index.get_user_id_from_event')
    def test_unauthenticated_protected_route_returns_401(self, mock_get_user):
        """Should return 401 for unauthenticated requests to protected routes"""
        from index import lambda_handler

        mock_get_user.return_value = None

        event = {
            'httpMethod': 'GET',
            'path': '/albums',
            'queryStringParameters': {},
            'headers': {}
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 401

    @patch('index.get_user_id_from_event')
    @patch('index.get_albums')
    def test_get_albums_route(self, mock_get_albums, mock_get_user):
        """Should handle GET /albums route"""
        from index import lambda_handler

        mock_get_user.return_value = 'user-123'
        mock_get_albums.return_value = [{'id': 'album-1', 'name': 'Test'}]

        event = {
            'httpMethod': 'GET',
            'path': '/albums',
            'queryStringParameters': {},
            'headers': {'Authorization': 'Bearer token'}
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'albums' in body

    @patch('index.get_user_id_from_event')
    @patch('index.validate_share_link')
    def test_share_link_route_no_auth_required(self, mock_validate, mock_get_user):
        """Should handle share link route without authentication"""
        from index import lambda_handler

        mock_get_user.return_value = None  # Not authenticated
        mock_validate.return_value = ({'albumId': 'album-001', 'photos': []}, None)

        event = {
            'httpMethod': 'GET',
            'path': '/share',
            'queryStringParameters': {'token': 'valid-token'},
            'headers': {}
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200

    @patch('index.get_user_id_from_event')
    def test_unknown_route_returns_404(self, mock_get_user):
        """Should return 404 for unknown routes"""
        from index import lambda_handler

        mock_get_user.return_value = 'user-123'

        event = {
            'httpMethod': 'GET',
            'path': '/unknown/route',
            'queryStringParameters': {},
            'headers': {}
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 404

    @patch('index.get_user_id_from_event')
    @patch('index.create_album_if_not_exists')
    def test_create_album_route(self, mock_create, mock_get_user):
        """Should handle POST /albums route"""
        from index import lambda_handler

        mock_get_user.return_value = 'user-123'
        mock_create.return_value = True

        event = {
            'httpMethod': 'POST',
            'path': '/albums',
            'queryStringParameters': {},
            'headers': {'Authorization': 'Bearer token'},
            'body': json.dumps({'name': 'New Album'})
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['name'] == 'New Album'


class TestGenerateUploadUrls:
    """Tests for generate_upload_urls function"""

    @patch('index.s3')
    def test_generates_presigned_urls(self, mock_s3):
        """Should generate presigned URLs for upload"""
        from index import generate_upload_urls

        mock_s3.generate_presigned_url.return_value = 'https://s3.amazonaws.com/presigned-url'

        result = generate_upload_urls(
            album_id='album-001',
            filename='photo.jpg',
            content_type='image/jpeg',
            user_id='user-123'
        )

        assert 'uploadUrl' in result
        assert 'photoKey' in result
        assert 'photoId' in result
        assert 'thumbnailUploadUrl' in result
        assert 'thumbnailKey' in result


class TestSavePhotoMetadata:
    """Tests for save_photo_metadata function"""

    @patch('index.photos_table')
    def test_saves_photo_and_date_entries(self, mock_table):
        """Should save photo metadata and date index entry"""
        from index import save_photo_metadata

        result = save_photo_metadata(
            album_id='album-001',
            photo_id='photo-001',
            filename='test.jpg',
            s3_key='photos/user/album/photo.jpg',
            thumbnail_key='thumbnails/user/album/photo_thumb.jpg',
            content_type='image/jpeg',
            size=1024,
            user_id='user-123'
        )

        assert result['photoId'] == 'photo-001'
        assert 'url' in result
        assert 'thumbnailUrl' in result
        # Should be called twice: once for photo, once for date index
        assert mock_table.put_item.call_count == 2
