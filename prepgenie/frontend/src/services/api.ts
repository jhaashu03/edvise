import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { 
  User, 
  LoginRequest, 
  RegisterRequest, 
  AuthResponse, 
  RegistrationResponse,
  StudyPlan, 
  PYQ, 
  PYQSearchResult,
  UploadedAnswer, 
  AnswerEvaluation,
  ChatMessage,
  ProgressData,
  SyllabusItem,
  ApiResponse,
  ModelAnswerResponse
} from '../types';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8001/api/v1',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        // Only redirect to login if it's not a login or register attempt itself
        if (error.response?.status === 401 && 
            !error.config?.url?.includes('/auth/login') && 
            !error.config?.url?.includes('/auth/register')) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Authentication
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    // Convert to form data for OAuth2 compatibility
    const formData = new FormData();
    formData.append('username', credentials.email); // OAuth2 uses 'username' field
    formData.append('password', credentials.password);
    
    const response: AxiosResponse<AuthResponse> = await this.api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  }

  async register(userData: RegisterRequest): Promise<RegistrationResponse> {
    const response: AxiosResponse<RegistrationResponse> = await this.api.post('/auth/register', userData);
    return response.data;
  }

  async getCurrentUser(): Promise<User> {
    const response: AxiosResponse<User> = await this.api.get('/auth/me');
    return response.data;
  }

  // Study Plans
  async getStudyPlan(): Promise<StudyPlan> {
    const response: AxiosResponse<StudyPlan> = await this.api.get('/study-plans/me');
    return response.data;
  }

  async createStudyPlan(targetDate: string): Promise<StudyPlan> {
    const response: AxiosResponse<StudyPlan> = await this.api.post('/study-plans', { targetDate });
    return response.data;
  }

  async updateStudyTarget(targetId: string, status: string): Promise<void> {
    await this.api.patch(`/study-plans/targets/${targetId}`, { status });
  }

  // PYQ Search
  async searchPYQs(query: string, filters?: { subject?: string; year?: number; limit?: number; page?: number }): Promise<PYQSearchResult[]> {
    const searchRequest = {
      query,
      limit: filters?.limit || 10,
      page: filters?.page || 1,
      timestamp: Date.now(), // Cache busting
      ...(filters?.subject && { subject: filters.subject }),
      ...(filters?.year && { year: filters.year }),
    };

    console.log('📡 API: Sending search request:', searchRequest);
    const response: AxiosResponse<PYQSearchResult[]> = await this.api.post('/pyqs/search', searchRequest);
    return response.data; // Backend returns array directly, not nested in 'data' property
  }

  async getPYQsBySubject(subject: string): Promise<PYQ[]> {
    const response: AxiosResponse<PYQ[]> = await this.api.get(`/pyqs/subject/${subject}`);
    return response.data; // Backend returns array directly
  }

  // Answer Upload & Evaluation
  async uploadAnswer(questionId: string, content: string, file?: File): Promise<UploadedAnswer & {task_id?: string}> {
    const formData = new FormData();
    formData.append('question_id', questionId);  // Fixed: backend expects question_id, not questionId
    formData.append('content', content);
    if (file) {
      formData.append('file', file);
    }

    const response: AxiosResponse<{id: number, message: string, answer: UploadedAnswer, task_id?: string}> = await this.api.post('/answers/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    // Return answer with task_id included for progress tracking
    return {
      ...response.data.answer,
      task_id: response.data.task_id
    };
  }

  async getAnswerEvaluation(answerId: string): Promise<AnswerEvaluation> {
    const response: AxiosResponse<AnswerEvaluation> = await this.api.get(`/answers/${answerId}/evaluation`);
    return response.data;
  }

  async getMyAnswers(): Promise<UploadedAnswer[]> {
    const response: AxiosResponse<UploadedAnswer[]> = await this.api.get('/answers/me');
    return response.data;
  }

  async startDimensionalEvaluation(answerId: string): Promise<{task_id?: string, message: string}> {
    const response: AxiosResponse<{task_id?: string, message: string}> = await this.api.post(`/answers/${answerId}/evaluate/dimensional`);
    return response.data;
  }

  async startTopperComparisonEvaluation(answerId: string): Promise<{task_id?: string, message: string}> {
    const response: AxiosResponse<{task_id?: string, message: string}> = await this.api.post(`/answers/${answerId}/evaluate/topper-comparison`);
    return response.data;
  }

  async getEvaluationOptions(): Promise<{
    dimensional: {
      name: string;
      description: string;
      features: string[];
      estimated_time: string;
    };
    topper_comparison: {
      name: string;
      description: string;
      features: string[];
      estimated_time: string;
    };
  }> {
    const response = await this.api.get('/answers/evaluation-options');
    return response.data;
  }

  // Model Answer Generation
  async generateModelAnswer(answerId: string, questionIndex: number = 0): Promise<ModelAnswerResponse> {
    const response: AxiosResponse<ModelAnswerResponse> = await this.api.post(
      `/answers/${answerId}/generate-model-answer?question_index=${questionIndex}`
    );
    return response.data;
  }

  async getModelAnswer(answerId: string): Promise<ModelAnswerResponse> {
    const response: AxiosResponse<ModelAnswerResponse> = await this.api.get(
      `/answers/${answerId}/model-answer`
    );
    return response.data;
  }

  // Chat
  async sendChatMessage(message: string, conversationId?: string): Promise<ChatMessage> {
    const payload: any = { message };
    if (conversationId) {
      payload.conversation_id = conversationId;
    }
    const response: AxiosResponse<ChatMessage> = await this.api.post('/chat/', payload);
    return response.data;
  }

  async getChatHistory(limit: number = 50): Promise<ChatMessage[]> {
    const response: AxiosResponse<ChatMessage[]> = await this.api.get(`/chat/history?limit=${limit}`);
    return response.data;
  }

  async getConversationMessages(conversationId: string, limit: number = 50): Promise<ChatMessage[]> {
    // Filter chat history by conversation_uuid for now
    // In a full implementation, there would be a dedicated endpoint
    const allHistory = await this.getChatHistory(200); // Get more messages to filter
    return allHistory.filter(msg => msg.conversation_uuid === conversationId).slice(0, limit);
  }

  // Conversation Management
  async getConversations(params: {
    page?: number;
    per_page?: number;
    status?: string;
    topic?: string;
    sort_by?: string;
    sort_order?: string;
  } = {}): Promise<{
    conversations: any[];
    total: number;
    page: number;
    per_page: number;
    has_next: boolean;
  }> {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        queryParams.append(key, value.toString());
      }
    });
    
    const response = await this.api.get(`/conversation-management/conversations?${queryParams}`);
    return response.data;
  }

  async searchConversations(params: {
    query: string;
    status?: string;
    topic?: string;
    date_from?: string;
    date_to?: string;
  }): Promise<{
    conversations: any[];
    total: number;
    page: number;
    per_page: number;
    has_next: boolean;
  }> {
    const response = await this.api.post('/conversation-management/conversations/search', params);
    return response.data;
  }

  async getConversationStats(): Promise<{
    active_conversations: number;
    archived_conversations: number;
    total_messages: number;
    conversations_this_week: number;
    most_active_topics: Array<{topic: string, count: number}>;
  }> {
    const response = await this.api.get('/conversation-management/conversations/stats');
    return response.data;
  }

  async updateConversation(conversationUuid: string, updates: {
    title?: string;
    tags?: string;
    is_pinned?: boolean;
    status?: string;
  }): Promise<any> {
    const response = await this.api.put(`/conversation-management/conversations/${conversationUuid}`, updates);
    return response.data;
  }

  async deleteConversation(conversationUuid: string): Promise<any> {
    const response = await this.api.delete(`/conversation-management/conversations/${conversationUuid}`);
    return response.data;
  }

  async archiveConversation(conversationUuid: string): Promise<any> {
    const response = await this.api.post(`/conversation-management/conversations/${conversationUuid}/archive`);
    return response.data;
  }

  async exportConversation(conversationUuid: string, format: 'json' | 'txt' | 'md' = 'json'): Promise<any> {
    const response = await this.api.post(`/conversation-management/conversations/${conversationUuid}/export?format=${format}`);
    return response.data;
  }

  // Progress & Analytics
  async getProgress(): Promise<ProgressData> {
    const response: AxiosResponse<ProgressData> = await this.api.get('/progress/me');
    return response.data;
  }

  // Syllabus
  async getSyllabus(): Promise<SyllabusItem[]> {
    const response: AxiosResponse<SyllabusItem[]> = await this.api.get('/syllabus');
    return response.data;
  }

  async getSyllabusBySubject(subject: string): Promise<SyllabusItem[]> {
    const response: AxiosResponse<SyllabusItem[]> = await this.api.get(`/syllabus/${subject}`);
    return response.data;
  }
}

export const apiService = new ApiService();
export default apiService;
