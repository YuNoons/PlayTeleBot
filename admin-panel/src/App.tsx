import { BrowserRouter, Routes, Route } from 'react-router-dom';
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
  return (
    <BrowserRouter>
      <SyncManager />
      <div className="app-container">
        <Sidebar />
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
