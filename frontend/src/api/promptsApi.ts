import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface PromptResponse {
  filename: string;
  content: string;
}

export const promptsApi = {
  getPrompt: async (promptName: string): Promise<PromptResponse> => {
    const response = await axios.get<PromptResponse>(`${API_BASE_URL}/api/prompts/${promptName}`);
    return response.data;
  },
};

