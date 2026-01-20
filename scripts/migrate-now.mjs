import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, QueryCommand, PutCommand, DeleteCommand } from "@aws-sdk/lib-dynamodb";

const REGION = "us-east-1";
const TABLE_NAME = "PhotosMetadata";
const FROM_USER = "default-user";
const TO_USER = "c4687488-c0f1-70de-59bd-5606931c0d77";

const client = new DynamoDBClient({ region: REGION });
const docClient = DynamoDBDocumentClient.from(client);

async function migrate() {
  console.log(`Migrating from "${FROM_USER}" to "${TO_USER}"...`);

  let lastEvaluatedKey = undefined;
  let totalMigrated = 0;

  do {
    // Query for items
    const queryParams = {
      TableName: TABLE_NAME,
      KeyConditionExpression: "pk = :pk",
      ExpressionAttributeValues: {
        ":pk": `USER#${FROM_USER}`
      },
      ExclusiveStartKey: lastEvaluatedKey
    };

    const response = await docClient.send(new QueryCommand(queryParams));
    const items = response.Items || [];

    console.log(`Processing batch of ${items.length} items...`);

    for (const item of items) {
      const oldPk = item.pk;
      const oldSk = item.sk;

      // Create new item
      const newItem = {
        ...item,
        pk: `USER#${TO_USER}`,
        userId: TO_USER,
        migratedFrom: FROM_USER,
        migratedAt: new Date().toISOString()
      };

      try {
        // Write new item
        await docClient.send(new PutCommand({
          TableName: TABLE_NAME,
          Item: newItem
        }));

        // Delete old item
        await docClient.send(new DeleteCommand({
          TableName: TABLE_NAME,
          Key: { pk: oldPk, sk: oldSk }
        }));

        totalMigrated++;

        const itemType = oldSk.startsWith("ALBUM#") ? "album" : "date_index";
        const itemId = oldSk.startsWith("ALBUM#") ? oldSk.replace("ALBUM#", "") : oldSk.substring(0, 25) + "...";
        console.log(`  [${totalMigrated}] Migrated ${itemType}: ${itemId}`);
      } catch (err) {
        console.error(`  Error migrating ${oldSk}:`, err.message);
      }
    }

    lastEvaluatedKey = response.LastEvaluatedKey;
  } while (lastEvaluatedKey);

  console.log(`\nMigration complete! Migrated ${totalMigrated} items.`);
}

migrate().catch(console.error);
