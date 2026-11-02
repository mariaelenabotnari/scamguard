import type {
  AuthSessionDto,
  AuthUserDto,
  LoginInputDto,
  RegisterInputDto,
  UserRole,
} from '../dtos/auth.dto';
import {
  httpClient,
  isMockMode,
  setAuthAccessToken,
  type IHttpClient,
} from '../lib/api/http-client';

const DEFAULT_MOCK_USER: AuthUserDto = {
  id: 'usr-elena-01',
  email: 'elena.botnari@scamguard.md',
  fullName: 'Elena Botnari',
  organization: 'Moldova Civic Media Lab',
  role: 'admin',
  accountAgeDays: 45,
};

export interface IAuthService {
  getCurrentUser(): Promise<AuthUserDto | null>;
  login(input: LoginInputDto): Promise<AuthSessionDto>;
  register(input: RegisterInputDto): Promise<AuthSessionDto>;
  switchMockRole(role: UserRole): Promise<AuthUserDto>;
  logout(): Promise<void>;
}

export class AuthService implements IAuthService {
  private currentUser: AuthUserDto | null = { ...DEFAULT_MOCK_USER };

  constructor(private readonly client: IHttpClient = httpClient) {}

  async getCurrentUser(): Promise<AuthUserDto | null> {
    if (isMockMode()) {
      return Promise.resolve(this.currentUser ? { ...this.currentUser } : null);
    }
    return this.client.get<AuthUserDto>('/auth/me');
  }

  async login(input: LoginInputDto): Promise<AuthSessionDto> {
    if (!input.email.includes('@') || input.password.trim().length < 6) {
      return Promise.reject(
        new Error('Enter a valid email address and a password of at least 6 characters.'),
      );
    }

    if (isMockMode()) {
      const role: UserRole = input.email.toLowerCase().includes('admin')
        ? 'admin'
        : 'journalist';
      const user: AuthUserDto = {
        id: 'usr-session-01',
        email: input.email.trim(),
        fullName: input.email.split('@')[0] || 'Researcher',
        organization: 'Independent Newsroom',
        role,
        accountAgeDays: 14,
      };
      this.currentUser = user;
      setAuthAccessToken('mock-jwt-token-scamguard');
      return Promise.resolve({
        accessToken: 'mock-jwt-token-scamguard',
        user,
      });
    }

    const session = await this.client.post<LoginInputDto, AuthSessionDto>('/auth/login', input);
    setAuthAccessToken(session.accessToken);
    return session;
  }

  async register(input: RegisterInputDto): Promise<AuthSessionDto> {
    if (!input.fullName.trim()) {
      return Promise.reject(new Error('Full name is required for researcher registration.'));
    }
    if (!input.email.includes('@')) {
      return Promise.reject(new Error('Enter a valid work or newsroom email address.'));
    }
    if (input.password.trim().length < 8) {
      return Promise.reject(new Error('Password must be at least 8 characters long.'));
    }

    if (isMockMode()) {
      const user: AuthUserDto = {
        id: `usr-${Date.now()}`,
        email: input.email.trim(),
        fullName: input.fullName.trim(),
        organization: input.organization.trim() || 'Independent Researcher',
        role: 'journalist',
        accountAgeDays: 0,
      };
      this.currentUser = user;
      setAuthAccessToken('mock-jwt-token-registered');
      return Promise.resolve({
        accessToken: 'mock-jwt-token-registered',
        user,
      });
    }

    const session = await this.client.post<RegisterInputDto, AuthSessionDto>(
      '/auth/register',
      input,
    );
    setAuthAccessToken(session.accessToken);
    return session;
  }

  async switchMockRole(role: UserRole): Promise<AuthUserDto> {
    const base = this.currentUser ?? DEFAULT_MOCK_USER;
    const updated: AuthUserDto = {
      ...base,
      role,
    };
    this.currentUser = updated;
    return Promise.resolve(updated);
  }

  async logout(): Promise<void> {
    if (isMockMode()) {
      this.currentUser = null;
      setAuthAccessToken(null);
      return Promise.resolve();
    }
    await this.client.post<Record<string, never>, unknown>('/auth/logout', {});
    setAuthAccessToken(null);
  }
}

export const authService: IAuthService = new AuthService();

