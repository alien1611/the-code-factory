import { test, expect } from '@playwright/test';

test.describe('Factory AI Code Verification E2E Smoke Tests', () => {
  test('Happy Path: Connect -> Select Repo -> Select PR -> Verify -> VERIFIED result', async ({ page }) => {
    // 1. Visit Landing page
    await page.goto('/');

    // 2. Click Connect GitHub CTA
    const connectBtn = page.getByTestId('hero-connect-btn');
    await connectBtn.click();

    // 3. Should navigate to /repos screen
    await expect(page).toHaveURL(/\/repos/);
    await expect(page.getByText('SELECT REPOSITORY & PULL REQUEST')).toBeVisible();

    // 4. Select active repository card
    const repoCard = page.locator('[data-testid^="repo-card-"]').first();
    await expect(repoCard).toBeVisible({ timeout: 10000 });
    await repoCard.click();

    // 5. Select first PR & Click Verify Code
    const verifyBtn = page.locator('[data-testid^="verify-btn-"]').first();
    await expect(verifyBtn).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(300);
    await verifyBtn.click();

    // 6. Should navigate to /verify progress pipeline
    await expect(page).toHaveURL(/\/verify/);
    await expect(page.getByText('VERIFICATION IN PROGRESS')).toBeVisible();

    // Fast-forward or wait for view results button
    const viewResultsBtn = page.getByTestId('view-results-btn');
    await viewResultsBtn.waitFor({ state: 'visible', timeout: 15000 });
    await viewResultsBtn.click();

    // 7. Should land on Results page
    await expect(page).toHaveURL(/\/results/);
    const verdictTitle = page.getByTestId('verdict-title');
    await expect(verdictTitle).toBeVisible();
    await expect(page.getByTestId('requirements-checklist')).toBeVisible();
  });

  test('Failure Path: Connect -> Select Repo -> Select PR -> Verify -> Violation / Diagnostics result', async ({ page }) => {
    // 1. Visit Landing page
    await page.goto('/');

    // 2. Click Connect GitHub CTA
    const connectBtn = page.getByTestId('hero-connect-btn');
    await connectBtn.click();

    // 3. Should navigate to /repos screen
    await expect(page).toHaveURL(/\/repos/);

    // 4. Select repository card
    const repoCard = page.locator('[data-testid^="repo-card-"]').first();
    await expect(repoCard).toBeVisible({ timeout: 10000 });
    await repoCard.click();

    const verifyBtn = page.locator('[data-testid^="verify-btn-"]').first();
    await expect(verifyBtn).toBeVisible();
    await verifyBtn.click();

    // 5. Progress pipeline
    await expect(page).toHaveURL(/\/verify/);

    // 6. Navigate to results once completed
    const viewResultsBtn = page.getByTestId('view-results-btn');
    await viewResultsBtn.waitFor({ state: 'visible', timeout: 15000 });
    await viewResultsBtn.click();

    // 7. Should land on Results page
    await expect(page).toHaveURL(/\/results/);
    const verdictTitle = page.getByTestId('verdict-title');
    await expect(verdictTitle).toBeVisible();
  });
});
