export interface ResearchDigestRequest {
  topic: string;
  thread_id?: string;
}

export interface ResearchPaper {
  arxiv_id: string;
  title: string;
  authors: string[];
  abstract: string;
  published: string;
  arxiv_url: string;
}

export interface ResearchDigestSection {
  title: string;
  content: string;
}

export type ResearchEventType =
  | "thread"
  | "status"
  | "paper"
  | "reasoning"
  | "digest_section"
  | "done"
  | "complete"
  | "error";

export interface ResearchStreamEventBase {
  type: ResearchEventType;
}

export interface ResearchThreadEvent extends ResearchStreamEventBase {
  type: "thread";
  thread_id: string;
}

export interface ResearchStatusEvent extends ResearchStreamEventBase {
  type: "status";
  stage: "searching" | "evaluating" | "generating";
  message: string;
  iteration?: number;
  query?: string;
  unique_papers?: number;
}

export interface ResearchPaperEvent extends ResearchStreamEventBase {
  type: "paper";
  paper: ResearchPaper;
  iteration?: number;
}

export interface ResearchReasoningEvent extends ResearchStreamEventBase {
  type: "reasoning";
  iteration: number;
  message: string;
  coverage_score: number;
  is_sufficient: boolean;
  next_focus?: string;
  stop_reasons?: string[];
}

export interface ResearchDigestSectionEvent extends ResearchStreamEventBase {
  type: "digest_section";
  section: ResearchDigestSection;
}

export interface ResearchDoneEvent extends ResearchStreamEventBase {
  type: "done";
  digest: string;
  iterations_used: number;
  paper_count: number;
}

export interface ResearchCompleteEvent extends ResearchStreamEventBase {
  type: "complete";
  thread_id: string;
}

export interface ResearchErrorEvent extends ResearchStreamEventBase {
  type: "error";
  error: string;
  message: string;
  iteration?: number;
}

export type ResearchStreamEvent =
  | ResearchThreadEvent
  | ResearchStatusEvent
  | ResearchPaperEvent
  | ResearchReasoningEvent
  | ResearchDigestSectionEvent
  | ResearchDoneEvent
  | ResearchCompleteEvent
  | ResearchErrorEvent;
