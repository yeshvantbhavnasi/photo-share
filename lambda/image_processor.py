"""
Image Processing Module for Bhavnasi Share

Handles image editing operations including:
- Rotation (Pillow-based, no AI)
- Auto-enhance (AWS Bedrock + Stability AI)
- AI Upscaling (AWS Bedrock + Stability AI)
- Background removal (AWS Bedrock + Stability AI)
- Style transfer (AWS Bedrock + Stability AI)
"""

import os
import io
import json
import uuid
import base64
from datetime import datetime
from PIL import Image, ImageEnhance
import boto3
from boto3.dynamodb.conditions import Key

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Configuration
PHOTOS_BUCKET = os.environ.get('PHOTOS_BUCKET', 'bhavnasi-family-photos')
PHOTOS_TABLE_NAME = os.environ.get('PHOTOS_TABLE', 'PhotosMetadata')
CLOUDFRONT_DOMAIN = os.environ.get('CLOUDFRONT_DOMAIN', 'd1nf5k4wr11svj.cloudfront.net')

photos_table = dynamodb.Table(PHOTOS_TABLE_NAME)

# Bedrock client (lazy initialization)
_bedrock_client = None

def get_bedrock_client():
    """Get or create Bedrock client"""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
    return _bedrock_client


def get_photo_metadata(photo_id):
    """Get photo metadata from DynamoDB by scanning for the photo ID"""
    # Query for the photo across all albums
    response = photos_table.scan(
        FilterExpression='photoId = :pid OR contains(sk, :photo_sk)',
        ExpressionAttributeValues={
            ':pid': photo_id,
            ':photo_sk': f'PHOTO#{photo_id}'
        }
    )

    items = response.get('Items', [])
    for item in items:
        if item.get('sk', '').startswith('PHOTO#') or item.get('photoId') == photo_id:
            return item
    return None


def download_image_from_s3(s3_key):
    """Download image from S3 and return as PIL Image"""
    response = s3.get_object(Bucket=PHOTOS_BUCKET, Key=s3_key)
    image_data = response['Body'].read()
    return Image.open(io.BytesIO(image_data))


def upload_image_to_s3(image, s3_key, content_type='image/jpeg'):
    """Upload PIL Image to S3"""
    buffer = io.BytesIO()

    # Determine format from content type or key
    if content_type == 'image/png' or s3_key.endswith('.png'):
        format_type = 'PNG'
    else:
        format_type = 'JPEG'
        # Convert RGBA to RGB for JPEG
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background

    image.save(buffer, format=format_type, quality=95)
    buffer.seek(0)

    s3.put_object(
        Bucket=PHOTOS_BUCKET,
        Key=s3_key,
        Body=buffer.getvalue(),
        ContentType=content_type
    )


def create_thumbnail(image, max_size=(400, 400)):
    """Create thumbnail from PIL Image"""
    thumbnail = image.copy()
    thumbnail.thumbnail(max_size, Image.Resampling.LANCZOS)
    return thumbnail


