const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';
const USE_MOCKS = (import.meta.env.VITE_USE_MOCKS ?? 'true') !== 'false';

export interface IHttpClient {
  get<TResponse>(path: string): Promise<TResponse>;
  post<TRequest, TResponse>(path: string, body: TRequest): Promise<TResponse>;
}

export class FetchHttpClient implements IHttpClient {
  constructor(private readonly baseUrl: string = API_BASE_URL) {}

  async get<TResponse>(path: string): Promise<TResponse> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`HTTP GET ${path} failed with status ${response.status}`);
    }
    return (await response.json()) as TResponse;
  }

  async post<TRequest, TResponse>(path: string, body: TRequest): Promise<TResponse> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error(`HTTP POST ${path} failed with status ${response.status}`);
    }
    return (await response.json()) as TResponse;
  }
}

export const httpClient: IHttpClient = new FetchHttpClient();
export const isMockMode = (): boolean => USE_MOCKS;

