export interface SqlQueryRequest {
  question: string;
}

export interface SqlQueryResponse {
  sql: string;
  rows: Record<string, unknown>[];
  answer: string;
  explanation?: string;
  summary?: string;
  thread_id?: string;
}
