export interface ApiResponse<T> {
  code: number
  data: T
  message: string
}

export interface HealthResponse {
  status: string
  version: string
}
