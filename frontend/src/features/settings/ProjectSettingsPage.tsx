import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { categoriesApi } from '@/api/categories'
import { membersApi } from '@/api/members'
import { projectSettingsApi } from '@/api/project-settings'
import { projectsApi } from '@/api/projects'
import { rolesApi } from '@/api/roles'
import { stagesApi } from '@/api/stages'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { usePermissions } from '@/hooks/use-permissions'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/auth-store'
import type { RoleConstraint } from '@/types'

type Tab = 'constraints' | 'categories' | 'general'
const TABS: { id: Tab; label: string }[] = [
  { id: 'constraints', label: 'Role Constraints' },
  { id: 'categories', label: 'Category Eligibility' },
  { id: 'general', label: 'General' },
]

const EDITABLE_FIELDS = [
  'title', 'description', 'priority', 'complexity',
  'estimated_minutes', 'spent_minutes', 'due_date', 'category', 'assignee',
]

// ── ConstraintCard ────────────────────────────────────────────────────────────

function ConstraintCard({
  constraint,
  stages,
  projectId,
}: {
  constraint: RoleConstraint
  stages: { id: number; name: string }[]
  projectId: number
}) {
  const qc = useQueryClient()
  const [local, setLocal] = useState<RoleConstraint>(constraint)

  useEffect(() => { setLocal(constraint) }, [constraint])

  const persist = useCallback(
    (updated: RoleConstraint) => {
      setLocal(updated)
      projectSettingsApi
        .upsertConstraint(projectId, {
          role_id: updated.role_id,
          allowed_transitions: updated.allowed_transitions,
          editable_fields: updated.editable_fields,
          assignee_only: updated.assignee_only,
          view_scope: updated.view_scope,
        })
        .then(() => qc.invalidateQueries({ queryKey: ['project-settings', projectId] }))
        .catch(() => toast.error('Failed to save constraint'))
    },
    [projectId, qc],
  )

  const hasTransition = (from: number, to: number): boolean => {
    if (local.allowed_transitions === null) return true
    return local.allowed_transitions.some(([f, t]) => f === from && t === to)
  }

  const toggleTransition = (from: number, to: number) => {
    const current: [number, number][] =
      local.allowed_transitions ??
      stages.flatMap((f) =>
        stages.filter((t) => t.id !== f.id).map((t) => [f.id, t.id] as [number, number]),
      )
    const exists = current.some(([f, t]) => f === from && t === to)
    const next = exists
      ? current.filter(([f, t]) => !(f === from && t === to))
      : ([...current, [from, to]] as [number, number][])
    persist({ ...local, allowed_transitions: next })
  }

  const toggleField = (field: string) => {
    const current = local.editable_fields ?? EDITABLE_FIELDS
    const next = current.includes(field)
      ? current.filter((f) => f !== field)
      : [...current, field]
    persist({ ...local, editable_fields: next.length === EDITABLE_FIELDS.length ? null : next })
  }

  return (
    <Card>
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h3 className="font-medium text-sm">{constraint.role_name}</h3>
          <div className="flex items-center gap-4 text-sm">
            <label className="flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={local.assignee_only}
                onChange={(e) => persist({ ...local, assignee_only: e.target.checked })}
              />
              Assignee only
            </label>
            <label className="flex items-center gap-1.5">
              <span className="text-muted-foreground text-xs">View:</span>
              <select
                className="text-xs border rounded px-1 py-0.5 bg-background"
                value={local.view_scope}
                onChange={(e) =>
                  persist({ ...local, view_scope: e.target.value as 'all' | 'assigned' })
                }
              >
                <option value="all">All tickets</option>
                <option value="assigned">Assigned only</option>
              </select>
            </label>
          </div>
        </div>

        {stages.length > 1 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">
              Stage transitions
              {local.allowed_transitions === null && (
                <span className="ml-2 text-green-600 dark:text-green-400">No restrictions</span>
              )}
            </p>
            <div className="overflow-x-auto">
              <table className="text-xs">
                <thead>
                  <tr>
                    <th className="px-2 py-1 text-left text-muted-foreground font-normal">
                      From ↓ / To →
                    </th>
                    {stages.map((s) => (
                      <th key={s.id} className="px-2 py-1 text-muted-foreground font-normal">
                        {s.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {stages.map((from) => (
                    <tr key={from.id}>
                      <td className="px-2 py-1 font-medium">{from.name}</td>
                      {stages.map((to) => (
                        <td key={to.id} className="px-2 py-1 text-center">
                          {from.id === to.id ? (
                            <span className="text-muted-foreground">—</span>
                          ) : (
                            <input
                              type="checkbox"
                              checked={hasTransition(from.id, to.id)}
                              onChange={() => toggleTransition(from.id, to.id)}
                            />
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2">
            Editable fields
            {local.editable_fields === null && (
              <span className="ml-2 text-green-600 dark:text-green-400">All fields</span>
            )}
          </p>
          <div className="flex flex-wrap gap-3">
            {EDITABLE_FIELDS.map((f) => (
              <label key={f} className="flex items-center gap-1.5 text-xs">
                <input
                  type="checkbox"
                  checked={local.editable_fields === null || local.editable_fields.includes(f)}
                  onChange={() => toggleField(f)}
                />
                {f}
              </label>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ── ProjectSettingsPage ───────────────────────────────────────────────────────

export function ProjectSettingsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const id = Number(projectId)
  const qc = useQueryClient()
  const navigate = useNavigate()
  const currentUser = useAuthStore((s) => s.user)
  const [activeTab, setActiveTab] = useState<Tab>('constraints')
  const [projName, setProjName] = useState('')
  const [projDesc, setProjDesc] = useState('')

  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectsApi.get(id),
    enabled: !Number.isNaN(id),
  })

  const { data: members } = useQuery({
    queryKey: ['members', id],
    queryFn: () => membersApi.list(id),
    enabled: !Number.isNaN(id),
  })

  const myMember = members?.find((m) => m.user_id === currentUser?.id)
  const { can } = usePermissions(myMember)

  const { data: settings, isPending: settingsPending } = useQuery({
    queryKey: ['project-settings', id],
    queryFn: () => projectSettingsApi.get(id),
    enabled: !Number.isNaN(id),
  })

  const { data: stages } = useQuery({
    queryKey: ['stages', id],
    queryFn: () => stagesApi.list(id),
    enabled: !Number.isNaN(id),
  })

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: categoriesApi.list,
  })

  const { data: projectRoles } = useQuery({
    queryKey: ['roles', 'project'],
    queryFn: () => rolesApi.list('project'),
  })
  const { data: bothRoles } = useQuery({
    queryKey: ['roles', 'both'],
    queryFn: () => rolesApi.list('both'),
  })
  const assignableRoles = [...(projectRoles ?? []), ...(bothRoles ?? [])]

  useEffect(() => {
    if (project) {
      setProjName(project.name)
      setProjDesc(project.description ?? '')
    }
  }, [project])

  const updateProjectMutation = useMutation({
    mutationFn: () => projectsApi.update(id, { name: projName, description: projDesc || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['project', id] })
      qc.invalidateQueries({ queryKey: ['projects'] })
      toast.success('Project updated')
    },
    onError: () => toast.error('Failed to update project'),
  })

  const deleteProjectMutation = useMutation({
    mutationFn: () => projectsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects'] })
      navigate('/projects')
      toast.success('Project deleted')
    },
    onError: () => toast.error('Failed to delete project'),
  })

  if (!can('projects:manage_settings')) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        403 — Project settings access required.
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl px-6 py-8">
        <h1 className="text-2xl font-semibold mb-6">
          {project?.name ?? <Skeleton className="inline-block h-6 w-40" />} — Settings
        </h1>

        {/* Tab bar */}
        <div className="flex gap-1 border-b mb-6">
          {TABS.map(({ id: tabId, label }) => (
            <button
              key={tabId}
              onClick={() => setActiveTab(tabId)}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                activeTab === tabId
                  ? 'border-foreground text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Tab 1 — Role Constraints */}
        {activeTab === 'constraints' && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Configure what each project role can see and do. Changes save immediately.
            </p>
            {settingsPending && <Skeleton className="h-32 w-full" />}
            {settings?.role_constraints.length === 0 && !settingsPending && (
              <p className="text-sm text-muted-foreground">No role constraints configured.</p>
            )}
            {settings?.role_constraints.map((rc) => (
              <ConstraintCard
                key={rc.role_id}
                constraint={rc}
                stages={stages ?? []}
                projectId={id}
              />
            ))}
            {/* Roles with no constraint yet */}
            {assignableRoles
              .filter((r) => !settings?.role_constraints.some((rc) => rc.role_id === r.id))
              .map((r) => (
                <Card key={r.id} className="border-dashed">
                  <CardContent className="p-4 flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      {r.name} — no restrictions
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        projectSettingsApi
                          .upsertConstraint(id, {
                            role_id: r.id,
                            allowed_transitions: null,
                            editable_fields: null,
                            assignee_only: false,
                            view_scope: 'all',
                          })
                          .then(() => qc.invalidateQueries({ queryKey: ['project-settings', id] }))
                          .catch(() => toast.error('Failed'))
                      }
                    >
                      Add constraint
                    </Button>
                  </CardContent>
                </Card>
              ))}
          </div>
        )}

        {/* Tab 2 — Category Eligibility */}
        {activeTab === 'categories' && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Set minimum proficiency and restrict which roles can be assigned tickets in each category.
            </p>
            {categories?.map((cat) => {
              const config = settings?.category_configs.find((c) => c.category_id === cat.id)
              const minProf = config?.min_proficiency ?? 0
              const allowedRoleIds = config?.allowed_role_ids ?? null

              return (
                <Card key={cat.id}>
                  <CardContent className="p-4 space-y-3">
                    <h3 className="font-medium text-sm capitalize">{cat.name}</h3>
                    <div className="flex items-center gap-3">
                      <Label className="text-xs w-44 shrink-0">
                        Min proficiency: <strong>{minProf.toFixed(2)}</strong>
                      </Label>
                      <input
                        type="range"
                        min={0}
                        max={1}
                        step={0.05}
                        defaultValue={minProf}
                        className="flex-1"
                        onMouseUp={(e) => {
                          const val = Number((e.target as HTMLInputElement).value)
                          projectSettingsApi
                            .upsertCategoryConfig(id, {
                              category_id: cat.id,
                              min_proficiency: val,
                              allowed_role_ids: allowedRoleIds,
                            })
                            .then(() =>
                              qc.invalidateQueries({ queryKey: ['project-settings', id] }),
                            )
                            .catch(() => toast.error('Failed to save'))
                        }}
                      />
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">
                        Allowed roles (all checked = no restriction):
                      </p>
                      <div className="flex flex-wrap gap-3">
                        {assignableRoles.map((r) => {
                          const checked =
                            allowedRoleIds === null || allowedRoleIds.includes(r.id)
                          return (
                            <label key={r.id} className="flex items-center gap-1.5 text-xs">
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={(e) => {
                                  const current =
                                    allowedRoleIds ?? assignableRoles.map((ar) => ar.id)
                                  const next = e.target.checked
                                    ? [...current, r.id]
                                    : current.filter((rid) => rid !== r.id)
                                  const final =
                                    next.length === assignableRoles.length ? null : next
                                  projectSettingsApi
                                    .upsertCategoryConfig(id, {
                                      category_id: cat.id,
                                      min_proficiency: minProf,
                                      allowed_role_ids: final,
                                    })
                                    .then(() =>
                                      qc.invalidateQueries({
                                        queryKey: ['project-settings', id],
                                      }),
                                    )
                                    .catch(() => toast.error('Failed to save'))
                                }}
                              />
                              {r.name}
                            </label>
                          )
                        })}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}

        {/* Tab 3 — General */}
        {activeTab === 'general' && (
          <div className="space-y-6">
            <Card>
              <CardContent className="p-4 space-y-4">
                <h3 className="font-medium">Project details</h3>
                <div>
                  <Label>Name</Label>
                  <Input value={projName} onChange={(e) => setProjName(e.target.value)} />
                </div>
                <div>
                  <Label>Description</Label>
                  <Input
                    value={projDesc}
                    onChange={(e) => setProjDesc(e.target.value)}
                    placeholder="Optional"
                  />
                </div>
                <Button
                  disabled={updateProjectMutation.isPending}
                  onClick={() => updateProjectMutation.mutate()}
                >
                  Save
                </Button>
              </CardContent>
            </Card>

            {can('projects:delete') && (
              <Card className="border-destructive/40">
                <CardContent className="p-4 space-y-3">
                  <h3 className="font-medium text-destructive">Danger zone</h3>
                  <p className="text-sm text-muted-foreground">
                    Permanently delete this project and all its stages and tickets.
                  </p>
                  <Button
                    variant="destructive"
                    disabled={deleteProjectMutation.isPending}
                    onClick={() => {
                      if (confirm(`Delete project "${project?.name}"? This cannot be undone.`)) {
                        deleteProjectMutation.mutate()
                      }
                    }}
                  >
                    Delete project
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
