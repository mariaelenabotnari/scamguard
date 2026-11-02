export type UserRole = 'visitor' | 'journalist' | 'admin';

export interface AuthUserDto {
  id: string;
  email: string;
  fullName: string;
  organization: string;
  role: UserRole;
  accountAgeDays: number;
}

export interface LoginInputDto {
  email: string;
  password: string;
}

export interface RegisterInputDto {
  fullName: string;
  email: string;
  organization: string;
  password: string;
}

export interface AuthSessionDto {
  accessToken: string;
  user: AuthUserDto;
}