def save_edited_photo(
    original_photo,
    edited_image,
    edit_operation,
    edit_parameters=None,
    user_id='default-user'
):
    """Save edited image and create DynamoDB entry

    Returns the new photo metadata
    """
    album_id = original_photo.get('albumId')
    original_photo_id = original_photo.get('photoId') or original_photo['sk'].replace('PHOTO#', '')
    original_filename = original_photo.get('filename', 'photo.jpg')

    # Generate new photo ID
    new_photo_id = str(uuid.uuid4())

    # Determine file extension based on operation
    if edit_operation == 'remove_bg':
        extension = '.png'
        content_type = 'image/png'
    else:
        # Keep original extension or default to jpg
        extension = '.' + original_filename.rsplit('.', 1)[-1] if '.' in original_filename else '.jpg'
        content_type = 'image/jpeg' if extension.lower() in ['.jpg', '.jpeg'] else 'image/png'

    # Generate new filename
    base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
    new_filename = f"{base_name}_{edit_operation}{extension}"

    # S3 paths
    s3_key = f"edited/{user_id}/{album_id}/{new_photo_id}{extension}"
    thumbnail_key = f"thumbnails/{user_id}/{album_id}/{new_photo_id}_thumb{extension}"

    # Upload edited image
    upload_image_to_s3(edited_image, s3_key, content_type)

    # Create and upload thumbnail
    thumbnail = create_thumbnail(edited_image)
    upload_image_to_s3(thumbnail, thumbnail_key, content_type)

    # Current timestamp
    now = datetime.utcnow().isoformat() + 'Z'

    # Create DynamoDB entry for the edited photo
    photo_item = {
        'pk': f'ALBUM#{album_id}',
        'sk': f'PHOTO#{new_photo_id}',
        'photoId': new_photo_id,
        'albumId': album_id,
        'originalPhotoId': original_photo_id,
        'filename': new_filename,
        's3Key': s3_key,
        'thumbnailKey': thumbnail_key,
        'editOperation': edit_operation,
        'editParameters': edit_parameters or {},
        'uploadDate': now,
        'contentType': content_type,
        'size': edited_image.size[0] * edited_image.size[1]  # Approximate
    }

    photos_table.put_item(Item=photo_item)

    # Also create a DATE# entry for timeline view
    date_str = now[:10]  # YYYY-MM-DD
    date_item = {
        'pk': f'USER#{user_id}',
        'sk': f'DATE#{date_str}#PHOTO#{new_photo_id}',
        'photoId': new_photo_id,
        'albumId': album_id,
        'filename': new_filename,
        's3Key': s3_key,
        'thumbnailKey': thumbnail_key,
        'uploadDate': now,
        'contentType': content_type
    }
    photos_table.put_item(Item=date_item)

    # Return new photo metadata
    return {
        'id': new_photo_id,
        'photoId': new_photo_id,
        'filename': new_filename,
        'url': f"https://{CLOUDFRONT_DOMAIN}/{s3_key}",
        'thumbnailUrl': f"https://{CLOUDFRONT_DOMAIN}/{thumbnail_key}",
        'uploadDate': now,
        'editOperation': edit_operation,
        'originalPhotoId': original_photo_id
    }


def rotate_image(photo_id, angle):
    """Rotate image using Pillow (no AI needed)

    Args:
        photo_id: ID of the photo to rotate
        angle: Rotation angle (90, 180, or 270)

    Returns:
        New photo metadata dict
    """
    # Validate angle
    if angle not in [90, 180, 270]:
        raise ValueError(f"Invalid rotation angle: {angle}. Must be 90, 180, or 270.")

    # Get original photo metadata
    photo_meta = get_photo_metadata(photo_id)
    if not photo_meta:
        raise ValueError(f"Photo not found: {photo_id}")

    # Download original image
    s3_key = photo_meta.get('s3Key')
    image = download_image_from_s3(s3_key)

    # Rotate (PIL rotates counter-clockwise, so negate for clockwise)
    rotated = image.rotate(-angle, expand=True)

    # Save and return
    return save_edited_photo(
        original_photo=photo_meta,
        edited_image=rotated,
        edit_operation='rotated',
        edit_parameters={'angle': angle}
    )


def enhance_image(photo_id, parameters=None):
    """Auto-enhance image using Stability AI via Bedrock

    If Bedrock is not available, falls back to basic Pillow enhancements.

    Args:
        photo_id: ID of the photo to enhance
        parameters: Optional dict with enhancement params

    Returns:
        New photo metadata dict
    """
    params = parameters or {}

    # Get original photo metadata
    photo_meta = get_photo_metadata(photo_id)
    if not photo_meta:
        raise ValueError(f"Photo not found: {photo_id}")

    # Download original image
    s3_key = photo_meta.get('s3Key')
    image = download_image_from_s3(s3_key)

    try:
        # Try Bedrock Stability AI enhancement
        enhanced = _enhance_with_bedrock(image, params)
    except Exception as e:
        print(f"Bedrock enhancement failed, using fallback: {e}")
        # Fallback to basic Pillow enhancement
        enhanced = _enhance_with_pillow(image, params)

    return save_edited_photo(
        original_photo=photo_meta,
        edited_image=enhanced,
        edit_operation='enhanced',
        edit_parameters=params
    )


