import type {
  AuthSessionDto,
  AuthUserDto,
  LoginInputDto,
  RegisterInputDto,
  UserRole,
  VerificationResponseDto,
  VerifyEmailInputDto,
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
  username: 'elena.botnari',
  fullName: 'Elena Botnari',
  organization: 'Moldova Civic Media Lab',
  role: 'admin',
  isVerified: true,
  accountAgeDays: 45,
};

const CLEAN_PROFILE_STORAGE_KEY = 'choruswatch_clean_profile';

export interface IAuthService {
  getCurrentUser(): Promise<AuthUserDto | null>;
  login(input: LoginInputDto): Promise<AuthSessionDto>;
  register(input: RegisterInputDto): Promise<VerificationResponseDto>;
  verifyEmail(input: VerifyEmailInputDto): Promise<AuthSessionDto>;
  resendCode(email: string): Promise<VerificationResponseDto>;
  switchMockRole(role: UserRole): Promise<AuthUserDto>;
  logout(): Promise<void>;
  isCleanProfile(): boolean;
  setCleanProfile(val: boolean): void;
}

export class AuthService implements IAuthService {
  private currentUser: AuthUserDto | null = { ...DEFAULT_MOCK_USER };
  private pendingRegistrations = new Map<string, { input: RegisterInputDto; code: string }>();

  constructor(private readonly client: IHttpClient = httpClient) {
    if (this.isCleanProfile()) {
      this.currentUser = {
        id: 'usr-new-investigator',
        email: 'researcher@news.md',
        username: 'new_investigator',
        fullName: 'New Investigator',
        organization: 'Independent Desk',
        role: 'journalist',
        isVerified: true,
        accountAgeDays: 0,
      };
    }
  }

  isCleanProfile(): boolean {
    try {
      return localStorage.getItem(CLEAN_PROFILE_STORAGE_KEY) === 'true';
    } catch {
      return false;
    }
  }

  setCleanProfile(val: boolean): void {
    try {
      if (val) {
        localStorage.setItem(CLEAN_PROFILE_STORAGE_KEY, 'true');
      } else {
        localStorage.removeItem(CLEAN_PROFILE_STORAGE_KEY);
      }
    } catch {
      // Ignore storage errors in headless tests
    }
  }

  async getCurrentUser(): Promise<AuthUserDto | null> {
    if (isMockMode()) {
      return Promise.resolve(this.currentUser ? { ...this.currentUser } : null);
    }
    return this.client.get<AuthUserDto>('/auth/me');
  }

  async login(input: LoginInputDto): Promise<AuthSessionDto> {
    const identifier = (input.login || input.username || input.email || '').trim();
    const isEmail = identifier.includes('@');
    const isValidUsername = /^[a-zA-Z0-9_]{3,30}$/.test(identifier);

    if (!identifier || (!isEmail && !isValidUsername) || input.password.trim().length < 6) {
      return Promise.reject(
        new Error('Enter a valid email address and a password of at least 6 characters.'),
      );
    }

    if (isMockMode()) {
      const isNew = identifier.toLowerCase().includes('new') || this.isCleanProfile();
      const role: UserRole =
        identifier.toLowerCase().includes('admin') || identifier.toLowerCase().includes('elena')
          ? 'admin'
          : 'journalist';
      const user: AuthUserDto = {
        id: `usr-${Date.now()}`,
        email: identifier.includes('@') ? identifier : `${identifier}@newsroom.md`,
        username: identifier.replace('@', ''),
        fullName: identifier.includes('@') ? identifier.split('@')[0] : identifier,
        organization: 'Independent Newsroom',
        role,
        isVerified: true,
        accountAgeDays: isNew ? 0 : 14,
      };
      this.currentUser = user;
      this.setCleanProfile(isNew);
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

  async register(input: RegisterInputDto): Promise<VerificationResponseDto> {
    const rawName = (input.fullName || input.username || '').trim();
    if (!rawName) {
      return Promise.reject(new Error('Full name is required for researcher registration.'));
    }
    if (!input.email.includes('@')) {
      return Promise.reject(new Error('Enter a valid work or newsroom email address.'));
    }
    if (input.password.trim().length < 8) {
      return Promise.reject(new Error('Password must be at least 8 characters long.'));
    }

    if (isMockMode()) {
      const code = '123456';
      this.pendingRegistrations.set(input.email.toLowerCase().trim(), { input, code });
      return Promise.resolve({
        message: 'Verification code sent to your email.',
        email: input.email.trim(),
        code,
        requiresVerification: true,
      });
    }

    return this.client.post<RegisterInputDto, VerificationResponseDto>(
      '/auth/register',
      input,
    );
  }

  async verifyEmail(input: VerifyEmailInputDto): Promise<AuthSessionDto> {
    const cleanEmail = input.email.trim().toLowerCase();
    const cleanCode = input.code.trim();

    if (!cleanCode || cleanCode.length < 6) {
      return Promise.reject(new Error('Please enter a valid 6-digit verification code.'));
    }

    if (isMockMode()) {
      const pending = this.pendingRegistrations.get(cleanEmail);
      if (cleanCode !== '123456' && (!pending || pending.code !== cleanCode)) {
        return Promise.reject(
          new Error('Invalid verification code. Please check your email or enter 123456.'),
        );
      }
      const rawUser = pending?.input;
      const username = rawUser?.username || cleanEmail.split('@')[0];
      const fullName = rawUser?.fullName || username;
      const user: AuthUserDto = {
        id: `usr-${Date.now()}`,
        email: cleanEmail,
        username,
        fullName,
        organization: rawUser?.organization || 'Independent Researcher',
        role: 'journalist',
        isVerified: true,
        accountAgeDays: 0,
      };
      this.currentUser = user;
      this.setCleanProfile(true);
      setAuthAccessToken('mock-jwt-token-verified');
      return Promise.resolve({
        accessToken: 'mock-jwt-token-verified',
        user,
      });
    }

    const session = await this.client.post<VerifyEmailInputDto, AuthSessionDto>(
      '/auth/verify-email',
      input,
    );
    this.setCleanProfile(true);
    setAuthAccessToken(session.accessToken);
    return session;
  }

  async resendCode(email: string): Promise<VerificationResponseDto> {
    if (isMockMode()) {
      return Promise.resolve({
        message: 'A new 6-digit verification code was sent to your email.',
        email,
        code: '123456',
        requiresVerification: true,
      });
    }
    return this.client.post<{ email: string }, VerificationResponseDto>(
      '/auth/resend-code',
      { email },
    );
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
    this.currentUser = null;
    this.setCleanProfile(false);
    setAuthAccessToken(null);
    if (!isMockMode()) {
      await this.client.post<Record<string, never>, unknown>('/auth/logout', {});
    }
  }
}

export const authService: IAuthService = new AuthService();
