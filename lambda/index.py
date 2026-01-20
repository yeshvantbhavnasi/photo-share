import json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal

# Import rate limiting and notification modules
try:
    import rate_limiter
    import notification_handler
    RATE_LIMITING_ENABLED = os.environ.get('RATE_LIMITING_ENABLED', 'true').lower() == 'true'
except ImportError as e:
    print(f"Warning: Rate limiting modules not available: {e}")
    RATE_LIMITING_ENABLED = False

# Initialize DynamoDB and S3
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
photos_table = dynamodb.Table(os.environ.get('PHOTOS_TABLE', 'PhotosMetadata'))
share_links_table = dynamodb.Table(os.environ.get('SHARE_LINKS_TABLE', 'ShareLinks'))

# S3 bucket for photos
PHOTOS_BUCKET = os.environ.get('PHOTOS_BUCKET', 'yeshvant-photos-bucket-2024')

# CloudFront domain for photo URLs
CLOUDFRONT_DOMAIN = os.environ.get('CLOUDFRONT_DOMAIN', 'd1nf5k4wr11svj.cloudfront.net')


def get_user_id_from_event(event):
    """Extract Cognito user ID from API Gateway authorizer context.

    When API Gateway is configured with a Cognito authorizer, it decodes
    the JWT token and passes the claims in the requestContext.
    The 'sub' claim contains the unique Cognito user ID.
    """
    try:
        # API Gateway passes decoded token claims in requestContext
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        user_id = claims.get('sub')  # Cognito user ID (UUID)
        if user_id:
            return user_id
    except Exception:
        pass
    return None  # Return None for unauthenticated requests


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
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }


def is_photo_visible(item):
    """Check if a photo should be visible (not hidden and not metadata)"""
    if not item['sk'].startswith('PHOTO#'):
        return False
    filename = item.get('filename', '')
    if filename.startswith('.'):
        return False
    if item.get('hidden', False):
        return False
    return True


def get_first_valid_photo(album_id):
    """Get the first valid (non-metadata, non-hidden) photo from an album for cover"""
    response = photos_table.query(
        KeyConditionExpression=Key('pk').eq(f'ALBUM#{album_id}'),
        Limit=20  # Check first 20 to find a valid one
    )
    for item in response.get('Items', []):
        if is_photo_visible(item):
            thumbnail_key = item.get('thumbnailKey')
            if thumbnail_key:
                return f"https://{CLOUDFRONT_DOMAIN}/{thumbnail_key}"
    return None


def hide_photo(photo_id, user_id='default-user'):
    """Hide a photo (soft delete) by marking it as hidden.

    This finds the photo in DynamoDB and sets hidden=True.
    The photo can be restored later by setting hidden=False.
    """
    from datetime import datetime

    # Find the photo across all albums
    response = photos_table.scan(
        FilterExpression='photoId = :pid OR contains(sk, :photo_sk)',
        ExpressionAttributeValues={
            ':pid': photo_id,
            ':photo_sk': f'PHOTO#{photo_id}'
        }
    )

    items = response.get('Items', [])
    hidden_count = 0

    for item in items:
        if item.get('sk', '').startswith('PHOTO#') or item.get('photoId') == photo_id:
            # Update the photo item to mark as hidden
            photos_table.update_item(
                Key={
                    'pk': item['pk'],
                    'sk': item['sk']
                },
                UpdateExpression='SET #hidden = :hidden, hiddenAt = :hiddenAt',
                ExpressionAttributeNames={
                    '#hidden': 'hidden'
                },
                ExpressionAttributeValues={
                    ':hidden': True,
                    ':hiddenAt': datetime.utcnow().isoformat() + 'Z'
                }
            )
            hidden_count += 1

    # Also hide any DATE# entries for timeline view
    date_response = photos_table.query(
        KeyConditionExpression=Key('pk').eq(f'USER#{user_id}'),
        FilterExpression=Attr('photoId').eq(photo_id)
    )
    for item in date_response.get('Items', []):
        if item.get('sk', '').startswith('DATE#'):
            photos_table.update_item(
                Key={
                    'pk': item['pk'],
                    'sk': item['sk']
                },
                UpdateExpression='SET #hidden = :hidden, hiddenAt = :hiddenAt',
                ExpressionAttributeNames={
                    '#hidden': 'hidden'
                },
                ExpressionAttributeValues={
                    ':hidden': True,
                    ':hiddenAt': datetime.utcnow().isoformat() + 'Z'
                }
            )
            hidden_count += 1

    if hidden_count == 0:
        raise ValueError(f'Photo not found: {photo_id}')

    return {'photoId': photo_id, 'hidden': True, 'itemsUpdated': hidden_count}


