import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

test.describe('Share Links', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should have share button on album page', async ({ page }) => {
    await page.goto('/albums/');

    // Click on first album if exists
    const albumCard = page.locator('a[href*="/album/?id="]').first();

    if (await albumCard.isVisible()) {
      await albumCard.click();
      await page.waitForURL(/\/album\/\?id=/);

      // Look for share button
      const shareButton = page.locator('button:has-text("Share"), button[aria-label*="share"], text=Share');
      await expect(shareButton).toBeVisible({ timeout: 10000 });
    }
  });

  test('should create share link', async ({ page }) => {
    await page.goto('/albums/');

    // Click on first album if exists
    const albumCard = page.locator('a[href*="/album/?id="]').first();

    if (await albumCard.isVisible()) {
      await albumCard.click();
      await page.waitForURL(/\/album\/\?id=/);

      // Click share button
      const shareButton = page.locator('button:has-text("Share")').first();
      if (await shareButton.isVisible()) {
        await shareButton.click();

        // Wait for share modal or share link to appear
        await expect(
          page.locator('text=Copy Link, input[value*="share"], text=Share Link').first()
        ).toBeVisible({ timeout: 10000 });
      }
    }
  });
});

test.describe('Public Share Access', () => {
  // Test that shared albums are accessible without login
  test('should access shared album without authentication', async ({ page, context }) => {
    // First, login and create a share link
    await login(page);
    await page.goto('/albums/');

    const albumCard = page.locator('a[href*="/album/?id="]').first();

    if (await albumCard.isVisible()) {
      await albumCard.click();
      await page.waitForURL(/\/album\/\?id=/);

      // Try to find and click share button
      const shareButton = page.locator('button:has-text("Share")').first();
      if (await shareButton.isVisible()) {
        await shareButton.click();

        // Look for share URL
        const shareInput = page.locator('input[value*="share"]');
        if (await shareInput.isVisible()) {
          const shareUrl = await shareInput.inputValue();

          // Clear cookies to simulate logged-out state
          await context.clearCookies();

          // Navigate to share URL in new context
          const newPage = await context.newPage();
          await newPage.goto(shareUrl);

          // Should be able to see album content without login
          await expect(newPage.locator('img').first()).toBeVisible({ timeout: 15000 });
        }
      }
    }
  });
});
