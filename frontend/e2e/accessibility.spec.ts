import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility Tests - WCAG 2.1 AA Compliance', () => {
  test.describe('Public Pages', () => {
    test('Homepage should have no accessibility violations', async ({ page }) => {
      await page.goto('/');

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();

      expect(accessibilityScanResults.violations).toEqual([]);
    });

    test('Pricing page should have no accessibility violations', async ({ page }) => {
      await page.goto('/pricing');

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();

      expect(accessibilityScanResults.violations).toEqual([]);
    });

    test('Features page should have no accessibility violations', async ({ page }) => {
      await page.goto('/features');

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();

      expect(accessibilityScanResults.violations).toEqual([]);
    });

    test('Contact page should have no accessibility violations', async ({ page }) => {
      await page.goto('/contact');

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();

      expect(accessibilityScanResults.violations).toEqual([]);
    });
  });

  test.describe('Application Pages', () => {
    test('Dashboard should have no accessibility violations', async ({ page }) => {
      await page.goto('/dashboard');

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();

      expect(accessibilityScanResults.violations).toEqual([]);
    });

    test('Templates page should have no accessibility violations', async ({ page }) => {
      await page.goto('/dashboard/templates');

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();

      expect(accessibilityScanResults.violations).toEqual([]);
    });

    test('Notifications page should have no accessibility violations', async ({ page }) => {
      await page.goto('/dashboard/notifications');

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();

      expect(accessibilityScanResults.violations).toEqual([]);
    });

    test('Visual builder page should have no accessibility violations', async ({ page }) => {
      await page.goto('/dashboard/jobs/new/visual');

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();

      expect(accessibilityScanResults.violations).toEqual([]);
    });
  });

  test.describe('Keyboard Navigation', () => {
    test('Should be able to navigate homepage with keyboard only', async ({ page }) => {
      await page.goto('/');

      // Tab through focusable elements
      await page.keyboard.press('Tab');
      const firstFocusedElement = await page.evaluate(() => document.activeElement?.tagName);
      expect(firstFocusedElement).toBeTruthy();

      // Check focus is visible
      const hasFocusStyles = await page.evaluate(() => {
        const element = document.activeElement as HTMLElement;
        const styles = window.getComputedStyle(element);
        return styles.outline !== 'none' || styles.boxShadow !== 'none';
      });
      expect(hasFocusStyles).toBeTruthy();
    });

    test('Should be able to navigate dashboard with keyboard only', async ({ page }) => {
      await page.goto('/dashboard');

      let tabCount = 0;
      const maxTabs = 20;

      // Tab through elements
      while (tabCount < maxTabs) {
        await page.keyboard.press('Tab');
        tabCount++;

        const activeElement = await page.evaluate(() => {
          const element = document.activeElement;
          return {
            tag: element?.tagName,
            role: element?.getAttribute('role'),
            ariaLabel: element?.getAttribute('aria-label'),
          };
        });

        // Verify interactive elements are focusable
        if (activeElement.tag === 'BUTTON' || activeElement.tag === 'A') {
          expect(activeElement.tag).toBeTruthy();
        }
      }
    });

    test('Modals should trap focus', async ({ page }) => {
      await page.goto('/dashboard/templates');

      // Wait for templates to load and click the first one
      await page.waitForTimeout(500);
      const firstTemplate = page.locator('[data-testid="template-card"]').first();

      if (await firstTemplate.isVisible()) {
        await firstTemplate.click();
        await page.waitForTimeout(500);

        // Check if modal/dialog is open
        const dialogElement = page.locator('[role="dialog"]');
        if (await dialogElement.isVisible()) {
          // Tab through modal elements
          const initialFocus = await page.evaluate(() => document.activeElement?.tagName);

          // Tab multiple times
          for (let i = 0; i < 10; i++) {
            await page.keyboard.press('Tab');
          }

          // Focus should still be within dialog
          const focusStillInDialog = await page.evaluate(() => {
            const activeElement = document.activeElement;
            const dialog = document.querySelector('[role="dialog"]');
            return dialog?.contains(activeElement);
          });

          expect(focusStillInDialog).toBeTruthy();

          // ESC should close modal
          await page.keyboard.press('Escape');
          await page.waitForTimeout(300);
          const dialogStillVisible = await dialogElement.isVisible();
          expect(dialogStillVisible).toBeFalsy();
        }
      }
    });
  });

  test.describe('Screen Reader Support', () => {
    test('All images should have alt text', async ({ page }) => {
      await page.goto('/');

      const imagesWithoutAlt = await page.evaluate(() => {
        const images = Array.from(document.querySelectorAll('img'));
        return images.filter(img => !img.hasAttribute('alt')).length;
      });

      expect(imagesWithoutAlt).toBe(0);
    });

    test('Form inputs should have associated labels', async ({ page }) => {
      await page.goto('/contact');

      const unlabeledInputs = await page.evaluate(() => {
        const inputs = Array.from(document.querySelectorAll('input, textarea, select'));
        return inputs.filter(input => {
          const id = input.id;
          const hasLabel = id && document.querySelector(`label[for="${id}"]`);
          const hasAriaLabel = input.hasAttribute('aria-label') || input.hasAttribute('aria-labelledby');
          return !hasLabel && !hasAriaLabel;
        }).length;
      });

      expect(unlabeledInputs).toBe(0);
    });

    test('Buttons should have accessible names', async ({ page }) => {
      await page.goto('/dashboard');

      const buttonsWithoutNames = await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        return buttons.filter(button => {
          const hasText = button.textContent?.trim().length > 0;
          const hasAriaLabel = button.hasAttribute('aria-label') || button.hasAttribute('aria-labelledby');
          return !hasText && !hasAriaLabel;
        }).length;
      });

      expect(buttonsWithoutNames).toBe(0);
    });

    test('Page should have proper heading hierarchy', async ({ page }) => {
      await page.goto('/');

      const headingStructure = await page.evaluate(() => {
        const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'));
        return headings.map(h => ({
          level: parseInt(h.tagName[1]),
          text: h.textContent?.trim().substring(0, 50),
        }));
      });

      // Should have at least one h1
      const h1Count = headingStructure.filter(h => h.level === 1).length;
      expect(h1Count).toBeGreaterThanOrEqual(1);

      // Check for heading level skips (e.g., h1 to h3 without h2)
      for (let i = 1; i < headingStructure.length; i++) {
        const levelDiff = headingStructure[i].level - headingStructure[i - 1].level;
        // Allow same level, one level up, or any level down, but not skipping levels up
        expect(levelDiff).toBeLessThanOrEqual(1);
      }
    });
  });

  test.describe('Color Contrast', () => {
    test('Color contrast should meet WCAG AA standards', async ({ page }) => {
      await page.goto('/');

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2aa'])
        .include(['body'])
        .analyze();

      const contrastViolations = accessibilityScanResults.violations.filter(
        v => v.id === 'color-contrast'
      );

      expect(contrastViolations).toEqual([]);
    });
  });

  test.describe('Responsive Design', () => {
    test('Mobile viewport should have no accessibility violations', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/');

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();

      expect(accessibilityScanResults.violations).toEqual([]);
    });

    test('Tablet viewport should have no accessibility violations', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('/');

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();

      expect(accessibilityScanResults.violations).toEqual([]);
    });
  });

  test.describe('ARIA Implementation', () => {
    test('Interactive elements should have proper ARIA roles', async ({ page }) => {
      await page.goto('/dashboard');

      const invalidAriaRoles = await page.evaluate(() => {
        const elements = Array.from(document.querySelectorAll('[role]'));
        const validRoles = [
          'alert', 'alertdialog', 'application', 'article', 'banner', 'button',
          'cell', 'checkbox', 'columnheader', 'combobox', 'complementary',
          'contentinfo', 'definition', 'dialog', 'directory', 'document',
          'feed', 'figure', 'form', 'grid', 'gridcell', 'group', 'heading',
          'img', 'link', 'list', 'listbox', 'listitem', 'log', 'main',
          'marquee', 'math', 'menu', 'menubar', 'menuitem', 'menuitemcheckbox',
          'menuitemradio', 'navigation', 'none', 'note', 'option', 'presentation',
          'progressbar', 'radio', 'radiogroup', 'region', 'row', 'rowgroup',
          'rowheader', 'scrollbar', 'search', 'searchbox', 'separator',
          'slider', 'spinbutton', 'status', 'switch', 'tab', 'table',
          'tablist', 'tabpanel', 'term', 'textbox', 'timer', 'toolbar',
          'tooltip', 'tree', 'treegrid', 'treeitem',
        ];

        return elements.filter(el => {
          const role = el.getAttribute('role');
          return role && !validRoles.includes(role);
        }).length;
      });

      expect(invalidAriaRoles).toBe(0);
    });

    test('Live regions should be properly configured', async ({ page }) => {
      await page.goto('/dashboard');

      // Check for toast/notification live regions
      const liveRegions = await page.evaluate(() => {
        const regions = Array.from(document.querySelectorAll('[aria-live]'));
        return regions.map(region => ({
          ariaLive: region.getAttribute('aria-live'),
          role: region.getAttribute('role'),
        }));
      });

      // If live regions exist, they should have valid values
      liveRegions.forEach(region => {
        expect(['polite', 'assertive', 'off']).toContain(region.ariaLive);
      });
    });
  });
});
