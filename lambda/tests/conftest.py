"""
Pytest fixtures and configuration for Lambda unit tests
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal

# Add lambda directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables before importing modules
# AWS_DEFAULT_REGION must be set before boto3 initializes
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['PHOTOS_TABLE'] = 'TestPhotosTable'
os.environ['SHARE_LINKS_TABLE'] = 'TestShareLinks'
os.environ['PHOTOS_BUCKET'] = 'test-photos-bucket'
os.environ['CLOUDFRONT_DOMAIN'] = 'test.cloudfront.net'
os.environ['RATE_LIMITING_ENABLED'] = 'false'


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB resource and tables"""
    with patch('boto3.resource') as mock_resource:
        mock_db = MagicMock()
        mock_resource.return_value = mock_db

        # Create mock tables
        mock_photos_table = MagicMock()
        mock_share_links_table = MagicMock()

        def get_table(table_name):
            if 'Photos' in table_name or table_name == 'TestPhotosTable':
                return mock_photos_table
            elif 'ShareLinks' in table_name or table_name == 'TestShareLinks':
                return mock_share_links_table
            return MagicMock()

        mock_db.Table.side_effect = get_table

        yield {
            'resource': mock_db,
            'photos_table': mock_photos_table,
            'share_links_table': mock_share_links_table
        }


@pytest.fixture
def mock_s3():
    """Mock S3 client"""
    with patch('boto3.client') as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        yield mock_s3


@pytest.fixture
def sample_jwt_token():
    """Generate a sample JWT token for testing"""
    import base64
    import json

    header = {'alg': 'RS256', 'typ': 'JWT'}
    payload = {
        'sub': 'test-user-123',
        'email': 'test@example.com',
        'iat': 1700000000,
        'exp': 1700086400
    }

    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    signature = 'fake_signature'

    return f"{header_b64}.{payload_b64}.{signature}"


@pytest.fixture
def sample_event():
    """Base API Gateway event structure"""
    return {
        'httpMethod': 'GET',
        'path': '/albums',
        'queryStringParameters': {},
        'headers': {},
        'body': None,
        'requestContext': {
            'authorizer': {
                'jwt': {
                    'claims': {}
                }
            }
        }
    }


@pytest.fixture
def authenticated_event(sample_event, sample_jwt_token):
    """API Gateway event with authentication"""
    event = sample_event.copy()
    event['headers'] = {
        'Authorization': f'Bearer {sample_jwt_token}'
    }
    event['requestContext'] = {
        'authorizer': {
            'jwt': {
                'claims': {
                    'sub': 'test-user-123',
                    'email': 'test@example.com'
                }
            }
        }
    }
    return event


@pytest.fixture
def sample_album():
    """Sample album data"""
    return {
        'pk': 'USER#test-user-123',
        'sk': 'ALBUM#album-001',
        'albumId': 'album-001',
        'name': 'Test Album',
        'userId': 'test-user-123',
        'createdAt': '2024-01-15T10:00:00Z'
    }


@pytest.fixture
def sample_photo():
    """Sample photo data"""
    return {
        'pk': 'ALBUM#album-001',
        'sk': 'PHOTO#photo-001',
        'photoId': 'photo-001',
        'albumId': 'album-001',
        'filename': 'test-photo.jpg',
        's3Key': 'photos/test-user-123/album-001/photo-001.jpg',
        'thumbnailKey': 'thumbnails/test-user-123/album-001/photo-001_thumb.jpg',
        'contentType': 'image/jpeg',
        'size': Decimal(1024000),
        'uploadDate': '2024-01-15T10:30:00Z',
        'hidden': False
    }


@pytest.fixture
def sample_share_link():
    """Sample share link data"""
    return {
        'linkId': 'abc12345-xyz',
        'albumId': 'album-001',
        'userId': 'test-user-123',
        'createdBy': 'test-user-123',
        'createdAt': '2024-01-15T12:00:00Z',
        'accessCount': Decimal(5)
    }


@pytest.fixture
def sample_image_bytes():
    """Create a simple test image as bytes"""
    from io import BytesIO
    from PIL import Image

    # Create a simple 100x100 red image
    img = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer.getvalue()
