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
        actual_content_type = 'image/png'
        # Ensure image is in a mode compatible with PNG
        if image.mode not in ['RGB', 'RGBA', 'L', 'LA', 'P']:
            image = image.convert('RGBA')
    else:
        format_type = 'JPEG'
        actual_content_type = 'image/jpeg'
        # Convert to RGB for JPEG (JPEG doesn't support alpha)
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

    # Save with appropriate settings
    if format_type == 'PNG':
        image.save(buffer, format=format_type, optimize=True)
    else:
        image.save(buffer, format=format_type, quality=95, optimize=True)

    buffer.seek(0)
    image_bytes = buffer.getvalue()

    print(f"Uploading to S3: {s3_key}, size: {len(image_bytes)} bytes, format: {format_type}")

    s3.put_object(
        Bucket=PHOTOS_BUCKET,
        Key=s3_key,
        Body=image_bytes,
        ContentType=actual_content_type
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


def _resize_for_bedrock(image, max_pixels=1000000):
    """Resize image if too large for fast Bedrock processing.

    Keeps aspect ratio, targets under max_pixels for faster API response.
    """
    total_pixels = image.width * image.height
    if total_pixels > max_pixels:
        scale = (max_pixels / total_pixels) ** 0.5
        new_width = int(image.width * scale)
        new_height = int(image.height * scale)
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    return image


def _enhance_with_bedrock(image, params):
    """Enhance image using Stability AI Creative Upscale via Bedrock

    Uses Creative Upscale with enhancement prompt for AI-powered image enhancement.
    """
    bedrock = get_bedrock_client()

    # Resize if too large (for faster processing within API Gateway timeout)
    image = _resize_for_bedrock(image, max_pixels=800000)
    print(f"Image for Bedrock enhance: {image.width}x{image.height}")

    # Convert image to base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Use Creative Upscale with enhancement prompt
    response = bedrock.invoke_model(
        modelId='us.stability.stable-creative-upscale-v1:0',
        body=json.dumps({
            'image': image_base64,
            'prompt': 'enhance photo quality, improve lighting, vivid colors, sharp details, professional photography',
            'negative_prompt': 'blurry, low quality, distorted, overexposed, underexposed',
            'creativity': 0.2,  # Lower = keep more of original
            'output_format': 'png'
        })
    )

    response_body = json.loads(response['body'].read())

    # Decode result image (new API uses 'images' array)
    result_base64 = response_body['images'][0]
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

    print(f"Original image: {image.width}x{image.height}, mode: {image.mode}")

    try:
        upscaled = _upscale_with_bedrock(image, scale_factor)
        print(f"Bedrock upscaled image: {upscaled.width}x{upscaled.height}, mode: {upscaled.mode}")
    except Exception as e:
        print(f"Bedrock upscale failed, using fallback: {e}")
        # Fallback to Pillow resize with proper mode handling
        if image.mode not in ['RGB', 'RGBA']:
            image = image.convert('RGB')
        new_size = (image.width * scale_factor, image.height * scale_factor)
        upscaled = image.resize(new_size, Image.Resampling.LANCZOS)
        print(f"Pillow upscaled image: {upscaled.width}x{upscaled.height}, mode: {upscaled.mode}")

    # Ensure the upscaled image is in a valid mode
    if upscaled.mode not in ['RGB', 'RGBA', 'L']:
        upscaled = upscaled.convert('RGB')

    return save_edited_photo(
        original_photo=photo_meta,
        edited_image=upscaled,
        edit_operation='upscaled',
        edit_parameters={'scale': scale_factor}
    )


def _upscale_with_bedrock(image, scale_factor):
    """Upscale image using Stability AI Fast Upscale via Bedrock

    Fast Upscale: max 1,048,576 pixels (1MP), 4x upscale
    Resizes input to fit within limit for faster processing.
    """
    bedrock = get_bedrock_client()

    # Resize to fit within Fast Upscale limit (1MP) for speed
    image = _resize_for_bedrock(image, max_pixels=800000)
    print(f"Image for Bedrock upscale: {image.width}x{image.height}")

    # Convert image to base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Use Fast Upscale (simpler API, no prompt needed)
    response = bedrock.invoke_model(
        modelId='us.stability.stable-fast-upscale-v1:0',
        body=json.dumps({
            'image': image_base64,
            'output_format': 'png'
        })
    )

    response_body = json.loads(response['body'].read())
    result_base64 = response_body['images'][0]
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
    """Remove background using Stability AI Remove Background service via Bedrock"""
    bedrock = get_bedrock_client()

    # Resize for faster processing
    image = _resize_for_bedrock(image, max_pixels=800000)
    print(f"Image for Bedrock remove_bg: {image.width}x{image.height}")

    # Convert image to base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Use dedicated Remove Background model
    response = bedrock.invoke_model(
        modelId='us.stability.stable-image-remove-background-v1:0',
        body=json.dumps({
            'image': image_base64,
            'output_format': 'png'
        })
    )

    response_body = json.loads(response['body'].read())
    result_base64 = response_body['images'][0]
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
    """Apply artistic style using Stability AI Creative Upscale with style presets"""
    bedrock = get_bedrock_client()

    # Map our style names to Stability AI style_preset values
    style_preset_map = {
        'watercolor': 'analog-film',  # Soft, artistic look
        'oil_painting': 'enhance',  # Rich, detailed
        'sketch': 'line-art',  # Line drawing style
        'anime': 'anime',  # Anime style
        'pop_art': 'comic-book',  # Bold, comic style
        'impressionist': 'digital-art'  # Artistic digital style
    }

    # Style prompts for additional guidance
    style_prompts = {
        'watercolor': 'watercolor painting, soft colors, artistic brush strokes, dreamy',
        'oil_painting': 'oil painting, thick brush strokes, rich colors, classical fine art',
        'sketch': 'pencil sketch, detailed line drawing, artistic illustration',
        'anime': 'anime art style, vibrant colors, clean lines, Japanese animation style',
        'pop_art': 'pop art, bold colors, comic book style, graphic design',
        'impressionist': 'impressionist painting, soft brush strokes, light and color, artistic'
    }

    style_preset = style_preset_map.get(style, 'digital-art')
    prompt = style_prompts.get(style, 'artistic style transformation')

    # Resize for faster processing
    image = _resize_for_bedrock(image, max_pixels=800000)
    print(f"Image for Bedrock style_transfer: {image.width}x{image.height}")

    # Convert image to base64
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Use Creative Upscale with style preset
    response = bedrock.invoke_model(
        modelId='us.stability.stable-creative-upscale-v1:0',
        body=json.dumps({
            'image': image_base64,
            'prompt': prompt,
            'style_preset': style_preset,
            'creativity': 0.5,  # Higher creativity for more style transformation
            'output_format': 'png'
        })
    )

    response_body = json.loads(response['body'].read())
    result_base64 = response_body['images'][0]
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