def _enhance_with_pillow(image, params):
    """Basic image enhancement using Pillow"""
    # Apply brightness adjustment
    brightness = params.get('brightness', 1.05)
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(brightness)

    # Apply contrast adjustment
    contrast = params.get('contrast', 1.1)
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(contrast)

    # Apply color saturation
    saturation = params.get('saturation', 1.1)
    enhancer = ImageEnhance.Color(image)
    image = enhancer.enhance(saturation)

    # Apply sharpness
    sharpness = params.get('sharpness', 1.1)
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(sharpness)

    return image


def _enhance_with_bedrock(image, params):
    """Enhance image using Stability AI via Bedrock"""
    bedrock = get_bedrock_client()

    # Convert image to base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Call Stability AI for enhancement
    response = bedrock.invoke_model(
        modelId='stability.stable-diffusion-xl-v1',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            'text_prompts': [
                {'text': 'enhance photo quality, improve lighting, color correction, high quality', 'weight': 1.0},
                {'text': 'blurry, low quality, distorted', 'weight': -1.0}
            ],
            'init_image': image_base64,
            'init_image_mode': 'IMAGE_STRENGTH',
            'image_strength': 0.35,  # Lower = keep more of original
            'cfg_scale': 7,
            'samples': 1,
            'steps': 30
        })
    )

    response_body = json.loads(response['body'].read())

    # Decode result image
    result_base64 = response_body['artifacts'][0]['base64']
    result_data = base64.b64decode(result_base64)

    return Image.open(io.BytesIO(result_data))


def upscale_image(photo_id, scale_factor=2):
    """Upscale image using Stability AI via Bedrock

    Args:
        photo_id: ID of the photo to upscale
        scale_factor: Upscale factor (2 or 4)

    Returns:
        New photo metadata dict
    """
    if scale_factor not in [2, 4]:
        raise ValueError(f"Invalid scale factor: {scale_factor}. Must be 2 or 4.")

    # Get original photo metadata
    photo_meta = get_photo_metadata(photo_id)
    if not photo_meta:
        raise ValueError(f"Photo not found: {photo_id}")

    # Download original image
    s3_key = photo_meta.get('s3Key')
    image = download_image_from_s3(s3_key)

    try:
        upscaled = _upscale_with_bedrock(image, scale_factor)
    except Exception as e:
        print(f"Bedrock upscale failed, using fallback: {e}")
        # Fallback to Pillow resize
        new_size = (image.width * scale_factor, image.height * scale_factor)
        upscaled = image.resize(new_size, Image.Resampling.LANCZOS)

    return save_edited_photo(
        original_photo=photo_meta,
        edited_image=upscaled,
        edit_operation='upscaled',
        edit_parameters={'scale': scale_factor}
    )


def _upscale_with_bedrock(image, scale_factor):
    """Upscale image using Stability AI via Bedrock"""
    bedrock = get_bedrock_client()

    # Convert image to base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Calculate target dimensions
    target_width = image.width * scale_factor
    target_height = image.height * scale_factor

    # Call Stability AI for upscaling
    response = bedrock.invoke_model(
        modelId='stability.stable-diffusion-xl-v1',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            'text_prompts': [
                {'text': 'high resolution, detailed, sharp, 4k quality', 'weight': 1.0}
            ],
            'init_image': image_base64,
            'init_image_mode': 'IMAGE_STRENGTH',
            'image_strength': 0.2,  # Keep most of original
            'width': min(target_width, 1024),  # SDXL max
            'height': min(target_height, 1024),
            'cfg_scale': 7,
            'samples': 1,
            'steps': 25
        })
    )

    response_body = json.loads(response['body'].read())
    result_base64 = response_body['artifacts'][0]['base64']
    result_data = base64.b64decode(result_base64)

    return Image.open(io.BytesIO(result_data))


def remove_background(photo_id):
    """Remove background from image using Stability AI via Bedrock

    Args:
        photo_id: ID of the photo

    Returns:
        New photo metadata dict (PNG with transparency)
    """
    # Get original photo metadata
    photo_meta = get_photo_metadata(photo_id)
    if not photo_meta:
        raise ValueError(f"Photo not found: {photo_id}")

    # Download original image
    s3_key = photo_meta.get('s3Key')
    image = download_image_from_s3(s3_key)

    try:
        result = _remove_bg_with_bedrock(image)
    except Exception as e:
        raise ValueError(f"Background removal failed: {e}")

    return save_edited_photo(
        original_photo=photo_meta,
        edited_image=result,
        edit_operation='remove_bg',
        edit_parameters={}
    )


