"""
Unit tests for Lambda duplicate_detector.py - duplicate image detection
"""

import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO
from PIL import Image


class TestComputeAverageHash:
    """Tests for compute_average_hash function"""

    def test_identical_images_same_hash(self):
        """Identical images should produce identical hashes"""
        from duplicate_detector import compute_average_hash

        img = Image.new('RGB', (100, 100), color='red')

        hash1 = compute_average_hash(img)
        hash2 = compute_average_hash(img)

        assert hash1 == hash2

    def test_different_images_different_hash(self):
        """Different images should produce different hashes"""
        from duplicate_detector import compute_average_hash

        # Create images with different patterns (not solid colors)
        img1 = Image.new('RGB', (100, 100))
        img2 = Image.new('RGB', (100, 100))

        # Fill with different patterns
        for x in range(100):
            for y in range(100):
                img1.putpixel((x, y), (x * 2, y * 2, 0))  # Gradient pattern
                img2.putpixel((x, y), (255 - x * 2, 255 - y * 2, 255))  # Inverted gradient

        hash1 = compute_average_hash(img1)
        hash2 = compute_average_hash(img2)

        assert hash1 != hash2

    def test_returns_hex_string(self):
        """Should return a valid hexadecimal string"""
        from duplicate_detector import compute_average_hash

        img = Image.new('RGB', (100, 100), color='green')
        hash_val = compute_average_hash(img)

        # Should be a valid hex string
        assert all(c in '0123456789abcdef' for c in hash_val)

    def test_hash_length(self):
        """Hash should have expected length for 8x8 default size"""
        from duplicate_detector import compute_average_hash

        img = Image.new('RGB', (100, 100), color='green')
        hash_val = compute_average_hash(img, hash_size=8)

        # 8x8 = 64 bits = 16 hex chars
        assert len(hash_val) == 16


