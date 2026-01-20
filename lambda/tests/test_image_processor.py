"""
Unit tests for Lambda image_processor.py - image editing operations
"""

import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO
from PIL import Image


class TestGetPhotoMetadata:
    """Tests for get_photo_metadata function"""

    @patch('image_processor.photos_table')
    def test_finds_photo_by_id(self, mock_table):
        """Should find photo metadata by photo ID"""
        from image_processor import get_photo_metadata

        mock_table.scan.return_value = {
            'Items': [
                {
                    'pk': 'ALBUM#album-001',
                    'sk': 'PHOTO#photo-123',
                    'photoId': 'photo-123',
                    's3Key': 'photos/photo.jpg'
                }
            ]
        }

        result = get_photo_metadata('photo-123')

        assert result is not None
        assert result['photoId'] == 'photo-123'

    @patch('image_processor.photos_table')
    def test_returns_none_for_missing_photo(self, mock_table):
        """Should return None when photo not found"""
        from image_processor import get_photo_metadata

        mock_table.scan.return_value = {'Items': []}

        result = get_photo_metadata('nonexistent')

        assert result is None


class TestCreateThumbnail:
    """Tests for create_thumbnail function"""

    def test_creates_smaller_image(self):
        """Should create a smaller thumbnail"""
        from image_processor import create_thumbnail

        original = Image.new('RGB', (1000, 1000), color='red')
        thumbnail = create_thumbnail(original, max_size=(200, 200))

        assert thumbnail.width <= 200
        assert thumbnail.height <= 200

    def test_preserves_aspect_ratio(self):
        """Should preserve aspect ratio"""
        from image_processor import create_thumbnail

        # 2:1 aspect ratio
        original = Image.new('RGB', (1000, 500), color='blue')
        thumbnail = create_thumbnail(original, max_size=(200, 200))

        # Should maintain 2:1 ratio
        ratio = thumbnail.width / thumbnail.height
        assert abs(ratio - 2.0) < 0.1

    def test_does_not_modify_original(self):
        """Should not modify the original image"""
        from image_processor import create_thumbnail

        original = Image.new('RGB', (500, 500), color='green')
        original_size = original.size

        create_thumbnail(original, max_size=(100, 100))

        assert original.size == original_size


class TestEnhanceWithPillow:
    """Tests for _enhance_with_pillow function"""

    def test_applies_brightness(self):
        """Should apply brightness enhancement"""
        from image_processor import _enhance_with_pillow

        img = Image.new('RGB', (100, 100), color='gray')
        enhanced = _enhance_with_pillow(img, {'brightness': 1.5})

        # Enhanced image should be different
        assert enhanced.size == img.size

    def test_applies_contrast(self):
        """Should apply contrast enhancement"""
        from image_processor import _enhance_with_pillow

        img = Image.new('RGB', (100, 100), color='gray')
        enhanced = _enhance_with_pillow(img, {'contrast': 1.5})

        assert enhanced.size == img.size

    def test_applies_all_enhancements(self):
        """Should apply all enhancement parameters"""
        from image_processor import _enhance_with_pillow

        img = Image.new('RGB', (100, 100), color='gray')
        params = {
            'brightness': 1.1,
            'contrast': 1.2,
            'saturation': 1.3,
            'sharpness': 1.4
        }
        enhanced = _enhance_with_pillow(img, params)

        assert enhanced.size == img.size


class TestStyleTransferWithPillow:
    """Tests for _style_transfer_with_pillow function"""

    def test_watercolor_style(self):
        """Should apply watercolor style"""
        from image_processor import _style_transfer_with_pillow

        img = Image.new('RGB', (100, 100), color='red')
        styled = _style_transfer_with_pillow(img, 'watercolor')

        assert styled.size == img.size

    def test_oil_painting_style(self):
        """Should apply oil painting style"""
        from image_processor import _style_transfer_with_pillow

        img = Image.new('RGB', (100, 100), color='blue')
        styled = _style_transfer_with_pillow(img, 'oil_painting')

        assert styled.size == img.size

    def test_sketch_style(self):
        """Should apply sketch style"""
        from image_processor import _style_transfer_with_pillow

        img = Image.new('RGB', (100, 100), color='green')
        styled = _style_transfer_with_pillow(img, 'sketch')

        assert styled.size == img.size
        assert styled.mode == 'RGB'

    def test_anime_style(self):
        """Should apply anime style"""
        from image_processor import _style_transfer_with_pillow

        img = Image.new('RGB', (100, 100), color='yellow')
        styled = _style_transfer_with_pillow(img, 'anime')

        assert styled.size == img.size

    def test_pop_art_style(self):
        """Should apply pop art style"""
        from image_processor import _style_transfer_with_pillow

        img = Image.new('RGB', (100, 100), color='purple')
        styled = _style_transfer_with_pillow(img, 'pop_art')

        assert styled.size == img.size

    def test_impressionist_style(self):
        """Should apply impressionist style"""
        from image_processor import _style_transfer_with_pillow

        img = Image.new('RGB', (100, 100), color='cyan')
        styled = _style_transfer_with_pillow(img, 'impressionist')

        assert styled.size == img.size

    def test_default_style(self):
        """Should apply default style for unknown style"""
        from image_processor import _style_transfer_with_pillow

        img = Image.new('RGB', (100, 100), color='white')
        styled = _style_transfer_with_pillow(img, 'unknown')

        assert styled.size == img.size


