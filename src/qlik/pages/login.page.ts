import { expect, type Page } from '@playwright/test';
import { AuthenticationError } from '../errors.js';
import { selectoresQlik } from '../selectors.js';

export class LoginPage {
  constructor(private readonly page: Page) {}

  async login(email: string, password: string): Promise<void> {
    await this.page.getByLabel(selectoresQlik.loginEmail).fill(email);
    await this.page.getByLabel(selectoresQlik.loginPassword).fill(password);
    await this.page.getByRole('button', { name: selectoresQlik.loginButton }).click();

    const blockingChallenge = this.page.getByText(/multi-factor|two-factor|mfa|sso|captcha/i);
    if (await blockingChallenge.count()) {
      throw new AuthenticationError('Qlik requiere MFA, SSO o CAPTCHA; completa el desafio manualmente.');
    }

    await expect(this.page).not.toHaveURL(/login|auth0/i, { timeout: 30_000 });
  }
}