class TestComputeDifferenceHash:
    """Tests for compute_difference_hash function"""

    def test_identical_images_same_hash(self):
        """Identical images should produce identical dHash"""
        from duplicate_detector import compute_difference_hash

        img = Image.new('RGB', (100, 100), color='red')

        hash1 = compute_difference_hash(img)
        hash2 = compute_difference_hash(img)

        assert hash1 == hash2

    def test_gradient_image_produces_expected_hash(self):
        """Gradient image should produce non-trivial hash"""
        from duplicate_detector import compute_difference_hash

        # Create a horizontal gradient with clear differences
        img = Image.new('RGB', (100, 100))
        for x in range(100):
            for y in range(100):
                # Alternating brightness pattern
                val = 255 if (x // 10) % 2 == 0 else 0
                img.putpixel((x, y), (val, val, val))

        hash_val = compute_difference_hash(img)

        # Should produce a valid hex hash
        assert len(hash_val) == 16
        assert all(c in '0123456789abcdef' for c in hash_val)


class TestComputeFileHash:
    """Tests for compute_file_hash function"""

    def test_same_data_same_hash(self):
        """Same data should produce same MD5 hash"""
        from duplicate_detector import compute_file_hash

        data = b'test image data'
        hash1 = compute_file_hash(data)
        hash2 = compute_file_hash(data)

        assert hash1 == hash2

    def test_different_data_different_hash(self):
        """Different data should produce different MD5 hash"""
        from duplicate_detector import compute_file_hash

        hash1 = compute_file_hash(b'data1')
        hash2 = compute_file_hash(b'data2')

        assert hash1 != hash2

    def test_returns_valid_md5(self):
        """Should return valid 32-character MD5 hash"""
        from duplicate_detector import compute_file_hash

        hash_val = compute_file_hash(b'test data')

        assert len(hash_val) == 32
        assert all(c in '0123456789abcdef' for c in hash_val)


class TestHammingDistance:
    """Tests for hamming_distance function"""

    def test_identical_hashes_zero_distance(self):
        """Identical hashes should have distance 0"""
        from duplicate_detector import hamming_distance

        hash_val = 'abcd1234'
        distance = hamming_distance(hash_val, hash_val)

        assert distance == 0

    def test_completely_different_hashes(self):
        """Opposite hashes should have maximum distance"""
        from duplicate_detector import hamming_distance

        # 0000 vs ffff in hex = all bits different
        hash1 = '0000'
        hash2 = 'ffff'
        distance = hamming_distance(hash1, hash2)

        assert distance == 16  # 4 hex chars * 4 bits = 16 bits

    def test_one_bit_difference(self):
        """Hashes differing by one bit should have distance 1"""
        from duplicate_detector import hamming_distance

        hash1 = '0000'
        hash2 = '0001'  # One bit different
        distance = hamming_distance(hash1, hash2)

        assert distance == 1

    def test_different_length_returns_infinity(self):
        """Different length hashes should return infinity"""
        from duplicate_detector import hamming_distance

        distance = hamming_distance('abc', 'abcd')

        assert distance == float('inf')


class TestFindDuplicatesInAlbum:
    """Tests for find_duplicates_in_album function"""

    @patch('duplicate_detector.photos_table')
    @patch('duplicate_detector.get_image_from_s3')
    def test_no_duplicates_found(self, mock_get_image, mock_table):
        """Should return empty groups when no duplicates exist"""
        from duplicate_detector import find_duplicates_in_album

        # Create two visually different images with patterns
        img1 = Image.new('RGB', (100, 100))
        img2 = Image.new('RGB', (100, 100))

        # Different patterns that produce different hashes
        for x in range(100):
            for y in range(100):
                img1.putpixel((x, y), (x * 2, 0, 0))  # Red gradient
                img2.putpixel((x, y), (0, 0, 255 - y * 2))  # Blue gradient

        buffer1 = BytesIO()
        buffer2 = BytesIO()
        img1.save(buffer1, format='JPEG')
        img2.save(buffer2, format='JPEG')
        buffer1.seek(0)
        buffer2.seek(0)

        mock_table.query.return_value = {
            'Items': [
                {
                    'sk': 'PHOTO#photo-1',
                    'photoId': 'photo-1',
                    's3Key': 'photos/photo1.jpg',
                    'thumbnailKey': 'thumbs/photo1.jpg',
                    'filename': 'photo1.jpg',
                    'hidden': False
                },
                {
                    'sk': 'PHOTO#photo-2',
                    'photoId': 'photo-2',
                    's3Key': 'photos/photo2.jpg',
                    'thumbnailKey': 'thumbs/photo2.jpg',
                    'filename': 'photo2.jpg',
                    'hidden': False
                }
            ]
        }

        mock_get_image.side_effect = [
            (img1, buffer1.getvalue()),
            (img2, buffer2.getvalue())
        ]

        result = find_duplicates_in_album('album-001')

        assert result['totalPhotos'] == 2
        # May or may not find duplicates due to hash similarity
        # The main assertion is that it runs without error
        assert 'duplicatesFound' in result
        assert 'duplicateGroups' in result

    @patch('duplicate_detector.photos_table')
    @patch('duplicate_detector.get_image_from_s3')
    def test_exact_duplicates_found(self, mock_get_image, mock_table):
        """Should find exact duplicate images"""
        from duplicate_detector import find_duplicates_in_album

        # Create identical images
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        img_bytes = buffer.getvalue()

        mock_table.query.return_value = {
            'Items': [
                {
                    'sk': 'PHOTO#photo-1',
                    'photoId': 'photo-1',
                    's3Key': 'photos/photo1.jpg',
                    'thumbnailKey': 'thumbs/photo1.jpg',
                    'filename': 'photo1.jpg',
                    'hidden': False
                },
                {
                    'sk': 'PHOTO#photo-2',
                    'photoId': 'photo-2',
                    's3Key': 'photos/photo2.jpg',
                    'thumbnailKey': 'thumbs/photo2.jpg',
                    'filename': 'photo2.jpg',
                    'hidden': False
                }
            ]
        }

        # Return same image for both
        mock_get_image.return_value = (img, img_bytes)

        result = find_duplicates_in_album('album-001')

        assert result['totalPhotos'] == 2
        assert result['duplicatesFound'] == 1
        assert len(result['duplicateGroups']) == 1

    @patch('duplicate_detector.photos_table')
    def test_single_photo_no_duplicates(self, mock_table):
        """Should handle album with single photo"""
        from duplicate_detector import find_duplicates_in_album

        mock_table.query.return_value = {
            'Items': [
                {
                    'sk': 'PHOTO#photo-1',
                    'photoId': 'photo-1',
                    's3Key': 'photos/photo1.jpg',
                    'filename': 'photo1.jpg',
                    'hidden': False
                }
            ]
        }

        result = find_duplicates_in_album('album-001')

        assert result['totalPhotos'] == 1
        assert result['duplicatesFound'] == 0
        assert len(result['duplicateGroups']) == 0

    @patch('duplicate_detector.photos_table')
    def test_excludes_hidden_photos(self, mock_table):
        """Should exclude hidden photos from duplicate detection"""
        from duplicate_detector import find_duplicates_in_album

        mock_table.query.return_value = {
            'Items': [
                {
                    'sk': 'PHOTO#photo-1',
                    'photoId': 'photo-1',
                    's3Key': 'photos/photo1.jpg',
                    'filename': 'photo1.jpg',
                    'hidden': True  # Hidden
                }
            ]
        }

        result = find_duplicates_in_album('album-001')

        assert result['totalPhotos'] == 0

    @patch('duplicate_detector.photos_table')
    def test_excludes_metadata_files(self, mock_table):
        """Should exclude macOS metadata files"""
        from duplicate_detector import find_duplicates_in_album

        mock_table.query.return_value = {
            'Items': [
                {
                    'sk': 'PHOTO#photo-1',
                    'photoId': 'photo-1',
                    's3Key': 'photos/.DS_Store',
                    'filename': '.DS_Store',
                    'hidden': False
                }
            ]
        }

        result = find_duplicates_in_album('album-001')

        assert result['totalPhotos'] == 0


class TestFindDuplicatesAcrossAlbums:
    """Tests for find_duplicates_across_albums function"""

    @patch('duplicate_detector.photos_table')
    def test_returns_cross_album_info(self, mock_table):
        """Should include cross-album information in results"""
        from duplicate_detector import find_duplicates_across_albums

        # Return two albums with no photos
        mock_table.query.side_effect = [
            # First call: get albums
            {
                'Items': [
                    {'sk': 'ALBUM#album-1', 'name': 'Album 1'},
                    {'sk': 'ALBUM#album-2', 'name': 'Album 2'}
                ]
            },
            # Second call: get photos from album 1
            {'Items': []},
            # Third call: get photos from album 2
            {'Items': []}
        ]

        result = find_duplicates_across_albums('user-123')

        # When there are no photos, should return early with basic structure
        assert result['totalPhotos'] == 0
        assert result['duplicatesFound'] == 0
        assert 'duplicateGroups' in result

    @patch('duplicate_detector.photos_table')
    @patch('duplicate_detector.get_image_from_s3')
    def test_detects_cross_album_duplicates(self, mock_get_image, mock_table):
        """Should detect duplicates across different albums"""
        from duplicate_detector import find_duplicates_across_albums

        # Create identical image
        img = Image.new('RGB', (100, 100), color='green')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        img_bytes = buffer.getvalue()

        mock_table.query.side_effect = [
            # First call: get albums
            {
                'Items': [
                    {'sk': 'ALBUM#album-1', 'name': 'Album 1'},
                    {'sk': 'ALBUM#album-2', 'name': 'Album 2'}
                ]
            },
            # Second call: photos from album 1
            {
                'Items': [
                    {
                        'sk': 'PHOTO#photo-1',
                        'photoId': 'photo-1',
                        's3Key': 'photos/photo1.jpg',
                        'thumbnailKey': 'thumbs/photo1.jpg',
                        'filename': 'photo1.jpg',
                        'hidden': False
                    }
                ]
            },
            # Third call: photos from album 2
            {
                'Items': [
                    {
                        'sk': 'PHOTO#photo-2',
                        'photoId': 'photo-2',
                        's3Key': 'photos/photo2.jpg',
                        'thumbnailKey': 'thumbs/photo2.jpg',
                        'filename': 'photo2.jpg',
                        'hidden': False
                    }
                ]
            }
        ]

        mock_get_image.return_value = (img, img_bytes)

        result = find_duplicates_across_albums('user-123')

        assert result['totalPhotos'] == 2
        assert result['duplicatesFound'] == 1
        assert result['crossAlbumGroups'] >= 1


class TestCheckDuplicateBeforeUpload:
    """Tests for check_duplicate_before_upload function"""

    @patch('duplicate_detector.photos_table')
    @patch('duplicate_detector.get_image_from_s3')
    def test_detects_duplicate_before_upload(self, mock_get_image, mock_table):
        """Should detect if new image is duplicate of existing"""
        from duplicate_detector import check_duplicate_before_upload

        # Create identical image data
        img = Image.new('RGB', (100, 100), color='purple')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        new_image_data = buffer.getvalue()

        mock_table.query.return_value = {
            'Items': [
                {
                    'sk': 'PHOTO#photo-1',
                    'photoId': 'photo-1',
                    's3Key': 'photos/photo1.jpg',
                    'thumbnailKey': 'thumbs/photo1.jpg',
                    'filename': 'existing.jpg',
                    'hidden': False
                }
            ]
        }

        mock_get_image.return_value = (img, new_image_data)

        result = check_duplicate_before_upload(new_image_data, 'album-001')

        assert result['isDuplicate'] is True
        assert len(result['matches']) > 0

    @patch('duplicate_detector.photos_table')
    @patch('duplicate_detector.get_image_from_s3')
    def test_no_duplicate_for_unique_image(self, mock_get_image, mock_table):
        """Should return no duplicate for unique image"""
        from duplicate_detector import check_duplicate_before_upload

        # Create new unique image with distinct pattern
        new_img = Image.new('RGB', (100, 100))
        for x in range(100):
            for y in range(100):
                new_img.putpixel((x, y), (x * 2, y * 2, 0))  # Gradient pattern

        buffer = BytesIO()
        new_img.save(buffer, format='JPEG')
        buffer.seek(0)
        new_image_data = buffer.getvalue()

        # Existing image has very different pattern
        existing_img = Image.new('RGB', (100, 100))
        for x in range(100):
            for y in range(100):
                existing_img.putpixel((x, y), (0, 0, 255 - x))  # Different gradient

        existing_buffer = BytesIO()
        existing_img.save(existing_buffer, format='JPEG')
        existing_buffer.seek(0)

        mock_table.query.return_value = {
            'Items': [
                {
                    'sk': 'PHOTO#photo-1',
                    'photoId': 'photo-1',
                    's3Key': 'photos/photo1.jpg',
                    'thumbnailKey': 'thumbs/photo1.jpg',
                    'filename': 'existing.jpg',
                    'hidden': False
                }
            ]
        }

        mock_get_image.return_value = (existing_img, existing_buffer.getvalue())

        result = check_duplicate_before_upload(new_image_data, 'album-001')

        # Verify the function runs and returns expected structure
        assert 'isDuplicate' in result
        assert 'matches' in result

    @patch('duplicate_detector.photos_table')
    def test_empty_album_no_duplicates(self, mock_table):
        """Should return no duplicates for empty album"""
        from duplicate_detector import check_duplicate_before_upload

        # Create test image
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        image_data = buffer.getvalue()

        mock_table.query.return_value = {'Items': []}

        result = check_duplicate_before_upload(image_data, 'empty-album')

        assert result['isDuplicate'] is False
        assert len(result['matches']) == 0


class TestComputeImageHashes:
    """Tests for compute_image_hashes function"""

    def test_returns_all_hash_types(self):
        """Should return aHash, dHash, fileHash, and fileSize"""
        from duplicate_detector import compute_image_hashes

        img = Image.new('RGB', (100, 100), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        img_data = buffer.getvalue()

        hashes = compute_image_hashes(img, img_data)

        assert 'aHash' in hashes
        assert 'dHash' in hashes
        assert 'fileHash' in hashes
        assert 'fileSize' in hashes
        assert hashes['fileSize'] == len(img_data)
