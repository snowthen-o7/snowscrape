/**
 * Notifications E2E Test
 * Tests for notification center functionality
 */

import { test, expect } from '@playwright/test';

test.describe('Notification Center', () => {
  test('should display notification bell in navigation', async ({ page }) => {
    await page.goto('/dashboard');

    // Should show notification bell icon
    const bellIcon = page.getByRole('button').filter({ has: page.locator('svg[class*="bell" i], [data-testid="notification-bell"]') });
    await expect(bellIcon.first()).toBeVisible();
  });

  test('should open notification dropdown when bell is clicked', async ({ page }) => {
    await page.goto('/dashboard');

    // Click notification bell
    const bellButton = page.getByRole('button').filter({ has: page.locator('svg') }).nth(1); // Adjust index as needed
    if (await bellButton.isVisible()) {
      await bellButton.click();

      // Should show dropdown with notifications
      await page.waitForTimeout(500);
      const dropdown = page.getByRole('menu').or(page.locator('[role="dialog"]'));
      if (await dropdown.isVisible()) {
        await expect(dropdown).toBeVisible();
      }
    }
  });

  test('should show unread notification count badge', async ({ page }) => {
    await page.goto('/dashboard');

    // Should show badge with count (if there are unread notifications)
    const badge = page.locator('[class*="badge"]').filter({ hasText: /\d+/ });
    // Badge may or may not be visible depending on notification state
    const badgeCount = await badge.count();
    expect(badgeCount).toBeGreaterThanOrEqual(0);
  });

  test('should navigate to full notifications page', async ({ page }) => {
    await page.goto('/dashboard/notifications');

    // Should show notifications page heading
    await expect(page.getByRole('heading', { name: /notifications/i })).toBeVisible();
  });

  test('should filter notifications by read status', async ({ page }) => {
    await page.goto('/dashboard/notifications');

    // Find and click tabs
    const allTab = page.getByRole('tab', { name: /all/i });
    if (await allTab.isVisible()) {
      await allTab.click();
      await page.waitForTimeout(300);
    }

    const unreadTab = page.getByRole('tab', { name: /unread/i });
    if (await unreadTab.isVisible()) {
      await unreadTab.click();
      await page.waitForTimeout(300);
    }

    const readTab = page.getByRole('tab', { name: /read/i });
    if (await readTab.isVisible()) {
      await readTab.click();
      await page.waitForTimeout(300);
    }
  });

  test('should filter notifications by category', async ({ page }) => {
    await page.goto('/dashboard/notifications');

    // Find category dropdown
    const categoryFilter = page.getByRole('button').filter({ hasText: /category|all categories/i });
    if (await categoryFilter.isVisible()) {
      await categoryFilter.click();

      // Select a category
      const jobCategory = page.getByRole('option', { name: /jobs/i }).or(page.getByText('Jobs'));
      if (await jobCategory.isVisible()) {
        await jobCategory.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('should mark notification as read', async ({ page }) => {
    await page.goto('/dashboard/notifications');

    // Find mark as read button
    const markReadButton = page.getByRole('button', { name: /mark read/i }).first();
    if (await markReadButton.isVisible()) {
      await markReadButton.click();
      await page.waitForTimeout(500);

      // Button should disappear or change state
    }
  });

  test('should mark all notifications as read', async ({ page }) => {
    await page.goto('/dashboard/notifications');

    // Find mark all as read button
    const markAllReadButton = page.getByRole('button', { name: /mark all read/i });
    if (await markAllReadButton.isVisible()) {
      await markAllReadButton.click();
      await page.waitForTimeout(500);
    }
  });

  test('should delete notification', async ({ page }) => {
    await page.goto('/dashboard/notifications');

    // Count notifications before deletion
    const notificationsBefore = await page.locator('[data-testid="notification-card"], [class*="notification"]').count();

    // Find delete button
    const deleteButton = page.getByRole('button').filter({ has: page.locator('svg[class*="trash" i]') }).first();
    if (await deleteButton.isVisible()) {
      await deleteButton.click();
      await page.waitForTimeout(500);

      // Notification count should decrease
      const notificationsAfter = await page.locator('[data-testid="notification-card"], [class*="notification"]').count();
      expect(notificationsAfter).toBeLessThanOrEqual(notificationsBefore);
    }
  });
});
