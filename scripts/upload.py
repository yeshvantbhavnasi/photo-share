#!/usr/bin/env python3
"""
Family Photo Sharing - Batch Upload Script

This script uploads photos from a local Mac folder to S3, creating albums
and storing metadata in DynamoDB.

Usage:
    python upload.py /path/to/folder [--album-name "My Album"]

Requirements:
    pip install boto3 pillow python-dotenv
"""

import os
import sys
import argparse
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("Error: boto3 is required. Install it with: pip install boto3")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is required. Install it with: pip install pillow")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables directly.")
    load_dotenv = lambda: None

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Configuration
REGION = os.getenv('AWS_REGION', 'us-east-1')
PHOTOS_BUCKET = os.getenv('PHOTOS_BUCKET', 'yeshvant-photos-storage-2026')
PHOTOS_TABLE = os.getenv('PHOTOS_TABLE', 'PhotosMetadata')
SHARE_LINKS_TABLE = os.getenv('SHARE_LINKS_TABLE', 'ShareLinks')
USER_ID = os.getenv('USER_ID', 'default-user')

# Supported image formats
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif'}

# Thumbnail settings
THUMBNAIL_SIZE = (400, 400)
THUMBNAIL_QUALITY = 85


class PhotoUploader:
    def __init__(self):
        self.s3 = boto3.client('s3', region_name=REGION)
        self.dynamodb = boto3.resource('dynamodb', region_name=REGION)
        self.photos_table = self.dynamodb.Table(PHOTOS_TABLE)
        self.share_links_table = self.dynamodb.Table(SHARE_LINKS_TABLE)

    def generate_id(self) -> str:
        """Generate a unique ID for albums and photos."""
        return str(uuid.uuid4())[:12]

    def get_content_type(self, ext: str) -> str:
        """Get content type from file extension."""
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.heic': 'image/heic',
            '.heif': 'image/heif',
        }
        return content_types.get(ext.lower(), 'application/octet-stream')

    def create_thumbnail(self, image_path: Path, output_path: Path) -> bool:
        """Create a thumbnail for the image."""
        try:
            with Image.open(image_path) as img:
                # Convert RGBA to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                # Preserve EXIF orientation
                try:
                    from PIL import ImageOps
                    img = ImageOps.exif_transpose(img)
                except Exception:
                    pass

                # Create thumbnail
                img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                img.save(output_path, 'JPEG', quality=THUMBNAIL_QUALITY, optimize=True)
                return True
        except Exception as e:
            print(f"  Warning: Could not create thumbnail: {e}")
            return False

    def upload_file(self, local_path: Path, s3_key: str, content_type: str) -> bool:
        """Upload a file to S3."""
        try:
            self.s3.upload_file(
                str(local_path),
                PHOTOS_BUCKET,
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )
            return True
        except ClientError as e:
            print(f"  Error uploading {local_path}: {e}")
            return False

    def create_album(self, name: str, description: Optional[str] = None) -> str:
        """Create a new album in DynamoDB."""
        album_id = self.generate_id()
        now = datetime.utcnow().isoformat() + 'Z'

        item = {
            'pk': f'USER#{USER_ID}',
            'sk': f'ALBUM#{album_id}',
            'albumId': album_id,
            'userId': USER_ID,
            'name': name,
            'photoCount': 0,
            'createdAt': now,
            'updatedAt': now,
        }

        if description:
            item['description'] = description

        self.photos_table.put_item(Item=item)
        print(f"Created album: {name} (ID: {album_id})")
        return album_id

    def save_photo_metadata(self, photo_data: dict):
        """Save photo metadata to DynamoDB."""
        self.photos_table.put_item(Item=photo_data)

    def update_album_count(self, album_id: str, count: int):
        """Update the photo count for an album."""
        self.photos_table.update_item(
            Key={
                'pk': f'USER#{USER_ID}',
                'sk': f'ALBUM#{album_id}'
            },
            UpdateExpression='SET photoCount = :count, updatedAt = :now',
            ExpressionAttributeValues={
                ':count': count,
                ':now': datetime.utcnow().isoformat() + 'Z'
            }
        )

    def set_album_cover(self, album_id: str, photo_key: str):
        """Set the cover photo for an album."""
        self.photos_table.update_item(
            Key={
                'pk': f'USER#{USER_ID}',
                'sk': f'ALBUM#{album_id}'
            },
            UpdateExpression='SET coverPhotoKey = :key',
            ExpressionAttributeValues={
                ':key': photo_key
            }
        )

    def upload_folder(self, folder_path: Path, album_name: Optional[str] = None) -> dict:
        """Upload all photos from a folder to S3 as an album."""
        if not folder_path.exists():
            print(f"Error: Folder does not exist: {folder_path}")
            return {'success': False, 'error': 'Folder not found'}

        if not folder_path.is_dir():
            print(f"Error: Path is not a directory: {folder_path}")
            return {'success': False, 'error': 'Not a directory'}

        # Find all image files
        image_files = []
        for file in folder_path.iterdir():
            if file.is_file() and file.suffix.lower() in SUPPORTED_FORMATS:
                image_files.append(file)

        if not image_files:
            print(f"No supported images found in: {folder_path}")
            return {'success': False, 'error': 'No images found'}

        # Sort by name
        image_files.sort(key=lambda x: x.name.lower())

        # Use folder name as album name if not specified
        if not album_name:
            album_name = folder_path.name

        print(f"\nUploading {len(image_files)} photos to album: {album_name}")
        print("-" * 50)

        # Create album
        album_id = self.create_album(album_name)

        # Create temp directory for thumbnails
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())

        uploaded_count = 0
        cover_photo_key = None

        for idx, image_file in enumerate(image_files, 1):
            print(f"[{idx}/{len(image_files)}] {image_file.name}...", end=' ')

            photo_id = self.generate_id()
            ext = image_file.suffix.lower()
            content_type = self.get_content_type(ext)

            # S3 keys
            photo_key = f"photos/{USER_ID}/{album_id}/{photo_id}{ext}"
            thumb_key = f"thumbnails/{USER_ID}/{album_id}/{photo_id}_thumb.jpg"

            # Upload original
            if not self.upload_file(image_file, photo_key, content_type):
                print("FAILED")
                continue

            # Create and upload thumbnail
            thumb_path = temp_dir / f"{photo_id}_thumb.jpg"
            if self.create_thumbnail(image_file, thumb_path):
                self.upload_file(thumb_path, thumb_key, 'image/jpeg')
                thumb_path.unlink()  # Clean up

            # Get file size
            file_size = image_file.stat().st_size

            # Save metadata
            now = datetime.utcnow().isoformat() + 'Z'
            photo_data = {
                'pk': f'ALBUM#{album_id}',
                'sk': f'PHOTO#{photo_id}',
                'photoId': photo_id,
                'albumId': album_id,
                'userId': USER_ID,
                'filename': image_file.name,
                's3Key': photo_key,
                'thumbnailKey': thumb_key,
                'contentType': content_type,
                'size': file_size,
                'uploadDate': now,
            }
            self.save_photo_metadata(photo_data)

            # Set first photo as cover
            if cover_photo_key is None:
                cover_photo_key = thumb_key

            uploaded_count += 1
            print("OK")

        # Clean up temp directory
        try:
            temp_dir.rmdir()
        except Exception:
            pass

        # Update album
        self.update_album_count(album_id, uploaded_count)
        if cover_photo_key:
            self.set_album_cover(album_id, cover_photo_key)

        print("-" * 50)
        print(f"Uploaded {uploaded_count}/{len(image_files)} photos")
        print(f"Album ID: {album_id}")

        return {
            'success': True,
            'album_id': album_id,
            'album_name': album_name,
            'photo_count': uploaded_count,
        }

    def create_share_link(self, album_id: str, expires_in_days: Optional[int] = None) -> str:
        """Create a share link for an album."""
        link_id = self.generate_id() + self.generate_id()  # Longer ID for security
        now = datetime.utcnow()

        item = {
            'linkId': link_id,
            'albumId': album_id,
            'userId': USER_ID,
            'createdAt': now.isoformat() + 'Z',
            'accessCount': 0,
            'createdBy': USER_ID,
        }

        if expires_in_days:
            from datetime import timedelta
            expires_at = now + timedelta(days=expires_in_days)
            item['expiresAt'] = expires_at.isoformat() + 'Z'

        self.share_links_table.put_item(Item=item)

        cloudfront_domain = os.getenv('CLOUDFRONT_DOMAIN', 'your-domain.cloudfront.net')
        share_url = f"https://{cloudfront_domain}/shared/?token={link_id}"

        print(f"\nShare link created: {share_url}")
        return share_url


def main():
    parser = argparse.ArgumentParser(
        description='Upload photos from a Mac folder to the Family Photo Sharing platform'
    )
    parser.add_argument(
        'folder',
        type=str,
        help='Path to the folder containing photos'
    )
    parser.add_argument(
        '--album-name', '-n',
        type=str,
        help='Name for the album (defaults to folder name)'
    )
    parser.add_argument(
        '--share',
        action='store_true',
        help='Generate a share link after upload'
    )
    parser.add_argument(
        '--expires',
        type=int,
        help='Share link expiration in days (default: never)'
    )

    args = parser.parse_args()

    folder_path = Path(args.folder).expanduser().resolve()

    uploader = PhotoUploader()
    result = uploader.upload_folder(folder_path, args.album_name)

    if result['success'] and args.share:
        uploader.create_share_link(result['album_id'], args.expires)


if __name__ == '__main__':
    main()
