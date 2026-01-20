import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';
import * as path from 'path';
import * as fs from 'fs';

test.describe('Upload', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should display upload page', async ({ page }) => {
    await page.goto('/upload/');

    // Check page title
    await expect(page.locator('h1')).toContainText('Upload Photos');

    // Check for dropzone
    await expect(page.locator('text=Drag & drop')).toBeVisible();

    // Check that ZIP support is mentioned
    await expect(page.locator('text=ZIP files')).toBeVisible();
  });

  test('should show album selection', async ({ page }) => {
    await page.goto('/upload/');

    // Should see album selection or create new album option
    const hasAlbums = await page.locator('select').isVisible().catch(() => false);
    const hasCreateNew = await page.locator('text=Create Album').isVisible().catch(() => false);
    const hasNewAlbumInput = await page.locator('input[placeholder*="Vacation"]').isVisible().catch(() => false);

    expect(hasAlbums || hasCreateNew || hasNewAlbumInput).toBeTruthy();
  });

  test('should create album from upload page', async ({ page }) => {
    await page.goto('/upload/');

    // Click create new album if the option exists
    const createNewBtn = page.locator('text=Create new album');
    if (await createNewBtn.isVisible().catch(() => false)) {
      await createNewBtn.click();
    }

    // Fill in album name if visible
    const albumInput = page.locator('input[placeholder*="Vacation"]');
    if (await albumInput.isVisible()) {
      const albumName = `Upload Test Album ${Date.now()}`;
      await albumInput.fill(albumName);
      await page.click('button:has-text("Create Album")');

      // Dropzone should become visible
      await expect(page.locator('text=Drag & drop')).toBeVisible();
    }
  });

  test('should handle file selection dialog', async ({ page }) => {
    await page.goto('/upload/');

    // Create album first if needed
    const albumInput = page.locator('input[placeholder*="Vacation"]');
    if (await albumInput.isVisible()) {
      await albumInput.fill(`Upload Test ${Date.now()}`);
      await page.click('button:has-text("Create Album")');
    }

    // The dropzone should have an input element for file selection
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();
  });

  test('should show upload progress UI elements', async ({ page }) => {
    await page.goto('/upload/');

    // Verify the upload UI structure exists
    await expect(page.locator('text=Supports')).toBeVisible();

    // Check supported formats are listed
    const formats = ['JPEG', 'PNG', 'GIF', 'WebP', 'HEIC', 'ZIP'];
    for (const format of formats) {
      await expect(page.locator(`text=${format}`)).toBeVisible();
    }
  });
});

test.describe('Upload with fixtures', () => {
  test.skip(({ browserName }) => browserName !== 'chromium', 'File upload tests run on Chromium only');

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should upload a test image', async ({ page }) => {
    await page.goto('/upload/');

    // Create album first if needed
    const albumInput = page.locator('input[placeholder*="Vacation"]');
    if (await albumInput.isVisible()) {
      await albumInput.fill(`Image Upload Test ${Date.now()}`);
      await page.click('button:has-text("Create Album")');
    }

    // Wait for dropzone
    await expect(page.locator('text=Drag & drop')).toBeVisible();

    // Create a test image blob (1x1 red pixel PNG)
    const testImageBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';
    const testImageBuffer = Buffer.from(testImageBase64, 'base64');

    // Use setInputFiles to upload
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test-image.png',
      mimeType: 'image/png',
      buffer: testImageBuffer,
    });

    // Wait for upload to complete
    await expect(page.locator('text=uploaded')).toBeVisible({ timeout: 30000 });

    // Check for View Album button
    await expect(page.locator('text=View Album')).toBeVisible();
  });
});
