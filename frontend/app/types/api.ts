export type Role = 'user' | 'admin'

export interface AuthUser {
  id: number
  username: string
  role: Role
}

export interface PublicStats {
  total_requests: number
  total_tokens: number
}

export interface ApiKeyRecord {
  id: number
  name: string
  description: string
  key_preview?: string
  key?: string
  is_active: boolean
  rate_limit_per_minute: number
  rate_limit_per_hour: number
  total_requests: number
  total_tokens_processed: number
  last_used_at: string | null
  requests_this_minute?: number
  requests_this_hour?: number
  user_id?: number | null
  username?: string | null
  created_at?: string
}

export interface UsageSnapshot {
  total_requests: number
  total_tokens: number
  requests_24h: number
  requests_this_minute: number
  requests_this_hour: number
  keys: ApiKeyRecord[]
}

export interface HistoryItem {
  id: number
  model_name: string
  api_key_name: string
  status: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  created_at: string
  completed_at: string | null
  error_message?: string | null
}

export interface Pagination {
  page: number
  per_page: number
  total_pages: number
  total_count: number
  has_next: boolean
  has_previous: boolean
}

export interface HistoryPage {
  requests: HistoryItem[]
  pagination: Pagination
}

export interface ModelRecord {
  id: number
  name: string
  description: string
  model_path: string
  model_type: string
  provider: string
  is_active: boolean
  is_default: boolean
  alwayswarm: boolean
  thinking_mode: string
  ollama_base_url: string
  huggingface_token?: string
  max_context_length: number
  default_temperature: number
  default_max_tokens: number
  default_top_p: number
  default_top_k: number
  default_min_p: number
  default_presence_penalty: number
  default_repetition_penalty: number
  total_requests?: number
  total_tokens_processed?: number
  created_at?: string
}

export interface AdminUser {
  id: number
  username: string
  role: Role
  is_active: boolean
  date_joined?: string
}

export interface ChartData {
  hourly_requests: Array<{ hour: string; count: number }>
  model_usage: Array<{ name: string; request_count: number }>
  model_tokens: Array<{
    name: string
    total_tokens: number
    input_tokens: number
    output_tokens: number
  }>
  api_key_usage: Array<{ name: string; request_count: number; total_tokens: number }>
}

export const emptyModelForm = (): Partial<ModelRecord> => ({
  name: '',
  description: '',
  model_path: '',
  model_type: 'chat',
  provider: 'vllm',
  is_active: true,
  is_default: false,
  alwayswarm: false,
  thinking_mode: 'default',
  ollama_base_url: 'http://localhost:11434',
  huggingface_token: '',
  max_context_length: 4096,
  default_temperature: 0.7,
  default_max_tokens: 512,
  default_top_p: 0.95,
  default_top_k: 20,
  default_min_p: 0,
  default_presence_penalty: 1.5,
  default_repetition_penalty: 1,
})
