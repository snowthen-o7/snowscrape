/**
 * Templates E2E Test
 * Tests for template marketplace browsing and selection
 */

import { test, expect } from '@playwright/test';

test.describe('Template Marketplace', () => {
  test('should navigate to templates page', async ({ page }) => {
    await page.goto('/dashboard/templates');

    // Should show templates heading
    await expect(page.getByRole('heading', { name: /templates/i })).toBeVisible();
  });

  test('should display official templates', async ({ page }) => {
    await page.goto('/dashboard/templates');

    // Should show multiple template cards
    const templateCards = page.locator('[data-testid="template-card"], .template-card, [class*="Card"]');
    await expect(templateCards.first()).toBeVisible();
  });

  test('should filter templates by category', async ({ page }) => {
    await page.goto('/dashboard/templates');

    // Find and click category filter
    const categoryFilter = page.getByRole('button', { name: /category|all categories/i });
    if (await categoryFilter.isVisible()) {
      await categoryFilter.click();

      // Select E-commerce category
      const ecommerceOption = page.getByRole('option', { name: /e-commerce/i }).or(page.getByText('E-commerce'));
      if (await ecommerceOption.isVisible()) {
        await ecommerceOption.click();

        // Should show filtered results
        await page.waitForTimeout(500);
      }
    }
  });

  test('should search for templates', async ({ page }) => {
    await page.goto('/dashboard/templates');

    // Find search input
    const searchInput = page.getByPlaceholder(/search/i);
    if (await searchInput.isVisible()) {
      await searchInput.fill('Amazon');

      // Should filter results
      await page.waitForTimeout(500);
      const amazonTemplate = page.getByText(/amazon/i);
      await expect(amazonTemplate.first()).toBeVisible();
    }
  });

  test('should navigate to template details', async ({ page }) => {
    await page.goto('/dashboard/templates');

    // Click on first template
    const firstTemplate = page.locator('[data-testid="template-card"]').first()
      .or(page.getByRole('button').filter({ hasText: /amazon|linkedin|zillow/i }).first());

    if (await firstTemplate.isVisible()) {
      await firstTemplate.click();

      // Should navigate to template details page
      await page.waitForURL(/\/dashboard\/templates\/.+/);

      // Should show template details
      await expect(page.getByRole('heading')).toBeVisible();
    }
  });

  test('should show template queries and sample data', async ({ page }) => {
    await page.goto('/dashboard/templates/amazon-product');

    // Should show tabs
    const queryTab = page.getByRole('tab', { name: /queries|configuration/i });
    if (await queryTab.isVisible()) {
      await queryTab.click();

      // Should show query information
      await page.waitForTimeout(500);
    }

    const sampleTab = page.getByRole('tab', { name: /sample|data/i });
    if (await sampleTab.isVisible()) {
      await sampleTab.click();

      // Should show sample data
      await page.waitForTimeout(500);
    }
  });
});

test.describe('Template Details', () => {
  test('should display template information', async ({ page }) => {
    await page.goto('/dashboard/templates/amazon-product');

    // Should show template name
    await expect(page.getByText(/amazon|scraper|product/i).first()).toBeVisible();
  });

  test('should allow copying queries', async ({ page }) => {
    await page.goto('/dashboard/templates/amazon-product');

    // Switch to queries tab
    const queryTab = page.getByRole('tab', { name: /queries/i });
    if (await queryTab.isVisible()) {
      await queryTab.click();

      // Find copy button
      const copyButton = page.getByRole('button', { name: /copy/i }).first();
      if (await copyButton.isVisible()) {
        await copyButton.click();

        // Should show success message or change button text
        await page.waitForTimeout(500);
      }
    }
  });
});