class TestResizeForBedrock:
    """Tests for _resize_for_bedrock function"""

    def test_resizes_large_image(self):
        """Should resize image that exceeds max pixels"""
        from image_processor import _resize_for_bedrock

        # 2000x2000 = 4M pixels
        large_img = Image.new('RGB', (2000, 2000), color='red')
        resized = _resize_for_bedrock(large_img, max_pixels=1000000)

        total_pixels = resized.width * resized.height
        assert total_pixels <= 1000000

    def test_preserves_small_image(self):
        """Should not resize image under max pixels"""
        from image_processor import _resize_for_bedrock

        small_img = Image.new('RGB', (100, 100), color='blue')
        resized = _resize_for_bedrock(small_img, max_pixels=1000000)

        assert resized.size == small_img.size

    def test_preserves_aspect_ratio(self):
        """Should preserve aspect ratio when resizing"""
        from image_processor import _resize_for_bedrock

        # 2:1 aspect ratio
        img = Image.new('RGB', (2000, 1000), color='green')
        resized = _resize_for_bedrock(img, max_pixels=100000)

        ratio = resized.width / resized.height
        assert abs(ratio - 2.0) < 0.1


class TestRotateImage:
    """Tests for rotate_image function"""

    @patch('image_processor.get_photo_metadata')
    @patch('image_processor.download_image_from_s3')
    @patch('image_processor.save_edited_photo')
    def test_rotates_90_degrees(self, mock_save, mock_download, mock_meta):
        """Should rotate image 90 degrees"""
        from image_processor import rotate_image

        mock_meta.return_value = {
            'photoId': 'photo-123',
            's3Key': 'photos/photo.jpg',
            'albumId': 'album-001',
            'filename': 'test.jpg'
        }
        mock_download.return_value = Image.new('RGB', (100, 50), color='red')
        mock_save.return_value = {'photoId': 'new-photo'}

        result = rotate_image('photo-123', 90)

        mock_save.assert_called_once()
        call_args = mock_save.call_args[1]
        assert call_args['edit_operation'] == 'rotated'
        assert call_args['edit_parameters']['angle'] == 90

    def test_rejects_invalid_angle(self):
        """Should reject invalid rotation angles"""
        from image_processor import rotate_image

        with pytest.raises(ValueError, match='Invalid rotation angle'):
            rotate_image('photo-123', 45)

    @patch('image_processor.get_photo_metadata')
    def test_raises_error_for_missing_photo(self, mock_meta):
        """Should raise error when photo not found"""
        from image_processor import rotate_image

        mock_meta.return_value = None

        with pytest.raises(ValueError, match='Photo not found'):
            rotate_image('nonexistent', 90)


class TestUpscaleImage:
    """Tests for upscale_image function"""

    def test_rejects_invalid_scale_factor(self):
        """Should reject invalid scale factors"""
        from image_processor import upscale_image

        with pytest.raises(ValueError, match='Invalid scale factor'):
            upscale_image('photo-123', 3)

    @patch('image_processor.get_photo_metadata')
    def test_raises_error_for_missing_photo(self, mock_meta):
        """Should raise error when photo not found"""
        from image_processor import upscale_image

        mock_meta.return_value = None

        with pytest.raises(ValueError, match='Photo not found'):
            upscale_image('nonexistent', 2)


class TestStyleTransfer:
    """Tests for style_transfer function"""

    def test_rejects_invalid_style(self):
        """Should reject invalid style names"""
        from image_processor import style_transfer

        with pytest.raises(ValueError, match='Invalid style'):
            style_transfer('photo-123', 'invalid_style')

    @patch('image_processor.get_photo_metadata')
    def test_raises_error_for_missing_photo(self, mock_meta):
        """Should raise error when photo not found"""
        from image_processor import style_transfer

        mock_meta.return_value = None

        with pytest.raises(ValueError, match='Photo not found'):
            style_transfer('nonexistent', 'watercolor')