def get_albums(user_id='default-user'):
    """Get all albums for a user"""
    response = photos_table.query(
        KeyConditionExpression=Key('pk').eq(f'USER#{user_id}') & Key('sk').begins_with('ALBUM#')
    )

    albums = []
    for item in response.get('Items', []):
        album_id = item['sk'].replace('ALBUM#', '')

        # Always get first valid (non-metadata, non-hidden) photo as cover
        cover_photo = get_first_valid_photo(album_id)

        # Count actual valid photos (exclude metadata files and hidden photos)
        photo_response = photos_table.query(
            KeyConditionExpression=Key('pk').eq(f'ALBUM#{album_id}')
        )
        valid_count = sum(1 for p in photo_response.get('Items', []) if is_photo_visible(p))

        albums.append({
            'id': album_id,
            'name': item.get('name', 'Untitled Album'),
            'photoCount': valid_count,
            'coverPhoto': cover_photo,
            'createdAt': item.get('createdAt')
        })

    # Sort by createdAt descending (newest first)
    albums.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
    return albums


def get_album_photos(album_id, user_id='default-user'):
    """Get all photos for an album (excludes hidden photos)"""
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
        # Use is_photo_visible to filter out hidden and metadata photos
        if not is_photo_visible(item):
            continue
        photo_id = item['sk'].replace('PHOTO#', '')
        photos.append({
            'id': photo_id,
            'filename': item.get('filename', ''),
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


def get_photos_by_date(user_id='default-user', start_date=None, end_date=None, limit=100):
    """Get photos ordered by date using DATE# items (no GSI needed).

    Query pattern: pk=USER#userId, sk begins_with DATE#
    Sort key format: DATE#YYYY-MM-DD#PHOTO#photoId
    Excludes hidden photos.
    """
    try:
        # Build key condition for main table (no GSI)
        pk = f'USER#{user_id}'

        if start_date and end_date:
            # Query between two dates
            key_condition = Key('pk').eq(pk) & Key('sk').between(
                f'DATE#{start_date}',
                f'DATE#{end_date}~'  # ~ is after all valid chars
            )
        elif start_date:
            # Query from start_date onwards
            key_condition = Key('pk').eq(pk) & Key('sk').gte(f'DATE#{start_date}')
        elif end_date:
            # Query up to end_date
            key_condition = Key('pk').eq(pk) & Key('sk').between('DATE#', f'DATE#{end_date}~')
        else:
            # Query all DATE# items
            key_condition = Key('pk').eq(pk) & Key('sk').begins_with('DATE#')

        response = photos_table.query(
            KeyConditionExpression=key_condition,
            ScanIndexForward=False,  # Descending order (newest first)
            Limit=limit
        )

        photos = []
        for item in response.get('Items', []):
            filename = item.get('filename', '')
            # Skip macOS metadata files and hidden photos
            if filename.startswith('.'):
                continue
            if item.get('hidden', False):
                continue

            photo_id = item.get('photoId')
            photos.append({
                'id': photo_id,
                'albumId': item.get('albumId'),
                'filename': filename,
                'url': f"https://{CLOUDFRONT_DOMAIN}/{item.get('s3Key')}",
                'thumbnailUrl': f"https://{CLOUDFRONT_DOMAIN}/{item.get('thumbnailKey')}" if item.get('thumbnailKey') else None,
                'uploadDate': item.get('uploadDate'),
                'size': item.get('size'),
                'contentType': item.get('contentType')
            })

        # Group by date for timeline view
        from collections import defaultdict
        by_date = defaultdict(list)
        for photo in photos:
            date_str = photo.get('uploadDate', '')[:10]  # Get YYYY-MM-DD
            by_date[date_str].append(photo)

        return {
            'photos': photos,
            'byDate': dict(by_date),
            'totalCount': len(photos),
            'hasMore': 'LastEvaluatedKey' in response
        }
    except Exception as e:
        return {'error': str(e), 'photos': [], 'byDate': {}, 'totalCount': 0}


def create_share_link(album_id, user_id='default-user', expires_in_days=None):
    """Create a new share link for an album"""
    from datetime import datetime, timedelta
    import uuid

    # Generate a unique token
    link_id = f"{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:11]}-{uuid.uuid4().hex[:3]}"

    item = {
        'linkId': link_id,
        'albumId': album_id,
        'userId': user_id,
        'createdBy': user_id,
        'createdAt': datetime.utcnow().isoformat() + 'Z',
        'accessCount': 0
    }

    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        item['expiresAt'] = expires_at.isoformat() + 'Z'

    share_links_table.put_item(Item=item)

    return {
        'token': link_id,
        'albumId': album_id,
        'expiresAt': item.get('expiresAt'),
        'shareUrl': f"https://{CLOUDFRONT_DOMAIN}/shared/?token={link_id}"
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


def create_album_if_not_exists(album_id, album_name, user_id='default-user'):
    """Create an album in DynamoDB if it doesn't exist"""
    from datetime import datetime

    # Check if album already exists
    response = photos_table.get_item(
        Key={
            'pk': f'USER#{user_id}',
            'sk': f'ALBUM#{album_id}'
        }
    )

    if 'Item' not in response:
        # Create the album
        photos_table.put_item(Item={
            'pk': f'USER#{user_id}',
            'sk': f'ALBUM#{album_id}',
            'albumId': album_id,
            'name': album_name or 'Untitled Album',
            'userId': user_id,
            'createdAt': datetime.utcnow().isoformat() + 'Z'
        })
        return True
    return False


def migrate_user_data(from_user_id, to_user_id):
    """Migrate all albums and photo data from one user to another.

    This is used to transfer data from 'default-user' to an authenticated user.
    """
    from datetime import datetime

    migrated_items = []

    # Find all items belonging to the source user
    response = photos_table.query(
        KeyConditionExpression=Key('pk').eq(f'USER#{from_user_id}')
    )

    items_to_migrate = response.get('Items', [])

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = photos_table.query(
            KeyConditionExpression=Key('pk').eq(f'USER#{from_user_id}'),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items_to_migrate.extend(response.get('Items', []))

    # Migrate each item
    for item in items_to_migrate:
        old_pk = item['pk']
        old_sk = item['sk']

        # Create new item with updated pk
        new_item = dict(item)
        new_item['pk'] = f'USER#{to_user_id}'
        new_item['userId'] = to_user_id
        new_item['migratedFrom'] = from_user_id
        new_item['migratedAt'] = datetime.utcnow().isoformat() + 'Z'

        # Write new item
        photos_table.put_item(Item=new_item)

        # Delete old item
        photos_table.delete_item(Key={'pk': old_pk, 'sk': old_sk})

        migrated_items.append({
            'type': 'album' if old_sk.startswith('ALBUM#') else 'date_index',
            'id': old_sk
        })

    return {
        'migratedCount': len(migrated_items),
        'fromUser': from_user_id,
        'toUser': to_user_id,
        'items': migrated_items
    }


def update_album(album_id, updates, user_id='default-user'):
    """Update album metadata (e.g., name)"""
    from datetime import datetime

    # Check if album exists
    response = photos_table.get_item(
        Key={
            'pk': f'USER#{user_id}',
            'sk': f'ALBUM#{album_id}'
        }
    )

    if 'Item' not in response:
        raise ValueError(f'Album not found: {album_id}')

    # Build update expression
    update_expressions = []
    expression_names = {}
    expression_values = {}

    if 'name' in updates:
        update_expressions.append('#name = :name')
        expression_names['#name'] = 'name'
        expression_values[':name'] = updates['name']

    if not update_expressions:
        raise ValueError('No valid updates provided')

    # Add updatedAt timestamp
    update_expressions.append('updatedAt = :updatedAt')
    expression_values[':updatedAt'] = datetime.utcnow().isoformat() + 'Z'

    # Update the album
    photos_table.update_item(
        Key={
            'pk': f'USER#{user_id}',
            'sk': f'ALBUM#{album_id}'
        },
        UpdateExpression='SET ' + ', '.join(update_expressions),
        ExpressionAttributeNames=expression_names if expression_names else None,
        ExpressionAttributeValues=expression_values
    )

    return {
        'albumId': album_id,
        'updated': True,
        **updates
    }


def generate_upload_urls(album_id, filename, content_type, user_id='default-user', is_thumbnail=False):
    """Generate presigned URLs for uploading a photo and optionally its thumbnail"""
    import uuid
    from datetime import datetime

    # Generate unique photo ID
    photo_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"

    # Determine S3 keys
    if is_thumbnail:
        s3_key = f"thumbnails/{user_id}/{album_id}/{filename}"
    else:
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'jpg'
        s3_key = f"photos/{user_id}/{album_id}/{photo_id}.{ext}"
        thumbnail_key = f"thumbnails/{user_id}/{album_id}/{photo_id}_thumb.jpg"

    # Generate presigned URL for upload
    upload_url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': PHOTOS_BUCKET,
            'Key': s3_key,
            'ContentType': content_type
        },
        ExpiresIn=3600  # 1 hour
    )

    result = {
        'uploadUrl': upload_url,
        'photoKey': s3_key,
        'photoId': photo_id
    }

    if not is_thumbnail:
        # Also generate thumbnail upload URL
        thumb_upload_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': PHOTOS_BUCKET,
                'Key': thumbnail_key,
                'ContentType': 'image/jpeg'
            },
            ExpiresIn=3600
        )
        result['thumbnailUploadUrl'] = thumb_upload_url
        result['thumbnailKey'] = thumbnail_key

    return result


