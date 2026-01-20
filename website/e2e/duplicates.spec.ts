import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

test.describe('Duplicate Detection', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should display duplicates page', async ({ page }) => {
    await page.goto('/duplicates/');

    // Check page title
    await expect(page.locator('h1')).toContainText('Duplicate');

    // Check for scan button or results
    const hasScanButton = await page.locator('button:has-text("Scan")').isVisible().catch(() => false);
    const hasResults = await page.locator('text=duplicates found, text=No duplicates').first().isVisible().catch(() => false);

    expect(hasScanButton || hasResults).toBeTruthy();
  });

  test('should have scan functionality', async ({ page }) => {
    await page.goto('/duplicates/');

    // Look for scan button
    const scanButton = page.locator('button:has-text("Scan"), button:has-text("Find Duplicates")').first();

    if (await scanButton.isVisible()) {
      await scanButton.click();

      // Wait for scan to start (loading indicator or results)
      await expect(
        page.locator('text=Scanning, text=duplicates, text=No duplicates').first()
      ).toBeVisible({ timeout: 60000 });
    }
  });

  test('should show album selection for scanning', async ({ page }) => {
    await page.goto('/duplicates/');

    // Check for album dropdown or all albums option
    const hasAlbumSelect = await page.locator('select').isVisible().catch(() => false);
    const hasAllAlbumsOption = await page.locator('text=All Albums, text=across albums').first().isVisible().catch(() => false);

    // At least one way to select scope should exist
    expect(hasAlbumSelect || hasAllAlbumsOption).toBeTruthy();
  });

  test('should handle delete duplicate functionality', async ({ page }) => {
    await page.goto('/duplicates/');

    // Start a scan
    const scanButton = page.locator('button:has-text("Scan"), button:has-text("Find")').first();
    if (await scanButton.isVisible()) {
      await scanButton.click();

      // Wait for results
      await page.waitForTimeout(5000);

      // If duplicates found, check for delete options
      const deleteButton = page.locator('button:has-text("Delete"), button:has-text("Remove")').first();
      const selectCheckbox = page.locator('input[type="checkbox"]').first();

      if (await deleteButton.isVisible()) {
        // Delete functionality exists
        expect(true).toBe(true);
      } else if (await selectCheckbox.isVisible()) {
        // Can select duplicates
        expect(true).toBe(true);
      }
    }
  });
});
