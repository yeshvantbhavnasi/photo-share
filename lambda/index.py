import json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
photos_table = dynamodb.Table(os.environ.get('PHOTOS_TABLE', 'PhotosMetadata'))
share_links_table = dynamodb.Table(os.environ.get('SHARE_LINKS_TABLE', 'ShareLinks'))

# CloudFront domain for photo URLs
CLOUDFRONT_DOMAIN = os.environ.get('CLOUDFRONT_DOMAIN', 'd1nf5k4wr11svj.cloudfront.net')


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


def cors_response(status_code, body):
    """Return response with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET, OPTIONS'
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }


def get_albums(user_id='default-user'):
    """Get all albums for a user"""
    response = photos_table.query(
        KeyConditionExpression=Key('pk').eq(f'USER#{user_id}') & Key('sk').begins_with('ALBUM#')
    )

    albums = []
    for item in response.get('Items', []):
        album_id = item['sk'].replace('ALBUM#', '')
        # Get cover photo URL if exists
        cover_photo = None
        if item.get('coverPhotoKey'):
            cover_photo = f"https://{CLOUDFRONT_DOMAIN}/{item.get('coverPhotoKey')}"

        albums.append({
            'id': album_id,
            'name': item.get('name', 'Untitled Album'),
            'photoCount': item.get('photoCount', 0),
            'coverPhoto': cover_photo,
            'createdAt': item.get('createdAt')
        })

    # Sort by createdAt descending (newest first)
    albums.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
    return albums


def get_album_photos(album_id, user_id='default-user'):
    """Get all photos for an album"""
    # Get album metadata first
    album_response = photos_table.get_item(
        Key={
            'pk': f'USER#{user_id}',
            'sk': f'ALBUM#{album_id}'
        }
    )
    album_item = album_response.get('Item', {})
    album_name = album_item.get('name', 'Untitled Album')

    # Get photos
    response = photos_table.query(
        KeyConditionExpression=Key('pk').eq(f'ALBUM#{album_id}')
    )

    photos = []
    for item in response.get('Items', []):
        if item['sk'].startswith('PHOTO#'):
            photo_id = item['sk'].replace('PHOTO#', '')
            photos.append({
                'id': photo_id,
                'filename': item.get('filename'),
                'url': f"https://{CLOUDFRONT_DOMAIN}/{item.get('s3Key')}",
                'thumbnailUrl': f"https://{CLOUDFRONT_DOMAIN}/{item.get('thumbnailKey')}" if item.get('thumbnailKey') else None,
                'uploadDate': item.get('uploadDate'),
                'size': item.get('size'),
                'contentType': item.get('contentType')
            })

    # Sort photos by uploadDate
    photos.sort(key=lambda x: x.get('uploadDate', ''))

    return {
        'albumId': album_id,
        'albumName': album_name,
        'photoCount': len(photos),
        'photos': photos
    }


def validate_share_link(token):
    """Validate a share link and return album data if valid"""
    try:
        response = share_links_table.get_item(
            Key={'linkId': token}
        )

        if 'Item' not in response:
            return None, 'Invalid share link'

        item = response['Item']

        # Check if expired
        if item.get('expiresAt'):
            from datetime import datetime
            expires = datetime.fromisoformat(item['expiresAt'].replace('Z', '+00:00'))
            if datetime.now(expires.tzinfo) > expires:
                return None, 'Share link has expired'

        # Update access count
        share_links_table.update_item(
            Key={'linkId': token},
            UpdateExpression='SET accessCount = if_not_exists(accessCount, :zero) + :inc',
            ExpressionAttributeValues={':zero': 0, ':inc': 1}
        )

        # Get album data
        album_data = get_album_photos(item['albumId'])
        album_data['shareLink'] = {
            'token': token,
            'expiresAt': item.get('expiresAt'),
            'accessCount': item.get('accessCount', 0) + 1
        }

        return album_data, None

    except Exception as e:
        return None, str(e)


def lambda_handler(event, context):
    """Main Lambda handler"""

    # Handle OPTIONS for CORS preflight
    http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', 'GET'))
    if http_method == 'OPTIONS':
        return cors_response(200, {})

    # Get path - handle both API Gateway v1 and v2 formats
    path = event.get('path', event.get('rawPath', '/'))
    # Strip stage prefix (e.g., /prod/) from path
    if path.startswith('/prod/'):
        path = path[5:]  # Remove '/prod' prefix
    elif path.startswith('/dev/'):
        path = path[4:]  # Remove '/dev' prefix
    query_params = event.get('queryStringParameters') or {}

    try:
        # Route: GET /albums
        if path == '/albums' or path == '/api/albums':
            albums = get_albums()
            return cors_response(200, {'albums': albums})

        # Route: GET /albums/{id}
        if path.startswith('/albums/') or path.startswith('/api/albums/'):
            album_id = path.split('/')[-1]
            if album_id:
                album_data = get_album_photos(album_id)
                return cors_response(200, album_data)

        # Route: GET /album?id=xxx
        if path == '/album' or path == '/api/album':
            album_id = query_params.get('id')
            if album_id:
                album_data = get_album_photos(album_id)
                return cors_response(200, album_data)
            return cors_response(400, {'error': 'Missing album id'})

        # Route: GET /share/{token} or /share?token=xxx
        if path.startswith('/share') or path.startswith('/api/share'):
            token = query_params.get('token')
            if not token:
                # Try to get token from path
                parts = path.rstrip('/').split('/')
                if len(parts) > 1 and parts[-1] and parts[-1] not in ['share', 'api']:
                    token = parts[-1]

            if token:
                album_data, error = validate_share_link(token)
                if error:
                    return cors_response(404, {'error': error})
                return cors_response(200, album_data)
            return cors_response(400, {'error': 'Missing share token'})

        # Default: return 404
        return cors_response(404, {'error': 'Not found', 'path': path})

    except Exception as e:
        return cors_response(500, {'error': str(e)})
