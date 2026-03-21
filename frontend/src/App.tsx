import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Layout/Sidebar';
import Header from './components/Layout/Header';
import DashboardPage from './pages/DashboardPage';
import AlertQueuePage from './pages/AlertQueuePage';
import CaseDetailPage from './pages/CaseDetailPage';
import SARPage from './pages/SARPage';
import HITLPage from './pages/HITLPage';
import AnalyticsPage from './pages/AnalyticsPage';
import SyntheticDataPage from './pages/SyntheticDataPage';

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-slate-900 overflow-hidden">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Header />
          <main className="flex-1 overflow-y-auto p-6">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/alerts" element={<AlertQueuePage />} />
              <Route path="/cases/:caseId" element={<CaseDetailPage />} />
              <Route path="/sar" element={<SARPage />} />
              <Route path="/hitl" element={<HITLPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/synthetic" element={<SyntheticDataPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}
