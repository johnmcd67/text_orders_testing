export type JobStatus =
  | 'pending'
  | 'running'
  | 'awaiting_review_data'
  | 'completed'
  | 'failed';

export interface Job {
  id: number;
  status: JobStatus;
  progress: number | null;
  progress_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface Order {
  orderno: number;
  customerid: number;
  customer_name: string;
  sku: string;
  quantity: number;
  reference_no: string | null;
  valve: "Yes" | "no" | "Horizontal valve" | "Vertical valve" | "Rectangular valve";
  delivery_address: string | null;
  cpsd: string | null;
  entry_id: string;
  option_sku: string | null;
  option_qty: number | null;
  telephone_number: string | null;
  contact_name: string | null;
}

export interface StartJobResponse {
  job_id: number;
  status: JobStatus;
  message: string;
}

export interface ApprovalResponse {
  status: string;
  message: string;
}

export interface DataPreviewResponse {
  job_id: number;
  data: Order[];
}

export interface JobHistoryItem {
  date: string;
  count: number;
}

export interface OrdersHistoryItem {
  date: string;
  total_orders: number;
}

export interface OrderLinesHistoryItem {
  date: string;
  total_order_lines: number;
}

export interface AvgProcessTimeItem {
  date: string;
  job_id: number;
  duration_seconds: number | null;
}

export interface FailureSummaryResponse {
  job_id: number;
  has_failures: boolean;
  failure_count: number;
  summary: string | null;
  generated_at: string | null;
  is_cached: boolean;
}

