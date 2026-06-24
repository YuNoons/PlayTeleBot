import { useEffect, useState } from 'react';
import { Search, Edit2 } from 'lucide-react';
import { api } from '../api';

interface User {
  user_id: number;
  name: string;
  username: string;
  games_played: number;
  wins: number;
  coins: number;
  title: string;
  is_banned: number; // 0 or 1 from API
  ban_reason: string;
  ban_until: number | null;
  last_active: string;
  daily_earnings: number;
  played_games: Record<string, number>;
}

export default function Users() {
  const [users, setUsers] = useState<User[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [sortCol, setSortCol] = useState<keyof User | null>(null);
  const [sortDesc, setSortDesc] = useState(true);
  
  const [editingUser, setEditingUser] = useState<User | null>(null);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const result = await api.getUsers(query);
      setUsers(result);
    } catch (err) {
      console.error(err);
      alert('Failed to fetch users. Check API connection.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    
    try {
      await api.updateUser({
        user_id: editingUser.user_id,
        name: editingUser.name,
        username: editingUser.username,
        coins: editingUser.coins,
        title: editingUser.title,
        is_banned: editingUser.is_banned,
        ban_reason: editingUser.ban_reason,
        ban_until: editingUser.ban_until
      });
      setEditingUser(null);
      fetchUsers();
    } catch (err) {
      alert('Failed to update user: ' + err);
    }
  };

  const handleSort = (col: keyof User) => {
    if (sortCol === col) {
      setSortDesc(!sortDesc);
    } else {
      setSortCol(col);
      setSortDesc(true);
    }
  };

  const sortedUsers = [...users].sort((a, b) => {
    if (!sortCol) return 0;
    const aVal = a[sortCol];
    const bVal = b[sortCol];
    if (aVal === null || bVal === null) return 0;
    if (aVal < bVal) return sortDesc ? 1 : -1;
    if (aVal > bVal) return sortDesc ? -1 : 1;
    return 0;
  });

  const isOnline = (lastActive: string) => {
    const lastActiveDate = new Date(lastActive).getTime();
    const now = new Date().getTime();
    return (now - lastActiveDate) < 5 * 60 * 1000; // 5 minutes
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1>Users & Economy</h1>
        <p>Manage player balances, titles, and restrictions</p>
      </div>

      <div className="flex-between" style={{ marginBottom: '1.5rem', gap: '1rem' }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: '400px' }}>
          <Search size={20} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
          <input 
            type="text" 
            placeholder="Search by ID, Name or Username..." 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchUsers()}
            style={{ paddingLeft: '2.5rem', width: '100%', boxSizing: 'border-box' }}
          />
        </div>
        <button className="primary" onClick={fetchUsers}>Search</button>
      </div>

      <div className="glass-panel data-table-container" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>
        ) : (
          <table className="data-table" style={{ position: 'relative' }}>
            <thead style={{ position: 'sticky', top: 0, backgroundColor: 'var(--bg-secondary)', zIndex: 1 }}>
              <tr>
                <th onClick={() => handleSort('user_id')} style={{ cursor: 'pointer' }}>User ID {sortCol === 'user_id' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th onClick={() => handleSort('name')} style={{ cursor: 'pointer' }}>Player {sortCol === 'name' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th onClick={() => handleSort('wins')} style={{ cursor: 'pointer' }}>Stats {sortCol === 'wins' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th onClick={() => handleSort('coins')} style={{ cursor: 'pointer' }}>Balance {sortCol === 'coins' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedUsers.map((u) => (
                <tr key={u.user_id}>
                  <td><code>{u.user_id}</code></td>
                  <td>
                    <div style={{ fontWeight: 500 }}>{u.name}</div>
                    {u.username && <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>@{u.username}</div>}
                    {u.title && <div style={{ fontSize: '0.75rem', color: 'var(--accent-color)' }}>«{u.title}»</div>}
                  </td>
                  <td>
                    <span title="Games Played">🎮 {u.games_played}</span><br/>
                    <span title="Wins" style={{ color: 'var(--success-color)' }}>🏆 {u.wins}</span>
                  </td>
                  <td style={{ fontWeight: 600, color: '#e3b341' }}>{u.coins} 🪙</td>
                  <td>
                    {u.is_banned ? (
                      <span className="badge danger">Banned</span>
                    ) : (u.ban_until && u.ban_until > Date.now() / 1000) ? (
                      <span className="badge warning">Timeout</span>
                    ) : isOnline(u.last_active) ? (
                      <span className="badge success">Online</span>
                    ) : (
                      <span className="badge" style={{ color: 'var(--text-secondary)' }}>Offline</span>
                    )}
                  </td>
                  <td>
                    <button onClick={() => setEditingUser(u)} style={{ padding: '0.4rem 0.8rem', fontSize: '0.875rem' }}>
                      <Edit2 size={16} /> Edit
                    </button>
                  </td>
                </tr>
              ))}
              {sortedUsers.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '2rem' }}>No users found</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Edit Modal Overlay */}
      {editingUser && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
          zIndex: 50, overflowY: 'auto', padding: '5vh 1rem'
        }}>
          <div className="glass-panel" style={{ 
            padding: '2rem', width: '100%', maxWidth: '500px',
            margin: '0 auto'
          }}>
            <h2 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Edit2 size={24} color="var(--accent-color)" /> Edit User
            </h2>
            <form onSubmit={handleUpdate} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              
              <div style={{ display: 'flex', gap: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Balance (Coins)</label>
                  <input type="number" value={editingUser.coins} onChange={(e) => setEditingUser({...editingUser, coins: parseInt(e.target.value) || 0})} style={{ width: '100%', boxSizing: 'border-box' }} />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Custom Title</label>
                  <input type="text" value={editingUser.title} onChange={(e) => setEditingUser({...editingUser, title: e.target.value})} style={{ width: '100%', boxSizing: 'border-box' }} />
                </div>
              </div>

              <div style={{ padding: '1rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', marginTop: '0.5rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Restriction (Moderation)</label>
                <select 
                  value={
                    editingUser.is_banned ? 'permanent' : 
                    editingUser.ban_until && editingUser.ban_until > Date.now() / 1000 ? String(editingUser.ban_until) : 'none'
                  }
                  onChange={e => {
                    const val = e.target.value;
                    if (val === 'none') {
                      setEditingUser({ ...editingUser, is_banned: 0, ban_until: 0, ban_reason: '' });
                    } else if (val === 'permanent') {
                      setEditingUser({ ...editingUser, is_banned: 1, ban_until: 0 });
                    } else {
                      // Custom timeouts based on offset added in options
                      setEditingUser({ ...editingUser, is_banned: 0, ban_until: parseFloat(val) });
                    }
                  }}
                  style={{ width: '100%', boxSizing: 'border-box', marginBottom: '1rem' }}
                >
                  <option value="none">No Restrictions</option>
                  <option value={String(Math.floor(Date.now() / 1000) + 3600)}>Timeout: 1 Hour (Mute)</option>
                  <option value={String(Math.floor(Date.now() / 1000) + 86400)}>Timeout: 24 Hours (Mute)</option>
                  <option value={String(Math.floor(Date.now() / 1000) + 604800)}>Timeout: 1 Week (Mute)</option>
                  <option value="permanent">Permanent Ban</option>
                  {/* If user has an active custom timeout not in list, keep it visible */}
                  {editingUser.ban_until && editingUser.ban_until > Date.now() / 1000 && 
                   ![3600, 86400, 604800].map(offset => String(Math.floor(Date.now() / 1000) + offset)).includes(String(Math.floor(editingUser.ban_until))) && 
                   !editingUser.is_banned && (
                    <option value={String(editingUser.ban_until)}>Active Custom Timeout</option>
                  )}
                </select>
                
                {(editingUser.is_banned || (editingUser.ban_until && editingUser.ban_until > Date.now() / 1000)) && (
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Reason for Restriction</label>
                    <input type="text" value={editingUser.ban_reason || ''} onChange={(e) => setEditingUser({...editingUser, ban_reason: e.target.value})} style={{ width: '100%', boxSizing: 'border-box' }} placeholder="Why is this user restricted?" />
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                <button type="button" onClick={() => setEditingUser(null)}>Cancel</button>
                <button type="submit" className="primary">Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
