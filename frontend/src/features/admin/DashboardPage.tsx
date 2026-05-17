import { useQuery } from '@tanstack/react-query'
import { Activity, FolderKanban, Users } from 'lucide-react'

import { adminApi } from '@/api/admin'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

function StatCard({
  title,
  value,
  icon: Icon,
}: {
  title: string
  value: number | undefined
  icon: React.ElementType
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {value === undefined ? (
          <Skeleton className="h-8 w-16" />
        ) : (
          <p className="text-3xl font-bold">{value}</p>
        )}
      </CardContent>
    </Card>
  )
}

export function DashboardPage() {
  const { data, isPending } = useQuery({
    queryKey: ['admin', 'dashboard'],
    queryFn: adminApi.getDashboard,
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard title="Total Users" value={data?.total_users} icon={Users} />
        <StatCard title="Projects" value={data?.total_projects} icon={FolderKanban} />
        <StatCard title="Active Tickets" value={data?.active_tickets} icon={Activity} />
      </div>

      {isPending ? (
        <div className="grid grid-cols-2 gap-6">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Users by Role</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th className="pb-2 text-left font-medium">Role</th>
                    <th className="pb-2 text-right font-medium">Users</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.users_by_role.map((row) => (
                    <tr key={row.role_name} className="border-b last:border-0">
                      <td className="py-2">{row.role_name}</td>
                      <td className="py-2 text-right">{row.user_count}</td>
                    </tr>
                  ))}
                  {data?.users_by_role.length === 0 && (
                    <tr>
                      <td colSpan={2} className="py-4 text-center text-muted-foreground">
                        No data yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Workload</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th className="pb-2 text-left font-medium">User</th>
                    <th className="pb-2 text-right font-medium">Assigned</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.workload_by_user.map((row) => (
                    <tr key={row.username} className="border-b last:border-0">
                      <td className="py-2">{row.username}</td>
                      <td className="py-2 text-right">{row.assigned_ticket_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