def _remove_bg_with_bedrock(image):
    """Remove background using Stability AI via Bedrock"""
    bedrock = get_bedrock_client()

    # Convert image to base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Use image-to-image with masking prompt
    response = bedrock.invoke_model(
        modelId='stability.stable-diffusion-xl-v1',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            'text_prompts': [
                {'text': 'subject only, transparent background, isolated object, no background', 'weight': 1.0},
                {'text': 'background, scenery, environment', 'weight': -1.0}
            ],
            'init_image': image_base64,
            'init_image_mode': 'IMAGE_STRENGTH',
            'image_strength': 0.5,
            'cfg_scale': 10,
            'samples': 1,
            'steps': 40
        })
    )

    response_body = json.loads(response['body'].read())
    result_base64 = response_body['artifacts'][0]['base64']
    result_data = base64.b64decode(result_base64)

    return Image.open(io.BytesIO(result_data))


def style_transfer(photo_id, style):
    """Apply artistic style to image using Stability AI via Bedrock

    Args:
        photo_id: ID of the photo
        style: Style name (watercolor, oil_painting, sketch, anime, etc.)

    Returns:
        New photo metadata dict
    """
    valid_styles = ['watercolor', 'oil_painting', 'sketch', 'anime', 'pop_art', 'impressionist']
    if style not in valid_styles:
        raise ValueError(f"Invalid style: {style}. Valid options: {valid_styles}")

    # Get original photo metadata
    photo_meta = get_photo_metadata(photo_id)
    if not photo_meta:
        raise ValueError(f"Photo not found: {photo_id}")

    # Download original image
    s3_key = photo_meta.get('s3Key')
    image = download_image_from_s3(s3_key)

    try:
        result = _style_transfer_with_bedrock(image, style)
    except Exception as e:
        raise ValueError(f"Style transfer failed: {e}")

    return save_edited_photo(
        original_photo=photo_meta,
        edited_image=result,
        edit_operation=f'style_{style}',
        edit_parameters={'style': style}
    )


def _style_transfer_with_bedrock(image, style):
    """Apply artistic style using Stability AI via Bedrock"""
    bedrock = get_bedrock_client()

    # Style prompts
    style_prompts = {
        'watercolor': 'watercolor painting style, soft colors, artistic brush strokes',
        'oil_painting': 'oil painting style, thick brush strokes, rich colors, classical art',
        'sketch': 'pencil sketch style, black and white, detailed line drawing',
        'anime': 'anime style, vibrant colors, clean lines, Japanese animation',
        'pop_art': 'pop art style, bold colors, comic book style, Andy Warhol inspired',
        'impressionist': 'impressionist painting style, soft brush strokes, light and color, Monet inspired'
    }

    prompt = style_prompts.get(style, 'artistic style')

    # Convert image to base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    response = bedrock.invoke_model(
        modelId='stability.stable-diffusion-xl-v1',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            'text_prompts': [
                {'text': prompt, 'weight': 1.0}
            ],
            'init_image': image_base64,
            'init_image_mode': 'IMAGE_STRENGTH',
            'image_strength': 0.6,  # More style transformation
            'cfg_scale': 12,
            'samples': 1,
            'steps': 50
        })
    )

    response_body = json.loads(response['body'].read())
    result_base64 = response_body['artifacts'][0]['base64']
    result_data = base64.b64decode(result_base64)

    return Image.open(io.BytesIO(result_data))


def process_image_edit(photo_id, operation, parameters=None):
    """Main entry point for image editing operations

    Args:
        photo_id: ID of the photo to edit
        operation: Edit operation type
        parameters: Operation-specific parameters

    Returns:
        New photo metadata dict
    """
    params = parameters or {}

    if operation == 'rotate':
        angle = params.get('angle', 90)
        return rotate_image(photo_id, angle)

    elif operation == 'enhance':
        return enhance_image(photo_id, params)

    elif operation == 'upscale':
        scale = params.get('scale', 2)
        return upscale_image(photo_id, scale)

    elif operation == 'remove_bg':
        return remove_background(photo_id)

    elif operation == 'style_transfer':
        style = params.get('style', 'watercolor')
        return style_transfer(photo_id, style)

    else:
        raise ValueError(f"Unknown operation: {operation}")
