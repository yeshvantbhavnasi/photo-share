import { test, expect } from '@playwright/test';
import { login, logout } from './helpers/auth';

test.describe('Navigation', () => {
  test('should redirect to login when not authenticated', async ({ page }) => {
    await page.goto('/albums/');

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });

  test('should show login page', async ({ page }) => {
    await page.goto('/login');

    // Check for login form elements
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should show signup page', async ({ page }) => {
    await page.goto('/signup');

    // Check for signup form elements
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('should login successfully', async ({ page }) => {
    await login(page);

    // Should be on albums page or dashboard
    await expect(page).toHaveURL(/\/(albums|$)/);

    // Should see navigation elements
    await expect(page.locator('text=Albums')).toBeVisible();
    await expect(page.locator('text=Sign out')).toBeVisible();
  });

  test('should navigate between pages when logged in', async ({ page }) => {
    await login(page);

    // Navigate to Albums
    await page.click('a:has-text("Albums")');
    await expect(page).toHaveURL(/\/albums/);

    // Navigate to Timeline
    await page.click('a:has-text("Timeline")');
    await expect(page).toHaveURL(/\/timeline/);

    // Navigate to Duplicates
    await page.click('a:has-text("Duplicates")');
    await expect(page).toHaveURL(/\/duplicates/);

    // Navigate to Upload
    await page.click('a:has-text("Upload")');
    await expect(page).toHaveURL(/\/upload/);
  });

  test('should logout successfully', async ({ page }) => {
    await login(page);

    // Logout
    await logout(page);

    // Should be on login page
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe('Timeline', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should display timeline page', async ({ page }) => {
    await page.goto('/timeline/');

    // Check page has timeline content
    await expect(page.locator('text=Timeline, h1')).toBeVisible();
  });
});

test.describe('Responsive Design', () => {
  test('should work on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    await login(page);

    // Check mobile navigation works
    await expect(page.locator('text=Albums').first()).toBeVisible();
  });

  test('should work on tablet viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });

    await login(page);

    await page.goto('/albums/');
    await expect(page.locator('h1')).toContainText('Albums');
  });
});
