import { test, expect } from '@playwright/test';

test.describe('Factory AI Code Verification E2E Smoke Tests', () => {
  test('Happy Path: Connect -> Select Repo -> Select PR #142 -> Verify -> VERIFIED result', async ({ page }) => {
    // 1. Visit Landing page
    await page.goto('/');

    // 2. Click Connect GitHub CTA
    const connectBtn = page.getByTestId('hero-connect-btn');
    await connectBtn.click();

    // 3. Should navigate to /repos screen
    await expect(page).toHaveURL(/\/repos/);
    await expect(page.getByText('SELECT REPOSITORY & PULL REQUEST')).toBeVisible();

    // 4. Select octocat/payment-gateway-service
    const repoCard = page.getByTestId('repo-card-repo-2');
    await repoCard.click();

    // 5. Select PR #142 (Verified sample) & Click Verify Code
    const verifyBtn = page.getByTestId('verify-btn-142');
    await expect(verifyBtn).toBeVisible();
    await verifyBtn.click();

    // 6. Should navigate to /verify progress pipeline
    await expect(page).toHaveURL(/\/verify/);
    await expect(page.getByText('VERIFICATION IN PROGRESS')).toBeVisible();

    // Fast-forward or wait for view results button
    const viewResultsBtn = page.getByTestId('view-results-btn');
    await viewResultsBtn.waitFor({ state: 'visible', timeout: 15000 });
    await viewResultsBtn.click();

    // 7. Should land on Results page with VERIFIED state
    await expect(page).toHaveURL(/\/results/);
    const verdictTitle = page.getByTestId('verdict-title');
    await expect(verdictTitle).toHaveText('VERIFIED');
    await expect(page.getByTestId('summary-card-tests')).toContainText('18 / 18 PASSED');
    await expect(page.getByTestId('requirements-checklist')).toBeVisible();
  });

  test('Failure Path: Connect -> Select Repo -> Select PR #89 -> Verify -> REQUIREMENT_VIOLATION result with issues', async ({ page }) => {
    // 1. Visit Landing page
    await page.goto('/');

    // 2. Click Connect GitHub CTA
    const connectBtn = page.getByTestId('hero-connect-btn');
    await connectBtn.click();

    // 3. Should navigate to /repos screen
    await expect(page).toHaveURL(/\/repos/);

    // 4. Default repo acme-corp/auth-core is active. Select PR #89 (Violation sample)
    const verifyBtn = page.getByTestId('verify-btn-89');
    await expect(verifyBtn).toBeVisible();
    await verifyBtn.click();

    // 5. Progress pipeline
    await expect(page).toHaveURL(/\/verify/);

    // 6. Navigate to results once completed
    const viewResultsBtn = page.getByTestId('view-results-btn');
    await viewResultsBtn.waitFor({ state: 'visible', timeout: 15000 });
    await viewResultsBtn.click();

    // 7. Should land on Results page with REQUIREMENT_VIOLATION state
    await expect(page).toHaveURL(/\/results/);
    const verdictTitle = page.getByTestId('verdict-title');
    await expect(verdictTitle).toHaveText('REQUIREMENT VIOLATION');
    await expect(page.getByTestId('summary-card-tests')).toContainText('14 / 17 PASSED');

    // 8. Issues list must be visible with at least one critical violation
    const issuesContainer = page.getByTestId('issues-container');
    await expect(issuesContainer).toBeVisible();
    await expect(page.getByText('Session Revocation Does Not Cascade to Child Sessions')).toBeVisible();
  });
});
