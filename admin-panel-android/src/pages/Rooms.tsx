import { useEffect, useState } from 'react';
import { Trash2 } from 'lucide-react';
import { api } from '../api';

interface Player {
  user_id: number;
  name: string;
}

interface Room {
  chat_id: number;
  players: Player[];
  game_type: string;
  state: string;
}

export default function Rooms() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortCol, setSortCol] = useState<keyof Room | null>(null);
  const [sortDesc, setSortDesc] = useState(true);

  const fetchRooms = async () => {
    try {
      const result = await api.getRooms();
      setRooms(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const deleteRoom = async (chatId: number) => {
    if (!window.confirm('Are you sure you want to force end this game?')) return;
    try {
      await api.deleteRoom(chatId);
      fetchRooms();
    } catch (err) {
      console.error(err);
      alert('Failed to delete game');
    }
  };

  useEffect(() => {
    fetchRooms();
    const interval = setInterval(fetchRooms, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSort = (col: keyof Room) => {
    if (sortCol === col) {
      setSortDesc(!sortDesc);
    } else {
      setSortCol(col);
      setSortDesc(true);
    }
  };

  const sortedRooms = [...rooms].sort((a, b) => {
    if (!sortCol) return 0;
    const aVal = a[sortCol];
    const bVal = b[sortCol];

    if (Array.isArray(aVal) || Array.isArray(bVal)) return 0;

    if (aVal === null || bVal === null) return 0;
    if (aVal < bVal) return sortDesc ? 1 : -1;
    if (aVal > bVal) return sortDesc ? -1 : 1;
    return 0;
  });

  return (
    <div className="animate-fade-in">
      <div className="page-header flex-between">
        <div>
          <h1>Active Rooms</h1>
          <p>Manage currently running games</p>
        </div>
        <button onClick={fetchRooms}>Refresh</button>
      </div>

      <div className="glass-panel data-table-container" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
        {loading && rooms.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>
        ) : (
          <table className="data-table" style={{ position: 'relative' }}>
            <thead style={{ position: 'sticky', top: 0, backgroundColor: 'var(--bg-secondary)', zIndex: 1 }}>
              <tr>
                <th onClick={() => handleSort('chat_id')} style={{ cursor: 'pointer' }}>Chat ID {sortCol === 'chat_id' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th onClick={() => handleSort('game_type')} style={{ cursor: 'pointer' }}>Game Type {sortCol === 'game_type' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th onClick={() => handleSort('state')} style={{ cursor: 'pointer' }}>State {sortCol === 'state' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th>Players</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedRooms.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>No active games</td>
                </tr>
              ) : (
                sortedRooms.map((room) => (
                  <tr key={room.chat_id}>
                    <td><code>{room.chat_id}</code></td>
                    <td><span className="badge">{room.game_type}</span></td>
                    <td><span className={`badge ${room.state === 'waiting' ? '' : 'success'}`}>{room.state}</span></td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        {room.players.length === 0 ? (
                          <span style={{ color: 'var(--text-secondary)' }}>No players</span>
                        ) : (
                          room.players.map((p, i) => (
                            <span key={p.user_id || i} className="badge" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}>
                              {p.name}
                            </span>
                          ))
                        )}
                      </div>
                    </td>
                    <td>
                      <button 
                        className="danger" 
                        style={{ padding: '0.4rem 0.8rem', fontSize: '0.875rem' }}
                        onClick={() => deleteRoom(room.chat_id)}
                      >
                        <Trash2 size={16} /> Force End
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
