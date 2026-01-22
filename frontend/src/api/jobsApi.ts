import axios from 'axios';
import type {
  Job,
  StartJobResponse,
  DataPreviewResponse,
  ApprovalResponse,
  Order,
  JobHistoryItem,
  OrdersHistoryItem,
  OrderLinesHistoryItem,
  AvgProcessTimeItem,
  FailureSummaryResponse
} from '../types/job.types';
import { getToken } from '../services/authService';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Helper to get auth headers
const getAuthHeaders = () => {
  const token = getToken();
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

export const jobsApi = {
  healthCheck: async () => {
    const response = await axios.get(`${API_BASE_URL}/`);
    return response.data;
  },

  startJob: async (): Promise<StartJobResponse> => {
    const response = await axios.post(`${API_BASE_URL}/api/jobs/start`, {}, { headers: getAuthHeaders() });
    return response.data;
  },

  getJobStatus: async (jobId: number): Promise<Job> => {
    const response = await axios.get(`${API_BASE_URL}/api/jobs/${jobId}/status`, { headers: getAuthHeaders() });
    return response.data;
  },

  getDataPreview: async (jobId: number): Promise<DataPreviewResponse> => {
    const response = await axios.get(`${API_BASE_URL}/api/jobs/${jobId}/preview`, { headers: getAuthHeaders() });
    return response.data;
  },

  approveData: async (jobId: number, approved: boolean, orders?: Order[]): Promise<ApprovalResponse> => {
    const body: any = { approved };
    if (orders) {
      body.orders = orders;
    }
    const response = await axios.post(`${API_BASE_URL}/api/jobs/${jobId}/approve`, body, { headers: getAuthHeaders() });
    return response.data;
  },

  downloadResults: async (jobId: number, fileType: 'order_details' | 'failed_orders') => {
    const response = await axios.get(
      `${API_BASE_URL}/api/jobs/${jobId}/results?file_type=${fileType}`,
      { responseType: 'blob', headers: getAuthHeaders() }
    );

    const url = window.URL.createObjectURL(response.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = `job_${jobId}_${fileType}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },

  getJobHistory: async (): Promise<JobHistoryItem[]> => {
    const response = await axios.get(`${API_BASE_URL}/api/jobs/history`, { headers: getAuthHeaders() });
    return response.data;
  },

  getOrdersHistory: async (): Promise<OrdersHistoryItem[]> => {
    const response = await axios.get(`${API_BASE_URL}/api/jobs/history/orders`, { headers: getAuthHeaders() });
    return response.data;
  },

  getOrderLinesHistory: async (): Promise<OrderLinesHistoryItem[]> => {
    const response = await axios.get(`${API_BASE_URL}/api/jobs/history/order-lines`, { headers: getAuthHeaders() });
    return response.data;
  },

  getAvgProcessTime: async (): Promise<AvgProcessTimeItem[]> => {
    const response = await axios.get(`${API_BASE_URL}/api/jobs/history/avg-process-time`, { headers: getAuthHeaders() });
    return response.data;
  },

  getFailureSummary: async (jobId: number, regenerate: boolean = false): Promise<FailureSummaryResponse> => {
    const response = await axios.get(
      `${API_BASE_URL}/api/jobs/${jobId}/failure-summary?regenerate=${regenerate}`,
      { headers: getAuthHeaders() }
    );
    return response.data;
  },

  downloadFailureSummaryPdf: async (jobId: number) => {
    const response = await axios.get(
      `${API_BASE_URL}/api/jobs/${jobId}/failure-summary/pdf`,
      { responseType: 'blob', headers: getAuthHeaders() }
    );

    const url = window.URL.createObjectURL(response.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = `job_${jobId}_failure_summary.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }
};