def save_photo_metadata(album_id, photo_id, filename, s3_key, thumbnail_key, content_type, size=0, user_id='default-user'):
    """Save photo metadata to DynamoDB"""
    from datetime import datetime

    upload_date = datetime.utcnow().isoformat() + 'Z'
    date_str = upload_date[:10]  # YYYY-MM-DD

    # Save photo in album
    photos_table.put_item(Item={
        'pk': f'ALBUM#{album_id}',
        'sk': f'PHOTO#{photo_id}',
        'photoId': photo_id,
        'albumId': album_id,
        'filename': filename,
        's3Key': s3_key,
        'thumbnailKey': thumbnail_key,
        'contentType': content_type,
        'size': size,
        'uploadDate': upload_date,
        'userId': user_id
    })

    # Also add date index entry for timeline
    photos_table.put_item(Item={
        'pk': f'USER#{user_id}',
        'sk': f'DATE#{date_str}#PHOTO#{photo_id}',
        'photoId': photo_id,
        'albumId': album_id,
        'filename': filename,
        's3Key': s3_key,
        'thumbnailKey': thumbnail_key,
        'contentType': content_type,
        'size': size,
        'uploadDate': upload_date
    })

    return {
        'photoId': photo_id,
        'url': f"https://{CLOUDFRONT_DOMAIN}/{s3_key}",
        'thumbnailUrl': f"https://{CLOUDFRONT_DOMAIN}/{thumbnail_key}" if thumbnail_key else None
    }


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

    # Get user ID from Cognito token (if authenticated)
    user_id = get_user_id_from_event(event)

    # Define protected routes that require authentication
    # Note: /edit is NOT protected to allow shared album viewers to use AI features
    protected_routes = ['/albums', '/album', '/timeline', '/photos', '/upload']
    is_protected = any(path == route or path.startswith(route + '/') or path.startswith('/api' + route) for route in protected_routes)

    # Check authentication for protected routes
    if is_protected and not user_id:
        return cors_response(401, {'error': 'Authentication required'})

    # ============================================
    # RATE LIMITING CHECK
    # ============================================
    if RATE_LIMITING_ENABLED:
        try:
            # Extract IP address and create identifier
            ip_address = event.get('requestContext', {}).get('identity', {}).get('sourceIp') or \
                        event.get('requestContext', {}).get('http', {}).get('sourceIp') or \
                        'unknown'

            # Prefer user ID if authenticated, otherwise use IP
            identifier = f"USER#{user_id}" if user_id else f"IP#{ip_address}"

            # Check rate limit
            rate_check = rate_limiter.check_rate_limit(identifier, path)

            if not rate_check['allowed']:
                # Rate limit exceeded - detect abuse and send notifications
                current_count = rate_check['current_count']
                abuse_info = rate_limiter.detect_abuse(identifier, current_count, path)

                # Record the abuse event
                rate_limiter.record_abuse_event(identifier, abuse_info, path)

                # Publish CloudWatch metrics
                rate_limiter.publish_cloudwatch_metrics(identifier, abuse_info, path)

                # Check if we should send notifications
                notification_check = rate_limiter.should_send_notification(identifier, abuse_info['severity'])

                if notification_check['should_send']:
                    # Send notifications (email and SMS based on severity)
                    notification_handler.send_notifications(abuse_info, identifier, path)
                    print(f"Notifications sent for {identifier} on {path}")
                else:
                    print(f"Notification skipped for {identifier}: {notification_check['reason']}")

                # Return 429 Too Many Requests
                return cors_response(429, {
                    'error': 'Too Many Requests',
                    'message': f"Rate limit exceeded. Please try again in {int(rate_check['time_until_reset'])} seconds.",
                    'retryAfter': int(rate_check['time_until_reset']),
                    'limit': rate_check['limit'],
                    'current': current_count
                })

            # Record the successful request
            record_result = rate_limiter.record_request(identifier, path, {
                'method': http_method,
                'userAgent': event.get('requestContext', {}).get('identity', {}).get('userAgent', 'unknown')
            })

            print(f"Request recorded: {identifier} on {path} - Count: {record_result.get('count', 0)}")

        except Exception as rate_limit_error:
            # Log error but don't block request if rate limiting fails
            print(f"Rate limiting error (allowing request): {rate_limit_error}")
    # ============================================
    # END RATE LIMITING CHECK
    # ============================================

    try:
        # Route: GET /albums
        if path == '/albums' or path == '/api/albums':
            albums = get_albums(user_id=user_id)
            return cors_response(200, {'albums': albums})

        # Route: GET /albums/{id}
        if path.startswith('/albums/') or path.startswith('/api/albums/'):
            album_id = path.split('/')[-1]
            if album_id:
                album_data = get_album_photos(album_id, user_id=user_id)
                return cors_response(200, album_data)

        # Route: GET /album?id=xxx
        if (path == '/album' or path == '/api/album') and http_method == 'GET':
            album_id = query_params.get('id')
            if album_id:
                album_data = get_album_photos(album_id, user_id=user_id)
                return cors_response(200, album_data)
            return cors_response(400, {'error': 'Missing album id'})

        # Route: PUT /album - Update album name
        if (path == '/album' or path == '/api/album') and http_method == 'PUT':
            try:
                body = json.loads(event.get('body', '{}'))
                album_id = body.get('albumId')
                name = body.get('name')

                if not album_id:
                    return cors_response(400, {'error': 'Missing albumId'})
                if not name:
                    return cors_response(400, {'error': 'Missing name'})

                result = update_album(album_id, {'name': name}, user_id=user_id)
                return cors_response(200, result)

            except ValueError as e:
                return cors_response(404, {'error': str(e)})
            except Exception as e:
                return cors_response(500, {'error': f'Update failed: {str(e)}'})

        # Route: GET /timeline or /photos?startDate=X&endDate=Y
        if path == '/timeline' or path == '/photos' or path == '/api/timeline' or path == '/api/photos':
            start_date = query_params.get('startDate')
            end_date = query_params.get('endDate')
            limit = int(query_params.get('limit', 100))
            timeline_data = get_photos_by_date(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                limit=min(limit, 500)  # Cap at 500
            )
            return cors_response(200, timeline_data)

        # Route: POST /share - Create a new share link (requires auth)
        if (path == '/share' or path == '/api/share') and http_method == 'POST':
            if not user_id:
                return cors_response(401, {'error': 'Authentication required'})
            try:
                body = json.loads(event.get('body', '{}'))
                album_id = body.get('albumId')
                expires_in_days = body.get('expiresInDays')

                if not album_id:
                    return cors_response(400, {'error': 'Missing albumId'})

                result = create_share_link(album_id, user_id=user_id, expires_in_days=expires_in_days)
                return cors_response(200, result)

            except Exception as e:
                return cors_response(500, {'error': f'Failed to create share link: {str(e)}'})

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

        # Route: POST /edit - Image editing operations
        if (path == '/edit' or path == '/api/edit') and http_method == 'POST':
            try:
                from image_processor import process_image_edit

                body = json.loads(event.get('body', '{}'))
                photo_id = body.get('photoId')
                operation = body.get('operation')
                parameters = body.get('parameters', {})

                if not photo_id:
                    return cors_response(400, {'error': 'Missing photoId'})
                if not operation:
                    return cors_response(400, {'error': 'Missing operation'})

                valid_operations = ['rotate', 'enhance', 'upscale', 'remove_bg', 'style_transfer']
                if operation not in valid_operations:
                    return cors_response(400, {
                        'error': f'Invalid operation: {operation}',
                        'validOperations': valid_operations
                    })

                result = process_image_edit(photo_id, operation, parameters)
                return cors_response(200, result)

            except ValueError as e:
                return cors_response(400, {'error': str(e)})
            except Exception as e:
                return cors_response(500, {'error': f'Edit failed: {str(e)}'})

        # Route: DELETE /photos/{id} - Hide (soft delete) a photo
        if (path.startswith('/photos/') or path.startswith('/api/photos/')) and http_method == 'DELETE':
            try:
                photo_id = path.split('/')[-1]
                if not photo_id or photo_id in ['photos', 'api']:
                    return cors_response(400, {'error': 'Missing photo ID'})

                result = hide_photo(photo_id, user_id=user_id)
                return cors_response(200, result)

            except ValueError as e:
                return cors_response(404, {'error': str(e)})
            except Exception as e:
                return cors_response(500, {'error': f'Delete failed: {str(e)}'})

        # Route: POST /photos/hide - Hide a photo (alternative to DELETE)
        if (path == '/photos/hide' or path == '/api/photos/hide') and http_method == 'POST':
            try:
                body = json.loads(event.get('body', '{}'))
                photo_id = body.get('photoId')

                if not photo_id:
                    return cors_response(400, {'error': 'Missing photoId'})

                result = hide_photo(photo_id, user_id=user_id)
                return cors_response(200, result)

            except ValueError as e:
                return cors_response(404, {'error': str(e)})
            except Exception as e:
                return cors_response(500, {'error': f'Hide failed: {str(e)}'})

        # Route: POST /upload - Get presigned URLs for uploading photos
        if (path == '/upload' or path == '/api/upload') and http_method == 'POST':
            try:
                body = json.loads(event.get('body', '{}'))
                album_id = body.get('albumId')
                album_name = body.get('albumName', 'Untitled Album')
                filename = body.get('filename')
                content_type = body.get('contentType', 'image/jpeg')

                if not album_id:
                    return cors_response(400, {'error': 'Missing albumId'})
                if not filename:
                    return cors_response(400, {'error': 'Missing filename'})

                # Create album if it doesn't exist
                create_album_if_not_exists(album_id, album_name, user_id=user_id)

                # Generate presigned upload URLs
                result = generate_upload_urls(album_id, filename, content_type, user_id=user_id)
                return cors_response(200, result)

            except Exception as e:
                return cors_response(500, {'error': f'Upload preparation failed: {str(e)}'})

        # Route: POST /upload/complete - Save photo metadata after successful upload
        if (path == '/upload/complete' or path == '/api/upload/complete') and http_method == 'POST':
            try:
                body = json.loads(event.get('body', '{}'))
                album_id = body.get('albumId')
                photo_id = body.get('photoId')
                filename = body.get('filename')
                photo_key = body.get('photoKey')
                thumbnail_key = body.get('thumbnailKey')
                content_type = body.get('contentType', 'image/jpeg')
                size = body.get('size', 0)

                if not album_id or not photo_id or not photo_key:
                    return cors_response(400, {'error': 'Missing required fields: albumId, photoId, photoKey'})

                result = save_photo_metadata(
                    album_id, photo_id, filename, photo_key, thumbnail_key, content_type, size, user_id=user_id
                )
                return cors_response(200, result)

            except Exception as e:
                return cors_response(500, {'error': f'Save metadata failed: {str(e)}'})

        # Route: POST /migrate - Migrate data from default-user to authenticated user
        if (path == '/migrate' or path == '/api/migrate') and http_method == 'POST':
            if not user_id:
                return cors_response(401, {'error': 'Authentication required'})
            try:
                # Migrate from default-user to authenticated user
                result = migrate_user_data('default-user', user_id)
                return cors_response(200, result)

            except Exception as e:
                return cors_response(500, {'error': f'Migration failed: {str(e)}'})

        # Route: GET /duplicates - Find duplicate images
        if (path == '/duplicates' or path == '/api/duplicates') and http_method == 'GET':
            try:
                from duplicate_detector import find_duplicates_in_album, find_duplicates_across_albums

                album_id = query_params.get('albumId')

                if album_id:
                    # Find duplicates within a specific album
                    result = find_duplicates_in_album(album_id, user_id=user_id)
                else:
                    # Find duplicates across all albums
                    result = find_duplicates_across_albums(user_id=user_id)

                return cors_response(200, result)

            except Exception as e:
                return cors_response(500, {'error': f'Duplicate detection failed: {str(e)}'})

        # Default: return 404
        return cors_response(404, {'error': 'Not found', 'path': path})

    except Exception as e:
        return cors_response(500, {'error': str(e)})
