const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';
const USE_MOCKS = (import.meta.env.VITE_USE_MOCKS ?? 'true') !== 'false';

let activeAccessToken: string | null = null;

export function setAuthAccessToken(token: string | null): void {
  activeAccessToken = token;
}

export function getAuthAccessToken(): string | null {
  return activeAccessToken;
}

export interface IHttpClient {
  get<TResponse>(path: string): Promise<TResponse>;
  post<TRequest, TResponse>(path: string, body: TRequest): Promise<TResponse>;
}

async function extractErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { error?: { message?: string } };
    if (body?.error?.message) {
      return body.error.message;
    }
  } catch {
    // Ignore non-JSON error bodies
  }
  return fallback;
}

export class FetchHttpClient implements IHttpClient {
  constructor(private readonly baseUrl: string = API_BASE_URL) {}

  private buildHeaders(includeJsonContentType = false): Record<string, string> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
    };
    if (includeJsonContentType) {
      headers['Content-Type'] = 'application/json';
    }
    if (activeAccessToken) {
      headers.Authorization = `Bearer ${activeAccessToken}`;
    }
    return headers;
  }

  async get<TResponse>(path: string): Promise<TResponse> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      headers: this.buildHeaders(false),
    });
    if (!response.ok) {
      const msg = await extractErrorMessage(
        response,
        `HTTP GET ${path} failed with status ${response.status}`,
      );
      throw new Error(msg);
    }
    return (await response.json()) as TResponse;
  }

  async post<TRequest, TResponse>(path: string, body: TRequest): Promise<TResponse> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: this.buildHeaders(true),
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const msg = await extractErrorMessage(
        response,
        `HTTP POST ${path} failed with status ${response.status}`,
      );
      throw new Error(msg);
    }
    return (await response.json()) as TResponse;
  }
}

export const httpClient: IHttpClient = new FetchHttpClient();
export const isMockMode = (): boolean => USE_MOCKS;
