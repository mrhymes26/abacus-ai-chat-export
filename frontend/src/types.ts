export type ChatType = "ai_chat" | "deployment_conversation";
export type ExportFormat = "json" | "html" | "markdown";
export type ExportMode = "selected" | "all";
export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface StatusResponse {
  has_env_api_key: boolean;
  has_stored_api_key: boolean;
  allow_persistent_api_key: boolean;
  connected: boolean;
  deployment_ids: string[];
  conversation_scopes: Record<string, string[]>;
  stored_conversation_scopes: Record<string, string[]>;
  data_dir: string;
}

export interface ConnectionResult {
  connected: boolean;
  source: "ui" | "env" | "stored" | "none";
  persisted: boolean;
  available_methods: string[];
  missing_methods: string[];
  warnings?: string[];
}

export interface ChatItem {
  id: string;
  type: ChatType;
  deployment_id?: string | null;
  title?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  last_event_created_at?: string | null;
  message_count?: number | null;
  raw_preview?: Record<string, unknown> | null;
  exportable: boolean;
  selected: boolean;
}

export interface ChatListResponse {
  items: ChatItem[];
  counts: Record<string, number>;
  warnings: string[];
}

export interface ConversationScopes {
  deployment_ids: string[];
  external_application_ids: string[];
  conversation_types: string[];
}

export interface ExportRequest {
  mode: ExportMode;
  chat_ids: string[];
  types: ChatType[];
  formats: ExportFormat[];
  deployment_ids?: string[];
  external_application_ids?: string[];
  conversation_types?: string[];
  zip: boolean;
}

export interface ExportStartResponse {
  job_id: string;
}

export interface BackupJob {
  job_id: string;
  status: JobStatus;
  progress: {
    total: number;
    done: number;
    failed: number;
    percent: number;
  };
  current_item?: string | null;
  errors: string[];
  result?: {
    backup_id?: string;
    backup_path?: string;
    zip_path?: string | null;
    download_url?: string;
  } | null;
}

export interface BackupSummary {
  backup_id: string;
  created_at: string;
  counts: Record<string, number>;
  path: string;
  zip_available: boolean;
  download_url?: string | null;
  size_bytes?: number | null;
}

export interface BackupListResponse {
  items: BackupSummary[];
}

export interface ToastMessage {
  id: number;
  type: "success" | "error" | "info";
  message: string;
}
