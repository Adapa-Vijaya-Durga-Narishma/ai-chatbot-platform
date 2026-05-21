export interface DataframeSourceResponse {
  source_type: string;
  source_name: string;
  row_count: number;
  column_count: number;
  columns: string[];
  preview_rows: Record<string, unknown>[];
}

export interface GoogleSheetConnectRequest {
  sheet_url: string;
}

export interface DataframeQueryResponse {
  answer: string;
  source_type: string;
  source_name: string;
  row_count: number;
  column_count: number;
  columns: string[];
}