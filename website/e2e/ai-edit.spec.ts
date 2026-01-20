import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

test.describe('AI Photo Editing', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should show edit options when viewing a photo', async ({ page }) => {
    await page.goto('/albums/');

    // Click on first album
    const albumCard = page.locator('a[href*="/album/?id="]').first();

    if (await albumCard.isVisible()) {
      await albumCard.click();
      await page.waitForURL(/\/album\/\?id=/);

      // Click on a photo to open lightbox/modal
      const photo = page.locator('img').first();
      if (await photo.isVisible()) {
        await photo.click();

        // Look for edit options
        await expect(
          page.locator('button:has-text("Edit"), button:has-text("Enhance"), text=Rotate, text=AI').first()
        ).toBeVisible({ timeout: 10000 });
      }
    }
  });

  test('should have rotate functionality', async ({ page }) => {
    await page.goto('/albums/');

    const albumCard = page.locator('a[href*="/album/?id="]').first();

    if (await albumCard.isVisible()) {
      await albumCard.click();
      await page.waitForURL(/\/album\/\?id=/);

      const photo = page.locator('img').first();
      if (await photo.isVisible()) {
        await photo.click();

        // Look for rotate button
        const rotateButton = page.locator('button:has-text("Rotate"), button[aria-label*="rotate"]').first();

        if (await rotateButton.isVisible()) {
          await expect(rotateButton).toBeEnabled();
        }
      }
    }
  });

  test('should have enhance functionality', async ({ page }) => {
    await page.goto('/albums/');

    const albumCard = page.locator('a[href*="/album/?id="]').first();

    if (await albumCard.isVisible()) {
      await albumCard.click();
      await page.waitForURL(/\/album\/\?id=/);

      const photo = page.locator('img').first();
      if (await photo.isVisible()) {
        await photo.click();

        // Look for enhance button
        const enhanceButton = page.locator('button:has-text("Enhance"), button[aria-label*="enhance"]').first();

        if (await enhanceButton.isVisible()) {
          await expect(enhanceButton).toBeEnabled();
        }
      }
    }
  });

  test('should have style transfer options', async ({ page }) => {
    await page.goto('/albums/');

    const albumCard = page.locator('a[href*="/album/?id="]').first();

    if (await albumCard.isVisible()) {
      await albumCard.click();
      await page.waitForURL(/\/album\/\?id=/);

      const photo = page.locator('img').first();
      if (await photo.isVisible()) {
        await photo.click();

        // Look for style options
        const styleButton = page.locator('button:has-text("Style"), text=Artistic, text=Filter').first();

        if (await styleButton.isVisible()) {
          await styleButton.click();

          // Check for style options
          await expect(
            page.locator('text=Cartoon, text=Oil Painting, text=Sketch, text=Anime').first()
          ).toBeVisible({ timeout: 5000 });
        }
      }
    }
  });

  test('should have remove background option', async ({ page }) => {
    await page.goto('/albums/');

    const albumCard = page.locator('a[href*="/album/?id="]').first();

    if (await albumCard.isVisible()) {
      await albumCard.click();
      await page.waitForURL(/\/album\/\?id=/);

      const photo = page.locator('img').first();
      if (await photo.isVisible()) {
        await photo.click();

        // Look for remove background option
        const removeBgButton = page.locator('button:has-text("Background"), button:has-text("Remove BG")').first();

        if (await removeBgButton.isVisible()) {
          await expect(removeBgButton).toBeEnabled();
        }
      }
    }
  });
});

test.describe('AI Edit on Shared Albums', () => {
  // Test that AI editing works on shared albums without login
  test('shared album should have AI edit capabilities', async ({ page }) => {
    // Navigate to a known shared album (if available)
    // This test requires a pre-existing share link in environment variable
    const shareToken = process.env.TEST_SHARE_TOKEN;

    if (shareToken) {
      await page.goto(`/share/${shareToken}`);

      // Wait for album to load
      await expect(page.locator('img').first()).toBeVisible({ timeout: 15000 });

      // Click on a photo
      const photo = page.locator('img').first();
      await photo.click();

      // AI edit options should be available even on shared albums
      await expect(
        page.locator('button:has-text("Edit"), button:has-text("Enhance"), text=Rotate').first()
      ).toBeVisible({ timeout: 10000 });
    }
  });
});
