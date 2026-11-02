export interface SystemParametersDto {
  parameterVersion: string;
  similarityThreshold: number;
  timeWindowMinutes: number;
  collectionIntervalMinutes: number;
  minClusterChannels: number;
  updatedAt: string;
  updatedBy: string;
}

export interface UpdateSystemParametersInputDto {
  similarityThreshold: number;
  timeWindowMinutes: number;
  collectionIntervalMinutes: number;
  minClusterChannels: number;
}

