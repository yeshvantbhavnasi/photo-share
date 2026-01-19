#!/usr/bin/env python3
"""
Backfill script to create timeline items for existing photos.

This script scans all ALBUM#/PHOTO# items and creates corresponding
USER#/DATE# items for timeline queries.

Usage:
    python backfill_timeline.py
"""

import boto3
from boto3.dynamodb.conditions import Key, Attr

# Configuration
REGION = 'us-east-1'
TABLE_NAME = 'PhotosMetadata'

dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(TABLE_NAME)


def backfill_timeline_items():
    """Scan all photo items and create timeline items."""

    print("Scanning for all photo items...")

    # Scan for all items where pk starts with ALBUM# and sk starts with PHOTO#
    response = table.scan(
        FilterExpression=Attr('pk').begins_with('ALBUM#') & Attr('sk').begins_with('PHOTO#')
    )

    items = response.get('Items', [])

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression=Attr('pk').begins_with('ALBUM#') & Attr('sk').begins_with('PHOTO#'),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response.get('Items', []))

    print(f"Found {len(items)} photo items")

    created = 0
    skipped = 0

    for item in items:
        photo_id = item.get('photoId')
        user_id = item.get('userId', 'default-user')
        upload_date = item.get('uploadDate', '')[:10]  # YYYY-MM-DD
        filename = item.get('filename', '')

        # Skip macOS metadata files
        if filename.startswith('.'):
            skipped += 1
            continue

        if not upload_date or not photo_id:
            print(f"  Skipping item with missing data: {item.get('sk')}")
            skipped += 1
            continue

        # Create timeline item
        timeline_pk = f"USER#{user_id}"
        timeline_sk = f"DATE#{upload_date}#PHOTO#{photo_id}"

        # Check if already exists
        existing = table.get_item(
            Key={'pk': timeline_pk, 'sk': timeline_sk}
        )

        if 'Item' in existing:
            skipped += 1
            continue

        # Create new timeline item
        timeline_item = {
            **item,
            'pk': timeline_pk,
            'sk': timeline_sk,
        }

        table.put_item(Item=timeline_item)
        created += 1

        if created % 50 == 0:
            print(f"  Created {created} timeline items...")

    print(f"\nBackfill complete!")
    print(f"  Created: {created}")
    print(f"  Skipped: {skipped}")


if __name__ == '__main__':
    backfill_timeline_items()
