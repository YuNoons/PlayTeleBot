import { useEffect, useState } from 'react';
import { ShieldAlert, Trash2, UserPlus, Clock } from 'lucide-react';

interface Admin {
  user_id: number;
  username: string;
  level: number;
  added_by: number;
  added_at: string;
}

interface AdminLog {
  id: number;
  admin_id: number;
  admin_name: string;
  action: string;
  target_user: string;
  target_chat: number;
  details: string;
  timestamp: string;
}

export default function Admins() {
  const [admins, setAdmins] = useState<Admin[]>([]);
  const [logs, setLogs] = useState<AdminLog[]>([]);
  const [sortCol, setSortCol] = useState<keyof Admin | null>(null);
  const [sortDesc, setSortDesc] = useState(true);
  
  const [newAdminId, setNewAdminId] = useState('');
  const [newAdminName, setNewAdminName] = useState('');
  const [newAdminLevel, setNewAdminLevel] = useState('1');

  const fetchData = async () => {
    try {
      const [adminsRes, logsRes] = await Promise.all([
        fetch('http://127.0.0.1:8000/api/admins').then(r => r.json()),
        fetch('http://127.0.0.1:8000/api/admin_logs').then(r => r.json()).catch(() => [])
      ]);
      setAdmins(adminsRes);
      setLogs(logsRes);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAddAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAdminId || !newAdminName) return;
    
    try {
      await fetch('http://127.0.0.1:8000/api/admins', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          user_id: parseInt(newAdminId), 
          username: newAdminName, 
          level: parseInt(newAdminLevel) 
        })
      });
      setNewAdminId('');
      setNewAdminName('');
      setNewAdminLevel('1');
      fetchData();
    } catch (err) {
      alert('Failed to add admin: ' + err);
    }
  };

  const handleRemoveAdmin = async (userId: number) => {
    if (!window.confirm('Remove this admin?')) return;
    try {
      await fetch(`http://127.0.0.1:8000/api/admins/${userId}`, { method: 'DELETE' });
      fetchData();
    } catch (err) {
      alert('Failed to remove admin: ' + err);
    }
  };

  const handleSort = (col: keyof Admin) => {
    if (sortCol === col) {
      setSortDesc(!sortDesc);
    } else {
      setSortCol(col);
      setSortDesc(true);
    }
  };

  const sortedAdmins = [...admins].sort((a, b) => {
    if (!sortCol) return 0;
    const aVal = a[sortCol];
    const bVal = b[sortCol];
    if (aVal === null || bVal === null) return 0;
    if (aVal < bVal) return sortDesc ? 1 : -1;
    if (aVal > bVal) return sortDesc ? -1 : 1;
    return 0;
  });

  return (
    <div className="animate-fade-in">
      <div className="page-header flex-between">
        <div>
          <h1>Admins & Logs</h1>
          <p>Manage bot administrators and audit their actions</p>
        </div>
        <button onClick={fetchData}>Refresh Data</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem', alignItems: 'start' }}>
        
        {/* Admins Panel */}
        <div>
          <div className="glass-panel" style={{ padding: '0', marginBottom: '2rem', maxHeight: '40vh', overflowY: 'auto' }}>
            <div style={{ padding: '1.5rem 1.5rem 0 1.5rem' }}>
              <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldAlert size={20} color="var(--accent-color)" /> Active Administrators
              </h2>
            </div>
            
            <table className="data-table" style={{ position: 'relative' }}>
              <thead style={{ position: 'sticky', top: 0, backgroundColor: 'var(--bg-secondary)', zIndex: 1 }}>
                <tr>
                  <th onClick={() => handleSort('username')} style={{ cursor: 'pointer' }}>Admin {sortCol === 'username' ? (sortDesc ? '↓' : '↑') : ''}</th>
                  <th onClick={() => handleSort('level')} style={{ cursor: 'pointer' }}>Level {sortCol === 'level' ? (sortDesc ? '↓' : '↑') : ''}</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedAdmins.map(admin => (
                  <tr key={admin.user_id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{admin.username || 'Unknown'}</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>ID: {admin.user_id}</div>
                    </td>
                    <td>
                      <span className={`badge ${admin.level === 2 ? 'danger' : ''}`}>
                        Level {admin.level} {admin.level === 2 && '(Super)'}
                      </span>
                    </td>
                    <td>
                      <button onClick={() => handleRemoveAdmin(admin.user_id)} style={{ padding: '0.4rem', color: 'var(--danger-color)', background: 'transparent', border: '1px solid var(--danger-color)' }}>
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
                {sortedAdmins.length === 0 && (
                  <tr><td colSpan={3} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>No admins found.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <UserPlus size={20} color="var(--success-color)" /> Add Administrator
            </h2>
            <form onSubmit={handleAddAdmin} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.25rem' }}>User ID</label>
                <input type="number" required value={newAdminId} onChange={e => setNewAdminId(e.target.value)} style={{ width: '100%', boxSizing: 'border-box' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.25rem' }}>Username / Name</label>
                <input type="text" required value={newAdminName} onChange={e => setNewAdminName(e.target.value)} style={{ width: '100%', boxSizing: 'border-box' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.25rem' }}>Admin Level</label>
                <select value={newAdminLevel} onChange={e => setNewAdminLevel(e.target.value)} style={{ width: '100%', boxSizing: 'border-box' }}>
                  <option value="1">Level 1 (Moderator)</option>
                  <option value="2">Level 2 (Super Admin)</option>
                </select>
              </div>
              <button type="submit" className="primary" style={{ marginTop: '0.5rem' }}>Grant Access</button>
            </form>
          </div>
        </div>

        {/* Logs Panel */}
        <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', height: '100%' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Clock size={20} color="var(--text-secondary)" /> Audit Logs
          </h2>
          
          <div style={{ overflowY: 'auto', flex: 1, paddingRight: '0.5rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {logs.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>No audit logs available.</p>
              ) : (
                logs.map(log => (
                  <div key={log.id} style={{ padding: '1rem', background: 'var(--bg-primary)', borderRadius: 'var(--radius-md)', borderLeft: '3px solid var(--accent-color)' }}>
                    <div className="flex-between" style={{ marginBottom: '0.5rem' }}>
                      <span style={{ fontWeight: 600 }}>{log.admin_name} <span style={{ color: 'var(--text-secondary)', fontWeight: 400 }}>({log.admin_id})</span></span>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{log.timestamp}</span>
                    </div>
                    <div style={{ marginBottom: '0.25rem' }}>
                      <span className="badge" style={{ background: 'rgba(88, 166, 255, 0.1)', color: 'var(--accent-color)' }}>{log.action}</span>
                      {log.target_user && <span style={{ marginLeft: '0.5rem', fontSize: '0.875rem' }}>Target: {log.target_user}</span>}
                    </div>
                    {log.details && (
                      <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', background: 'var(--bg-secondary)', padding: '0.5rem', borderRadius: '4px', marginTop: '0.5rem' }}>
                        {log.details}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