class TestProcessImageEdit:
    """Tests for process_image_edit function - main entry point"""

    @patch('image_processor.rotate_image')
    def test_routes_rotate_operation(self, mock_rotate):
        """Should route rotate operation correctly"""
        from image_processor import process_image_edit

        mock_rotate.return_value = {'photoId': 'new-id'}

        process_image_edit('photo-123', 'rotate', {'angle': 90})

        mock_rotate.assert_called_once_with('photo-123', 90)

    @patch('image_processor.enhance_image')
    def test_routes_enhance_operation(self, mock_enhance):
        """Should route enhance operation correctly"""
        from image_processor import process_image_edit

        mock_enhance.return_value = {'photoId': 'new-id'}

        process_image_edit('photo-123', 'enhance', {'brightness': 1.2})

        mock_enhance.assert_called_once()

    @patch('image_processor.upscale_image')
    def test_routes_upscale_operation(self, mock_upscale):
        """Should route upscale operation correctly"""
        from image_processor import process_image_edit

        mock_upscale.return_value = {'photoId': 'new-id'}

        process_image_edit('photo-123', 'upscale', {'scale': 2})

        mock_upscale.assert_called_once_with('photo-123', 2)

    @patch('image_processor.remove_background')
    def test_routes_remove_bg_operation(self, mock_remove_bg):
        """Should route remove_bg operation correctly"""
        from image_processor import process_image_edit

        mock_remove_bg.return_value = {'photoId': 'new-id'}

        process_image_edit('photo-123', 'remove_bg', {})

        mock_remove_bg.assert_called_once_with('photo-123')

    @patch('image_processor.style_transfer')
    def test_routes_style_transfer_operation(self, mock_style):
        """Should route style_transfer operation correctly"""
        from image_processor import process_image_edit

        mock_style.return_value = {'photoId': 'new-id'}

        process_image_edit('photo-123', 'style_transfer', {'style': 'anime'})

        mock_style.assert_called_once_with('photo-123', 'anime')

    def test_raises_error_for_unknown_operation(self):
        """Should raise error for unknown operation"""
        from image_processor import process_image_edit

        with pytest.raises(ValueError, match='Unknown operation'):
            process_image_edit('photo-123', 'unknown_op', {})


class TestUploadImageToS3:
    """Tests for upload_image_to_s3 function"""

    @patch('image_processor.s3')
    def test_uploads_jpeg_image(self, mock_s3):
        """Should upload JPEG image with correct content type"""
        from image_processor import upload_image_to_s3

        img = Image.new('RGB', (100, 100), color='red')
        upload_image_to_s3(img, 'photos/test.jpg', 'image/jpeg')

        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs['ContentType'] == 'image/jpeg'
        assert call_kwargs['Key'] == 'photos/test.jpg'

    @patch('image_processor.s3')
    def test_uploads_png_image(self, mock_s3):
        """Should upload PNG image with correct content type"""
        from image_processor import upload_image_to_s3

        img = Image.new('RGBA', (100, 100), color='blue')
        upload_image_to_s3(img, 'photos/test.png', 'image/png')

        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs['ContentType'] == 'image/png'

    @patch('image_processor.s3')
    def test_converts_rgba_to_rgb_for_jpeg(self, mock_s3):
        """Should convert RGBA to RGB when saving as JPEG"""
        from image_processor import upload_image_to_s3

        # RGBA image
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        upload_image_to_s3(img, 'photos/test.jpg', 'image/jpeg')

        # Should succeed without error (JPEG can't have alpha)
        mock_s3.put_object.assert_called_once()


class TestSaveEditedPhoto:
    """Tests for save_edited_photo function"""

    @patch('image_processor.photos_table')
    @patch('image_processor.upload_image_to_s3')
    def test_saves_edited_photo_metadata(self, mock_upload, mock_table):
        """Should save edited photo and create DynamoDB entries"""
        from image_processor import save_edited_photo

        original = {
            'albumId': 'album-001',
            'photoId': 'orig-photo',
            'filename': 'test.jpg',
            'sk': 'PHOTO#orig-photo'
        }
        edited_img = Image.new('RGB', (100, 100), color='green')

        result = save_edited_photo(
            original_photo=original,
            edited_image=edited_img,
            edit_operation='enhanced',
            edit_parameters={'brightness': 1.2},
            user_id='user-123'
        )

        assert 'photoId' in result
        assert 'url' in result
        assert 'thumbnailUrl' in result
        assert result['editOperation'] == 'enhanced'
        # Should upload both photo and thumbnail
        assert mock_upload.call_count == 2
        # Should create album and date entries
        assert mock_table.put_item.call_count == 2

    @patch('image_processor.photos_table')
    @patch('image_processor.upload_image_to_s3')
    def test_uses_png_for_remove_bg(self, mock_upload, mock_table):
        """Should use PNG format for remove_bg operation"""
        from image_processor import save_edited_photo

        original = {
            'albumId': 'album-001',
            'photoId': 'orig-photo',
            'filename': 'test.jpg',
            'sk': 'PHOTO#orig-photo'
        }
        edited_img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 0))

        result = save_edited_photo(
            original_photo=original,
            edited_image=edited_img,
            edit_operation='remove_bg',
            edit_parameters={},
            user_id='user-123'
        )

        assert result['filename'].endswith('.png')
