import { Routes, Route } from 'react-router-dom';
import { MainLayout } from './components/layout/MainLayout';
import { DashboardPage } from './pages/DashboardPage';
import { NotesPage } from './pages/NotesPage';
import { TriagePage } from './pages/TriagePage';
import { ProjectsPage } from './pages/ProjectsPage';
import { ProjectDetailPage } from './pages/ProjectDetailPage';
import { ArchivePage } from './pages/ArchivePage';
import { RejectedPage } from './pages/RejectedPage';
import { DeferredPage } from './pages/DeferredPage';

function App() {
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/notes" element={<NotesPage />} />
        <Route path="/triage" element={<TriagePage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:key" element={<ProjectDetailPage />} />
        <Route path="/archive" element={<ArchivePage />} />
        <Route path="/rejected" element={<RejectedPage />} />
        <Route path="/deferred" element={<DeferredPage />} />
      </Routes>
    </MainLayout>
  );
}

export default App;
