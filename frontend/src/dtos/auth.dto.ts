export type UserRole = 'visitor' | 'journalist' | 'admin';

export interface AuthUserDto {
  id: string;
  email: string;
  username?: string;
  fullName: string;
  organization: string;
  role: UserRole;
  isVerified?: boolean;
  accountAgeDays: number;
}

export interface LoginInputDto {
  email?: string;
  username?: string;
  login?: string;
  password: string;
}

export interface RegisterInputDto {
  username?: string;
  fullName: string;
  email: string;
  organization?: string;
  password: string;
}

export interface VerifyEmailInputDto {
  email: string;
  code: string;
}

export interface VerificationResponseDto {
  message: string;
  email: string;
  code?: string;
  requiresVerification: boolean;
}

export interface AuthSessionDto {
  accessToken: string;
  user: AuthUserDto;
}

