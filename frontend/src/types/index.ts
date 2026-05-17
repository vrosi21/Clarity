// Backend-mirrored type definitions. Keep aligned with backend/app/schemas.

export type StageType = 'start' | 'normal' | 'final'
export type Priority = 'p1' | 'p2' | 'p3' | 'p4' | 'p5'
export type RoleScope = 'org' | 'project' | 'both'

export interface Role {
  id: number
  name: string
  description: string | null
  scope: RoleScope
  is_builtin: boolean
  permissions: string[]
}

export interface OrgRoleInfo {
  role_id: number
  role_name: string
  permissions: string[]
}

export interface User {
  id: number
  email: string
  username: string
  full_name: string | null
  years_experience: number
  is_active: boolean
  org_role: OrgRoleInfo | null
}

export interface AuthToken {
  access_token: string
  token_type: string
}

export interface Project {
  id: number
  name: string
  description: string | null
  created_at: string
}

export interface Member {
  user_id: number
  username: string
  email: string
  role_id: number
  role_name: string
  role_permissions: string[]
}

export interface Stage {
  id: number
  project_id: number
  name: string
  order: number
  type: StageType | null
  color: string | null
}

export interface Ticket {
  id: number
  project_id: number
  stage_id: number
  title: string
  description: string | null
  priority: Priority
  complexity: number
  estimated_minutes: number | null
  assignee_id: number | null
  assignee_username: string | null
  category_id: number | null
  category_name: string | null
  created_at: string
  updated_at: string
}

export interface Comment {
  id: number
  content: string
  user_id: number
  username: string | null
  parent_id: number | null
  created_at: string
}

export interface Category {
  id: number
  name: string
  description: string | null
}

export interface UserDetail {
  id: number
  email: string
  username: string
  full_name: string | null
  years_experience: number
  is_active: boolean
  org_role_id: number | null
  org_role_name: string | null
  skills: SkillProfile[]
}

export interface SkillProfile {
  category_id: number
  proficiency: number
}

export interface RoleConstraint {
  id: number
  role_id: number
  role_name: string
  allowed_transitions: [number, number][] | null
  editable_fields: string[] | null
  assignee_only: boolean
  view_scope: 'all' | 'assigned'
}

export interface CategoryConfig {
  id: number
  category_id: number
  category_name: string
  min_proficiency: number
  allowed_role_ids: number[] | null
}

export interface ProjectSettings {
  role_constraints: RoleConstraint[]
  category_configs: CategoryConfig[]
}

export interface DashboardStats {
  total_users: number
  total_projects: number
  active_tickets: number
  users_by_role: { role_name: string; user_count: number }[]
  workload_by_user: { username: string; assigned_ticket_count: number }[]
}

// Helpers exported for convenience.
export const PRIORITIES: Priority[] = ['p1', 'p2', 'p3', 'p4', 'p5']
export const PRIORITY_LABEL: Record<Priority, string> = {
  p1: 'P1 — Critical',
  p2: 'P2 — High',
  p3: 'P3 — Medium',
  p4: 'P4 — Low',
  p5: 'P5 — Trivial',
}
