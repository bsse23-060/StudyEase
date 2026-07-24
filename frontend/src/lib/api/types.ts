export type Role = "student" | "instructor" | "admin";
export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  level_preference: string;
  weekly_hours: number;
  goal: string;
  language_preference: string;
}
export interface Question {
  id: number;
  lesson: number;
  concept: number | null;
  kind: "multiple_choice" | "true_false" | "short_answer";
  prompt: string;
  options: unknown;
  explanation: string;
  difficulty: number;
  points: number;
  quiz: number | null;
  position: number;
  is_required: boolean;
}
export interface Quiz {
  id: number;
  lesson: number;
  title: string;
  instructions: string;
  pass_mark: number | null;
  maximum_attempts: number | null;
  available_from: string | null;
  available_until: string | null;
  time_limit_minutes: number | null;
  is_published: boolean;
  questions: Question[];
  attempt_count: number;
  created_at: string;
  updated_at: string;
}
export interface QuizSubmissionAnswer {
  id: number;
  question: number;
  prompt: string;
  answer: unknown;
  is_correct: boolean;
  points_earned: number;
  feedback: string;
}
export interface QuizSubmission {
  id: number;
  learner: number;
  quiz: number;
  status: "started" | "submitted";
  started_at: string;
  submitted_at: string | null;
  total_score: number;
  maximum_score: number;
  percentage_score: number | null;
  passed: boolean | null;
  answers: QuizSubmissionAnswer[];
}
export interface Lesson {
  id: number;
  module: number;
  title: string;
  kind: string;
  content: string;
  resource_url: string;
  estimated_minutes: number;
  position: number;
  questions: Question[];
}
export interface Module {
  id: number;
  course: number;
  title: string;
  summary: string;
  position: number;
  lessons: Lesson[];
}
export interface Course {
  id: number;
  instructor: number | null;
  instructor_name?: string;
  slug: string;
  title: string;
  description: string;
  is_published: boolean;
  is_archived: boolean;
  archived_at: string | null;
  archived_by: number | null;
  metadata: Record<string, unknown>;
  modules: Module[];
  created_at: string;
  updated_at: string;
}
export interface Enrollment {
  id: number;
  learner: number;
  course: number;
  status: "active" | "paused" | "completed";
  enrolled_at: string;
  completed_at: string | null;
}
export interface Mastery {
  id: number;
  learner: number;
  concept: number;
  probability: number;
  stability_days: number;
  last_seen_at: string | null;
  updated_at: string;
}
export interface Attempt {
  id: number;
  learner: number;
  question: number;
  answer: unknown;
  is_correct: boolean;
  points_earned: number;
  seconds_spent: number;
  feedback: string;
  created_at: string;
}
export interface RoadmapStep {
  id: number;
  enrollment: number;
  module: number;
  position: number;
  target_date: string | null;
  rationale: string;
  completed_at: string | null;
}
export interface Citation {
  id?: number;
  chunk_id?: number;
  document_id?: number;
  document_title?: string;
  source_filename?: string;
  course_id?: number;
  lesson_id?: number;
  page?: number | null;
  section_title?: string;
  chunk_position?: number;
  quote?: string;
  score?: number | null;
}
export interface Message {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  citations: Citation[];
  created_at: string;
}
export interface Conversation {
  id: number;
  owner: number;
  title: string;
  course: number | null;
  lesson: number | null;
  messages: Message[];
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}
export interface DocumentRecord {
  id: number;
  owner: number;
  course: number | null;
  lesson: number | null;
  title: string;
  source_url: string;
  status: "uploaded" | "queued" | "processing" | "ready" | "failed";
  visibility: "private" | "course";
  processing_error: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  chunk_count: number;
  topics: unknown[];
  created_at: string;
  updated_at: string;
}
export interface Chunk {
  id: number;
  document: number;
  text: string;
  position: number;
  page: number | null;
  section_title: string;
  character_count: number;
}
export interface Flashcard {
  id: number;
  deck: number;
  question: string;
  answer: string;
  easiness: number;
  interval_days: number;
  repetitions: number;
  next_review_at: string | null;
  total_reviews: number;
  correct_reviews: number;
  course: number | null;
  lesson: number | null;
  concept: number | null;
  created_at: string;
  updated_at: string;
}
export interface Deck {
  id: number;
  owner: number;
  name: string;
  description: string;
  topics: unknown[];
  cards: Flashcard[];
  created_at: string;
}
export interface Routine {
  id: number;
  owner: number;
  name: string;
  preferences: Record<string, unknown>;
  is_active: boolean;
  suggestions: unknown[];
  blocks: ScheduleBlock[];
  created_at: string;
  updated_at: string;
}
export interface ScheduleBlock {
  id: number;
  routine: number;
  activity_name: string;
  start_time: string;
  end_time: string;
  category: string;
  is_flexible: boolean;
  notes: string;
  recurrence: "once" | "weekly";
  weekday: number | null;
  calendar_date: string | null;
  timezone: string;
  recurrence_start: string | null;
  recurrence_end: string | null;
  course: number | null;
  is_active: boolean;
  warnings: Array<{
    code: "schedule_overlap";
    conflicting_block_id: number;
    message: string;
  }>;
}
