import { Page, expect } from '@playwright/test';

// Test credentials - MUST be set as environment variables in CI
// Add TEST_EMAIL and TEST_PASSWORD to GitHub Secrets
const TEST_EMAIL = process.env.TEST_EMAIL;
const TEST_PASSWORD = process.env.TEST_PASSWORD;

if (!TEST_EMAIL || !TEST_PASSWORD) {
  console.warn('WARNING: TEST_EMAIL and TEST_PASSWORD environment variables are not set. Tests requiring authentication will be skipped.');
}

/**
 * Log in to the application
 */
export async function login(page: Page) {
  if (!TEST_EMAIL || !TEST_PASSWORD) {
    throw new Error('TEST_EMAIL and TEST_PASSWORD environment variables must be set. Add them to GitHub Secrets.');
  }

  await page.goto('/login');

  // Wait for login form to be visible
  await expect(page.locator('input[type="email"]')).toBeVisible();

  // Fill in credentials
  await page.fill('input[type="email"]', TEST_EMAIL);
  await page.fill('input[type="password"]', TEST_PASSWORD);

  // Click sign in button
  await page.click('button[type="submit"]');

  // Wait for redirect to albums page or dashboard
  await page.waitForURL(/\/(albums|$)/, { timeout: 15000 });

  // Verify we're logged in by checking for nav elements
  await expect(page.locator('text=Sign out')).toBeVisible({ timeout: 10000 });
}

/**
 * Log out of the application
 */
export async function logout(page: Page) {
  await page.click('text=Sign out');
  await page.waitForURL('/login');
}

/**
 * Check if user is logged in
 */
export async function isLoggedIn(page: Page): Promise<boolean> {
  try {
    await expect(page.locator('text=Sign out')).toBeVisible({ timeout: 3000 });
    return true;
  } catch {
    return false;
  }
}

/**
 * Ensure user is logged in before test
 */
export async function ensureLoggedIn(page: Page) {
  const loggedIn = await isLoggedIn(page);
  if (!loggedIn) {
    await login(page);
  }
}
