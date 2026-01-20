#!/usr/bin/env python3
"""
Migrate all albums from 'default-user' to a specific Cognito user.

Usage:
    python migrate-to-user.py <cognito-user-id>

Or to look up by email:
    python migrate-to-user.py --email bhavnasiyeshvant@gmail.com

This script directly updates DynamoDB to transfer ownership of all
albums and photos from the default user to the specified user.
"""

import sys
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime

# Configuration
PHOTOS_TABLE = 'PhotosMetadata'
REGION = 'us-east-1'
USER_POOL_ID = None  # Will be set from environment or argument

dynamodb = boto3.resource('dynamodb', region_name=REGION)
cognito = boto3.client('cognito-idp', region_name=REGION)
photos_table = dynamodb.Table(PHOTOS_TABLE)


def get_user_id_by_email(email, user_pool_id):
    """Look up Cognito user ID by email address"""
    try:
        response = cognito.admin_get_user(
            UserPoolId=user_pool_id,
            Username=email
        )

        # Find the 'sub' attribute which is the user ID
        for attr in response.get('UserAttributes', []):
            if attr['Name'] == 'sub':
                return attr['Value']

        # If no sub found, the username might be the sub
        return response.get('Username')
    except cognito.exceptions.UserNotFoundException:
        print(f"Error: User with email '{email}' not found in Cognito")
        return None
    except Exception as e:
        print(f"Error looking up user: {e}")
        return None


def migrate_user_data(from_user_id, to_user_id):
    """Migrate all data from one user to another"""
    print(f"\nMigrating data from '{from_user_id}' to '{to_user_id}'...")

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

    if not items_to_migrate:
        print("No items found to migrate.")
        return {'migratedCount': 0}

    print(f"Found {len(items_to_migrate)} items to migrate")

    migrated_count = 0

    for item in items_to_migrate:
        old_pk = item['pk']
        old_sk = item['sk']

        # Determine item type
        if old_sk.startswith('ALBUM#'):
            item_type = 'album'
            item_id = old_sk.replace('ALBUM#', '')
        elif old_sk.startswith('DATE#'):
            item_type = 'date_index'
            item_id = old_sk
        else:
            item_type = 'unknown'
            item_id = old_sk

        # Create new item with updated pk
        new_item = dict(item)
        new_item['pk'] = f'USER#{to_user_id}'
        new_item['userId'] = to_user_id
        new_item['migratedFrom'] = from_user_id
        new_item['migratedAt'] = datetime.utcnow().isoformat() + 'Z'

        try:
            # Write new item
            photos_table.put_item(Item=new_item)

            # Delete old item
            photos_table.delete_item(Key={'pk': old_pk, 'sk': old_sk})

            migrated_count += 1
            print(f"  Migrated {item_type}: {item_id}")
        except Exception as e:
            print(f"  Error migrating {item_type} {item_id}: {e}")

    print(f"\nMigration complete! Migrated {migrated_count} items.")
    return {'migratedCount': migrated_count}


def list_user_pools():
    """List available Cognito user pools"""
    try:
        response = cognito.list_user_pools(MaxResults=10)
        pools = response.get('UserPools', [])

        if not pools:
            print("No user pools found. Run scripts/setup-cognito.sh first.")
            return None

        print("\nAvailable User Pools:")
        for i, pool in enumerate(pools):
            print(f"  {i+1}. {pool['Name']} ({pool['Id']})")

        return pools
    except Exception as e:
        print(f"Error listing user pools: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nLooking for existing user pools...")
        pools = list_user_pools()

        if pools:
            print("\nTo migrate, first ensure your user account exists in Cognito,")
            print("then run:")
            print("  python migrate-to-user.py --email bhavnasiyeshvant@gmail.com --pool <pool-id>")
        return

    # Parse arguments
    email = None
    user_id = None
    pool_id = None

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--email' and i + 1 < len(sys.argv):
            email = sys.argv[i + 1]
            i += 2
        elif arg == '--pool' and i + 1 < len(sys.argv):
            pool_id = sys.argv[i + 1]
            i += 2
        else:
            user_id = arg
            i += 1

    # If email provided, look up user ID
    if email:
        if not pool_id:
            pools = list_user_pools()
            if pools and len(pools) == 1:
                pool_id = pools[0]['Id']
                print(f"\nUsing pool: {pool_id}")
            else:
                print("\nPlease specify --pool <pool-id>")
                return

        user_id = get_user_id_by_email(email, pool_id)
        if not user_id:
            return

        print(f"Found user ID: {user_id}")

    if not user_id:
        print("Error: No user ID or email specified")
        return

    # Confirm migration
    print(f"\nThis will migrate all albums from 'default-user' to user '{user_id}'")
    confirm = input("Continue? (yes/no): ")

    if confirm.lower() != 'yes':
        print("Migration cancelled.")
        return

    # Run migration
    migrate_user_data('default-user', user_id)


if __name__ == '__main__':
    main()
