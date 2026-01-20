import { test, expect } from '@playwright/test';
import { login, ensureLoggedIn } from './helpers/auth';

test.describe('Albums', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should display albums page', async ({ page }) => {
    await page.goto('/albums/');

    // Check page title
    await expect(page.locator('h1')).toContainText('Albums');

    // Check for New Album button
    await expect(page.locator('text=New Album')).toBeVisible();
  });

  test('should create a new album', async ({ page }) => {
    await page.goto('/albums/');

    // Click New Album button
    await page.click('text=New Album');

    // Wait for modal
    await expect(page.locator('text=Create New Album')).toBeVisible();

    // Generate unique album name
    const albumName = `Test Album ${Date.now()}`;

    // Fill in album name
    await page.fill('input[placeholder*="Vacation"]', albumName);

    // Click Create button
    await page.click('button:has-text("Create")');

    // Should redirect to album page
    await page.waitForURL(/\/album\/\?id=/, { timeout: 10000 });

    // Verify album was created
    await expect(page.locator('h1')).toContainText(albumName);
  });

  test('should edit album name', async ({ page }) => {
    // First create an album
    await page.goto('/albums/');
    await page.click('text=New Album');

    const originalName = `Edit Test ${Date.now()}`;
    await page.fill('input[placeholder*="Vacation"]', originalName);
    await page.click('button:has-text("Create")');

    await page.waitForURL(/\/album\/\?id=/);

    // Click edit button (pencil icon)
    const editButton = page.locator('button[aria-label="Edit album name"], button:has(svg)').first();
    await editButton.click();

    // Edit the name
    const newName = `Renamed Album ${Date.now()}`;
    await page.fill('input[type="text"]', newName);

    // Save changes
    await page.click('button:has-text("Save"), button[aria-label="Save"]');

    // Verify name was updated
    await expect(page.locator('h1')).toContainText(newName);
  });

  test('should navigate to album from albums list', async ({ page }) => {
    await page.goto('/albums/');

    // Click on first album card if exists
    const albumCard = page.locator('a[href*="/album/?id="]').first();

    if (await albumCard.isVisible()) {
      await albumCard.click();

      // Should be on album page
      await expect(page).toHaveURL(/\/album\/\?id=/);
    }
  });
});
