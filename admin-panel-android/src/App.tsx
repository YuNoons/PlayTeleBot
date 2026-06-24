import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Menu } from 'lucide-react';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Rooms from './pages/Rooms';
import Users from './pages/Users';
import Admins from './pages/Admins';
import Store from './pages/Store';
import Reports from './pages/Reports';
import Broadcast from './pages/Broadcast';
import Settings from './pages/Settings';
import SyncManager from './components/SyncManager';
import './App.css';

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <BrowserRouter>
      <div className="app-container">
        <SyncManager />

        {/* Mobile Header */}
        <header className="mobile-header">
          <button className="burger-btn" onClick={() => setIsSidebarOpen(true)}>
            <Menu size={24} />
          </button>
          <h2 style={{ marginLeft: '1rem', fontSize: '1.25rem' }}>Admin Panel</h2>
        </header>

        <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

        <main className="main-content">
          <div className="page-container">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/rooms" element={<Rooms />} />
              <Route path="/store" element={<Store />} />
              <Route path="/users" element={<Users />} />
              <Route path="/admins" element={<Admins />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/broadcast" element={<Broadcast />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
