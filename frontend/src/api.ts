import type {
  BackupJob,
  BackupListResponse,
  ChatListResponse,
  ConnectionResult,
  ConversationScopes,
  ExportFormat,
  ExportMode,
  ExportStartResponse,
  StatusResponse
} from "./types";

async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...options, headers });
  const contentType = response.headers.get("Content-Type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof data === "object" && data && "detail" in data ? String(data.detail) : String(data || response.statusText);
    throw new Error(detail);
  }
  return data as T;
}

export function getStatus(): Promise<StatusResponse> {
  return apiRequest<StatusResponse>("/api/status");
}

export function connect(apiKey?: string, rememberLocally = false): Promise<ConnectionResult> {
  return apiRequest<ConnectionResult>("/api/connect", {
    method: "POST",
    body: JSON.stringify({ api_key: apiKey || undefined, remember_locally: rememberLocally })
  });
}

export function forgetStoredApiKey(): Promise<{ deleted: boolean }> {
  return apiRequest<{ deleted: boolean }>("/api/api-key", { method: "DELETE" });
}

export function getConversationScopes(): Promise<ConversationScopes> {
  return apiRequest<ConversationScopes>("/api/conversation-scopes");
}

export function saveConversationScopes(scopes: ConversationScopes): Promise<ConversationScopes> {
  return apiRequest<ConversationScopes>("/api/conversation-scopes", {
    method: "PUT",
    body: JSON.stringify(scopes)
  });
}

export function listChats(refresh = false, includeDeployments = true): Promise<ChatListResponse> {
  const params = new URLSearchParams({
    include_ai_chat: "true",
    include_deployments: String(includeDeployments),
    refresh: String(refresh)
  });
  return apiRequest<ChatListResponse>(`/api/chats?${params.toString()}`);
}

export function startExport(input: {
  mode: ExportMode;
  chatIds: string[];
  formats: ExportFormat[];
  zip: boolean;
}): Promise<ExportStartResponse> {
  return apiRequest<ExportStartResponse>("/api/export", {
    method: "POST",
    body: JSON.stringify({
      mode: input.mode,
      chat_ids: input.chatIds,
      types: ["ai_chat", "deployment_conversation"],
      formats: input.formats,
      zip: input.zip
    })
  });
}

export function getJob(jobId: string): Promise<BackupJob> {
  return apiRequest<BackupJob>(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export function cancelJob(jobId: string): Promise<{ cancelled: boolean }> {
  return apiRequest<{ cancelled: boolean }>(`/api/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" });
}

export function listBackups(): Promise<BackupListResponse> {
  return apiRequest<BackupListResponse>("/api/backups");
}

export function getManifest(backupId: string): Promise<unknown> {
  return apiRequest<unknown>(`/api/backups/${encodeURIComponent(backupId)}/manifest`);
}

export function deleteBackup(backupId: string): Promise<{ deleted: boolean }> {
  return apiRequest<{ deleted: boolean }>(`/api/backups/${encodeURIComponent(backupId)}?confirm=true`, {
    method: "DELETE"
  });
}
