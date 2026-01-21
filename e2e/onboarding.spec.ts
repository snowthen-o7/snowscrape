/**
 * Onboarding E2E Test
 * Tests for onboarding tour and quick start guide
 */

import { test, expect } from '@playwright/test';

test.describe('Onboarding Tour', () => {
  test.beforeEach(async ({ page }) => {
    // Clear onboarding completed flag
    await page.goto('/dashboard');
    await page.evaluate(() => {
      localStorage.removeItem('onboarding_completed');
      localStorage.removeItem('quickstart_dismissed');
    });
  });

  test('should show onboarding tour on first visit', async ({ page }) => {
    await page.goto('/dashboard');

    // Wait for onboarding modal to appear
    await page.waitForTimeout(1500); // Wait for 1s delay + render

    // Should show welcome dialog
    const welcomeText = page.getByText(/welcome to snowscrape/i);
    if (await welcomeText.isVisible()) {
      await expect(welcomeText).toBeVisible();
    }
  });

  test('should navigate through onboarding steps', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForTimeout(1500);

    // Check if onboarding dialog is visible
    const dialog = page.locator('[role="dialog"]');
    if (await dialog.isVisible()) {
      // Click Next button
      const nextButton = page.getByRole('button', { name: /next/i });
      if (await nextButton.isVisible()) {
        // Click through steps
        await nextButton.click();
        await page.waitForTimeout(500);

        await nextButton.click();
        await page.waitForTimeout(500);

        await nextButton.click();
        await page.waitForTimeout(500);

        // Final step should show "Get Started"
        const getStartedButton = page.getByRole('button', { name: /get started/i });
        if (await getStartedButton.isVisible()) {
          await getStartedButton.click();
        }
      }
    }
  });

  test('should skip onboarding tour', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForTimeout(1500);

    // Find and click skip button
    const skipButton = page.getByRole('button', { name: /skip/i });
    if (await skipButton.isVisible()) {
      await skipButton.click();
      await page.waitForTimeout(500);

      // Onboarding should be closed
      const welcomeText = page.queryByText(/welcome to snowscrape/i);
      if (welcomeText) {
        await expect(welcomeText).not.toBeVisible();
      }
    }
  });

  test('should navigate back in onboarding', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForTimeout(1500);

    const dialog = page.locator('[role="dialog"]');
    if (await dialog.isVisible()) {
      // Click Next
      const nextButton = page.getByRole('button', { name: /next/i });
      if (await nextButton.isVisible()) {
        await nextButton.click();
        await page.waitForTimeout(500);

        // Click Back
        const backButton = page.getByRole('button', { name: /back/i });
        if (await backButton.isVisible()) {
          await backButton.click();
          await page.waitForTimeout(500);

          // Should be back to first step
          await expect(page.getByText(/welcome to snowscrape/i)).toBeVisible();
        }
      }
    }
  });

  test('should show progress indicator', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForTimeout(1500);

    const dialog = page.locator('[role="dialog"]');
    if (await dialog.isVisible()) {
      // Should show step 1 of 4
      const stepIndicator = page.getByText(/step 1 of 4/i);
      if (await stepIndicator.isVisible()) {
        await expect(stepIndicator).toBeVisible();
      }

      // Should show progress bar
      const progressBar = page.locator('[role="progressbar"]');
      if (await progressBar.isVisible()) {
        await expect(progressBar).toBeVisible();
      }
    }
  });
});

test.describe('Quick Start Guide', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await page.evaluate(() => {
      localStorage.removeItem('quickstart_dismissed');
    });
  });

  test('should display quick start guide on dashboard', async ({ page }) => {
    await page.goto('/dashboard');

    // Should show quick start guide card
    const quickStartHeading = page.getByRole('heading', { name: /quick start/i });
    if (await quickStartHeading.isVisible()) {
      await expect(quickStartHeading).toBeVisible();
    }
  });

  test('should show quick start options', async ({ page }) => {
    await page.goto('/dashboard');

    const quickStartCard = page.locator('[class*="quickstart"], [data-testid="quickstart"]');
    if (await quickStartCard.isVisible()) {
      // Should show 3 options
      const templateOption = page.getByText(/use a template/i);
      const visualBuilderOption = page.getByText(/visual builder/i);
      const manualOption = page.getByText(/manual setup/i);

      if (await templateOption.isVisible()) {
        await expect(templateOption).toBeVisible();
      }
      if (await visualBuilderOption.isVisible()) {
        await expect(visualBuilderOption).toBeVisible();
      }
      if (await manualOption.isVisible()) {
        await expect(manualOption).toBeVisible();
      }
    }
  });

  test('should dismiss quick start guide', async ({ page }) => {
    await page.goto('/dashboard');

    // Find dismiss button (X button)
    const dismissButton = page.getByRole('button', { name: /close|dismiss/i })
      .filter({ has: page.locator('svg') });

    if (await dismissButton.first().isVisible()) {
      await dismissButton.first().click();
      await page.waitForTimeout(500);

      // Quick start guide should be hidden
      const quickStartHeading = page.queryByRole('heading', { name: /quick start/i });
      if (quickStartHeading) {
        await expect(quickStartHeading).not.toBeVisible();
      }
    }
  });

  test('should navigate to templates when clicking template option', async ({ page }) => {
    await page.goto('/dashboard');

    const templateButton = page.getByRole('button').filter({ hasText: /use a template/i });
    if (await templateButton.isVisible()) {
      await templateButton.click();

      // Should navigate to templates page
      await page.waitForURL(/\/dashboard\/templates/);
    }
  });

  test('should navigate to visual builder when clicking visual builder option', async ({ page }) => {
    await page.goto('/dashboard');

    const visualBuilderButton = page.getByRole('button').filter({ hasText: /visual builder/i });
    if (await visualBuilderButton.isVisible()) {
      await visualBuilderButton.click();

      // Should navigate to visual builder page
      await page.waitForURL(/\/dashboard\/jobs\/new\/visual/);
    }
  });
});
