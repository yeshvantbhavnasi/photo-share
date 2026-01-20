"""
Duplicate Image Detection Module for Bhavnasi Share

Detects duplicate images using:
- Perceptual hashing (pHash) for visual similarity
- File hash (MD5) for exact matches
- File size comparison as a quick filter
"""

import os
import io
import hashlib
from PIL import Image
import boto3
from boto3.dynamodb.conditions import Key, Attr

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Configuration
PHOTOS_BUCKET = os.environ.get('PHOTOS_BUCKET', 'yeshvant-photos-bucket-2024')
PHOTOS_TABLE_NAME = os.environ.get('PHOTOS_TABLE', 'PhotosMetadata')
CLOUDFRONT_DOMAIN = os.environ.get('CLOUDFRONT_DOMAIN', 'd1nf5k4wr11svj.cloudfront.net')

photos_table = dynamodb.Table(PHOTOS_TABLE_NAME)

# Similarity threshold for perceptual hash (lower = more similar)
# 0 = identical, 10 = very similar, 20+ = different images
SIMILARITY_THRESHOLD = 10


def compute_average_hash(image, hash_size=8):
    """
    Compute average hash (aHash) of an image.

    This is a simple but effective perceptual hashing algorithm:
    1. Reduce size to hash_size x hash_size
    2. Convert to grayscale
    3. Compute mean pixel value
    4. Set bits based on whether each pixel is above/below mean
    """
    # Resize to hash_size x hash_size
    img = image.resize((hash_size, hash_size), Image.Resampling.LANCZOS)

    # Convert to grayscale
    img = img.convert('L')

    # Get pixel data
    pixels = list(img.getdata())

    # Compute mean
    avg = sum(pixels) / len(pixels)

    # Create hash: 1 if pixel >= avg, 0 otherwise
    bits = ''.join('1' if p >= avg else '0' for p in pixels)

    # Convert to hex string
    return hex(int(bits, 2))[2:].zfill(hash_size * hash_size // 4)


def compute_difference_hash(image, hash_size=8):
    """
    Compute difference hash (dHash) of an image.

    More robust than aHash:
    1. Resize to (hash_size + 1) x hash_size
    2. Convert to grayscale
    3. Compare adjacent pixels horizontally
    """
    # Resize to (hash_size + 1) x hash_size
    img = image.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)

    # Convert to grayscale
    img = img.convert('L')

    # Get pixel data
    pixels = list(img.getdata())

    # Compute difference hash
    bits = []
    for row in range(hash_size):
        for col in range(hash_size):
            left_pixel = pixels[row * (hash_size + 1) + col]
            right_pixel = pixels[row * (hash_size + 1) + col + 1]
            bits.append('1' if left_pixel > right_pixel else '0')

    # Convert to hex string
    return hex(int(''.join(bits), 2))[2:].zfill(hash_size * hash_size // 4)


def compute_file_hash(data):
    """Compute MD5 hash of file data for exact matching"""
    return hashlib.md5(data).hexdigest()


def hamming_distance(hash1, hash2):
    """
    Compute Hamming distance between two hex hash strings.
    Returns the number of differing bits.
    """
    if len(hash1) != len(hash2):
        return float('inf')

    # Convert hex to binary and compare
    bin1 = bin(int(hash1, 16))[2:].zfill(len(hash1) * 4)
    bin2 = bin(int(hash2, 16))[2:].zfill(len(hash2) * 4)

    return sum(b1 != b2 for b1, b2 in zip(bin1, bin2))


def get_image_from_s3(s3_key):
    """Download image from S3 and return as PIL Image"""
    try:
        response = s3.get_object(Bucket=PHOTOS_BUCKET, Key=s3_key)
        image_data = response['Body'].read()
        return Image.open(io.BytesIO(image_data)), image_data
    except Exception as e:
        print(f"Error downloading {s3_key}: {e}")
        return None, None


def compute_image_hashes(image, image_data):
    """Compute all hashes for an image"""
    return {
        'aHash': compute_average_hash(image),
        'dHash': compute_difference_hash(image),
        'fileHash': compute_file_hash(image_data),
        'fileSize': len(image_data)
    }


def find_duplicates_in_album(album_id, user_id='default-user'):
    """
    Find duplicate images within a single album.

    Returns groups of duplicate photos.
    """
    # Get all photos in the album
    response = photos_table.query(
        KeyConditionExpression=Key('pk').eq(f'ALBUM#{album_id}')
    )

    photos = []
    for item in response.get('Items', []):
        if not item.get('sk', '').startswith('PHOTO#'):
            continue
        if item.get('hidden', False):
            continue
        if item.get('filename', '').startswith('.'):
            continue

        photos.append({
            'id': item.get('photoId', item['sk'].replace('PHOTO#', '')),
            's3Key': item.get('s3Key'),
            'thumbnailKey': item.get('thumbnailKey'),
            'filename': item.get('filename', ''),
            'size': item.get('size', 0),
            'url': f"https://{CLOUDFRONT_DOMAIN}/{item.get('s3Key')}",
            'thumbnailUrl': f"https://{CLOUDFRONT_DOMAIN}/{item.get('thumbnailKey')}" if item.get('thumbnailKey') else None
        })

    if len(photos) < 2:
        return {'duplicateGroups': [], 'totalPhotos': len(photos), 'duplicatesFound': 0}

    # Compute hashes for all photos
    photo_hashes = []
    for photo in photos:
        if not photo.get('s3Key'):
            continue

        # Use thumbnail for faster processing if available
        key_to_use = photo.get('thumbnailKey') or photo.get('s3Key')
        image, image_data = get_image_from_s3(key_to_use)

        if image:
            hashes = compute_image_hashes(image, image_data)
            photo_hashes.append({
                **photo,
                **hashes
            })

    # Find duplicates by comparing hashes
    duplicate_groups = []
    processed = set()

    for i, photo1 in enumerate(photo_hashes):
        if photo1['id'] in processed:
            continue

        group = [photo1]

        for j, photo2 in enumerate(photo_hashes[i+1:], i+1):
            if photo2['id'] in processed:
                continue

            # Check for exact match first (fastest)
            if photo1.get('fileHash') == photo2.get('fileHash'):
                group.append(photo2)
                processed.add(photo2['id'])
                continue

            # Check perceptual similarity using dHash
            distance = hamming_distance(photo1.get('dHash', ''), photo2.get('dHash', ''))
            if distance <= SIMILARITY_THRESHOLD:
                group.append({
                    **photo2,
                    'similarity': 100 - (distance * 100 // 64),  # Convert to percentage
                    'exactMatch': False
                })
                processed.add(photo2['id'])

        if len(group) > 1:
            # Mark first photo in group
            group[0]['similarity'] = 100
            group[0]['exactMatch'] = True
            duplicate_groups.append({
                'photos': group,
                'count': len(group)
            })
            processed.add(photo1['id'])

    total_duplicates = sum(g['count'] - 1 for g in duplicate_groups)

    return {
        'duplicateGroups': duplicate_groups,
        'totalPhotos': len(photos),
        'duplicatesFound': total_duplicates,
        'groupsFound': len(duplicate_groups)
    }


def find_duplicates_across_albums(user_id='default-user'):
    """
    Find duplicate images across all albums for a user.

    Returns groups of duplicate photos with album information.
    """
    # Get all albums for the user
    response = photos_table.query(
        KeyConditionExpression=Key('pk').eq(f'USER#{user_id}') & Key('sk').begins_with('ALBUM#')
    )

    albums = []
    for item in response.get('Items', []):
        album_id = item['sk'].replace('ALBUM#', '')
        albums.append({
            'id': album_id,
            'name': item.get('name', 'Untitled Album')
        })

    # Collect all photos with hashes
    all_photo_hashes = []

    for album in albums:
        album_response = photos_table.query(
            KeyConditionExpression=Key('pk').eq(f'ALBUM#{album["id"]}')
        )

        for item in album_response.get('Items', []):
            if not item.get('sk', '').startswith('PHOTO#'):
                continue
            if item.get('hidden', False):
                continue
            if item.get('filename', '').startswith('.'):
                continue

            photo = {
                'id': item.get('photoId', item['sk'].replace('PHOTO#', '')),
                'albumId': album['id'],
                'albumName': album['name'],
                's3Key': item.get('s3Key'),
                'thumbnailKey': item.get('thumbnailKey'),
                'filename': item.get('filename', ''),
                'size': item.get('size', 0),
                'url': f"https://{CLOUDFRONT_DOMAIN}/{item.get('s3Key')}",
                'thumbnailUrl': f"https://{CLOUDFRONT_DOMAIN}/{item.get('thumbnailKey')}" if item.get('thumbnailKey') else None
            }

            # Use thumbnail for faster processing
            key_to_use = photo.get('thumbnailKey') or photo.get('s3Key')
            if key_to_use:
                image, image_data = get_image_from_s3(key_to_use)
                if image:
                    hashes = compute_image_hashes(image, image_data)
                    all_photo_hashes.append({**photo, **hashes})

    if len(all_photo_hashes) < 2:
        return {'duplicateGroups': [], 'totalPhotos': len(all_photo_hashes), 'duplicatesFound': 0}

    # Find duplicates
    duplicate_groups = []
    processed = set()

    for i, photo1 in enumerate(all_photo_hashes):
        if photo1['id'] in processed:
            continue

        group = [photo1]

        for j, photo2 in enumerate(all_photo_hashes[i+1:], i+1):
            if photo2['id'] in processed:
                continue

            # Check for exact match first
            if photo1.get('fileHash') == photo2.get('fileHash'):
                group.append({**photo2, 'similarity': 100, 'exactMatch': True})
                processed.add(photo2['id'])
                continue

            # Check perceptual similarity
            distance = hamming_distance(photo1.get('dHash', ''), photo2.get('dHash', ''))
            if distance <= SIMILARITY_THRESHOLD:
                group.append({
                    **photo2,
                    'similarity': 100 - (distance * 100 // 64),
                    'exactMatch': False
                })
                processed.add(photo2['id'])

        if len(group) > 1:
            group[0]['similarity'] = 100
            group[0]['exactMatch'] = True

            # Check if duplicates are in different albums (cross-album)
            albums_in_group = set(p['albumId'] for p in group)

            duplicate_groups.append({
                'photos': group,
                'count': len(group),
                'crossAlbum': len(albums_in_group) > 1,
                'albums': list(albums_in_group)
            })
            processed.add(photo1['id'])

    total_duplicates = sum(g['count'] - 1 for g in duplicate_groups)

    return {
        'duplicateGroups': duplicate_groups,
        'totalPhotos': len(all_photo_hashes),
        'duplicatesFound': total_duplicates,
        'groupsFound': len(duplicate_groups),
        'crossAlbumGroups': sum(1 for g in duplicate_groups if g.get('crossAlbum', False))
    }


def check_duplicate_before_upload(image_data, album_id, user_id='default-user'):
    """
    Check if an image is a duplicate before uploading.

    Returns matching photos if duplicates are found.
    """
    # Compute hashes for the new image
    image = Image.open(io.BytesIO(image_data))
    new_hashes = compute_image_hashes(image, image_data)

    # Get existing photos in the album
    response = photos_table.query(
        KeyConditionExpression=Key('pk').eq(f'ALBUM#{album_id}')
    )

    matches = []

    for item in response.get('Items', []):
        if not item.get('sk', '').startswith('PHOTO#'):
            continue
        if item.get('hidden', False):
            continue

        s3_key = item.get('thumbnailKey') or item.get('s3Key')
        if not s3_key:
            continue

        existing_image, existing_data = get_image_from_s3(s3_key)
        if not existing_image:
            continue

        existing_hashes = compute_image_hashes(existing_image, existing_data)

        # Check for exact match
        if new_hashes['fileHash'] == existing_hashes['fileHash']:
            matches.append({
                'id': item.get('photoId', item['sk'].replace('PHOTO#', '')),
                'filename': item.get('filename', ''),
                'similarity': 100,
                'exactMatch': True,
                'url': f"https://{CLOUDFRONT_DOMAIN}/{item.get('s3Key')}",
                'thumbnailUrl': f"https://{CLOUDFRONT_DOMAIN}/{item.get('thumbnailKey')}" if item.get('thumbnailKey') else None
            })
            continue

        # Check perceptual similarity
        distance = hamming_distance(new_hashes['dHash'], existing_hashes['dHash'])
        if distance <= SIMILARITY_THRESHOLD:
            matches.append({
                'id': item.get('photoId', item['sk'].replace('PHOTO#', '')),
                'filename': item.get('filename', ''),
                'similarity': 100 - (distance * 100 // 64),
                'exactMatch': False,
                'url': f"https://{CLOUDFRONT_DOMAIN}/{item.get('s3Key')}",
                'thumbnailUrl': f"https://{CLOUDFRONT_DOMAIN}/{item.get('thumbnailKey')}" if item.get('thumbnailKey') else None
            })

    return {
        'isDuplicate': len(matches) > 0,
        'matches': matches
    }
