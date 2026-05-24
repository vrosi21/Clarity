import { Navigate, Route, Routes } from 'react-router-dom'
import { Toaster } from 'sonner'

import { ProtectedRoute } from '@/components/common/protected-route'
import { AppShell } from '@/components/layout/app-shell'
import { LoginPage } from '@/features/auth/login-page'
import { BoardPage } from '@/features/board/board-page'
import { HomePage } from '@/features/home/home-page'
import { MembersPage } from '@/features/members/members-page'
import { ProjectDashboard } from '@/features/projects/project-dashboard'
import { ProjectsPage } from '@/features/projects/projects-page'
import { SimulationPage } from '@/features/simulation/simulation-page'
import { AdminLayout } from '@/features/admin/AdminLayout'
import { DashboardPage } from '@/features/admin/DashboardPage'
import { UsersPage } from '@/features/admin/UsersPage'
import { RolesPage } from '@/features/admin/RolesPage'
import { CategoriesPage } from '@/features/admin/CategoriesPage'
import { AccountSettingsPage } from '@/features/settings/AccountSettingsPage'
import { ProjectSettingsPage } from '@/features/settings/ProjectSettingsPage'

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<Navigate to="/login" replace />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/simulation" element={<SimulationPage />} />
            <Route path="/projects/:projectId" element={<ProjectDashboard />} />
            <Route path="/projects/:projectId/board" element={<BoardPage />} />
            <Route path="/projects/:projectId/members" element={<MembersPage />} />
            <Route path="/projects/:projectId/settings" element={<ProjectSettingsPage />} />
            <Route path="/settings" element={<AccountSettingsPage />} />
            <Route path="/admin" element={<AdminLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="users" element={<UsersPage />} />
              <Route path="roles" element={<RolesPage />} />
              <Route path="categories" element={<CategoriesPage />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster richColors closeButton />
    </>
  )
}
