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
  ApiResponse 
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
  async searchPYQs(query: string, filters?: { subject?: string; year?: number; limit?: number }): Promise<PYQSearchResult[]> {
    const searchRequest = {
      query,
      limit: filters?.limit || 10,
      ...(filters?.subject && { subject: filters.subject }),
      ...(filters?.year && { year: filters.year }),
    };

    const response: AxiosResponse<PYQSearchResult[]> = await this.api.post('/pyqs/search', searchRequest);
    return response.data; // Backend returns array directly, not nested in 'data' property
  }

  async getPYQsBySubject(subject: string): Promise<PYQ[]> {
    const response: AxiosResponse<PYQ[]> = await this.api.get(`/pyqs/subject/${subject}`);
    return response.data; // Backend returns array directly
  }

  // Answer Upload & Evaluation
  async uploadAnswer(questionId: string, content: string, file?: File): Promise<UploadedAnswer> {
    const formData = new FormData();
    formData.append('question_id', questionId);  // Fixed: backend expects question_id, not questionId
    formData.append('content', content);
    if (file) {
      formData.append('file', file);
    }

    const response: AxiosResponse<{id: number, message: string, answer: UploadedAnswer}> = await this.api.post('/answers/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data.answer;  // Extract the answer from the wrapped response
  }

  async getAnswerEvaluation(answerId: string): Promise<AnswerEvaluation> {
    const response: AxiosResponse<AnswerEvaluation> = await this.api.get(`/answers/${answerId}/evaluation`);
    return response.data;
  }

  async getMyAnswers(): Promise<UploadedAnswer[]> {
    const response: AxiosResponse<UploadedAnswer[]> = await this.api.get('/answers/me');
    return response.data;
  }

  // Chat
  async sendChatMessage(message: string): Promise<ChatMessage> {
    const response: AxiosResponse<ChatMessage> = await this.api.post('/chat/', { message });
    return response.data;
  }

  async getChatHistory(limit: number = 50): Promise<ChatMessage[]> {
    const response: AxiosResponse<ChatMessage[]> = await this.api.get(`/chat/history?limit=${limit}`);
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
