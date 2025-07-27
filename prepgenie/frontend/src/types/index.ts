export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  createdAt: string;
  isActive: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface RegistrationResponse {
  message: string;
  user: User;
}

export interface StudyPlan {
  id: string;
  user_id: string;
  target_date: string;
  targets: StudyTarget[];
  created_at: string;
  updated_at: string;
}

export interface StudyTarget {
  id: string;
  subject: string;
  topic: string;
  dueDate: string;
  status: 'pending' | 'in_progress' | 'completed';
  priority: 'low' | 'medium' | 'high';
}

export interface PYQ {
  id: string;
  question: string;
  year: number;
  paper: string;
  subject: string;
  topic: string[];
  marks: number;
  difficulty: 'easy' | 'medium' | 'hard';
}

export interface PYQSearchResult {
  id: number;
  question: string;
  year: number;
  paper: string;
  subject: string;
  topics: string[];
  marks: number;
  difficulty: string;
  similarity_score: number;
}

export interface UploadedAnswer {
  id: string;
  userId: string;
  questionId: string;
  content: string;
  filePath?: string;
  fileName?: string;
  evaluation?: AnswerEvaluation;
  uploadedAt: string;
  task_id?: string;
  processing_started?: boolean;
}

export interface AnswerEvaluation {
  id: string;
  score: number;
  maxScore: number;
  feedback: string;
  strengths: string[];
  improvements: string[];
  structure: number;
  coverage: number;
  tone: number;
  evaluatedAt: string;
}

export interface ChatMessage {
  id: string;
  conversation_id?: string;
  conversation_uuid?: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  tokens_used?: number;
}

export interface ProgressData {
  totalQuestions: number;
  answersSubmitted: number;
  averageScore: number;
  weakAreas: string[];
  strongAreas: string[];
  recentActivity: ActivityLog[];
}

export interface ActivityLog {
  id: string;
  type: 'answer_submitted' | 'pyq_searched' | 'plan_updated';
  description: string;
  timestamp: string;
}

export interface SyllabusItem {
  id: string;
  subject: string;
  topic: string;
  subtopics: string[];
  paper: string;
  importance: 'low' | 'medium' | 'high';
}

export interface ApiResponse<T> {
  data: T;
  message: string;
  success: boolean;
}
