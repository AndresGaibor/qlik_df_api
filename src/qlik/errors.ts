export class QlikAutomationError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = new.target.name;
  }
}

export class AuthenticationError extends QlikAutomationError {}
export class TenantNotFoundError extends QlikAutomationError {}
export class SpaceNotFoundError extends QlikAutomationError {}
export class DataflowNotFoundError extends QlikAutomationError {}
export class DownloadError extends QlikAutomationError {}
