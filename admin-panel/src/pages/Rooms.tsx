import { useEffect, useState } from 'react';
import { Trash2 } from 'lucide-react';

interface Game {
  chat_id: number;
  players: string;
  game_type: string;
  game_state: string;
  state: string;
}

export default function Rooms() {
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortCol, setSortCol] = useState<keyof Game | null>(null);
  const [sortDesc, setSortDesc] = useState(true);

  const fetchGames = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/rooms');
      if (!res.ok) throw new Error('Network error');
      const result = await res.json();
      setGames(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const deleteGame = async (chat_id: number) => {
    if (!window.confirm('Are you sure you want to force end this game?')) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/rooms/${chat_id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete');
      fetchGames();
    } catch (err) {
      console.error(err);
      alert('Failed to delete game');
    }
  };

  useEffect(() => {
    fetchGames();
    const interval = setInterval(fetchGames, 5000);
    return () => clearInterval(interval);
  }, []);

  const renderPlayers = (playersJson: string) => {
    try {
      const players = JSON.parse(playersJson);
      if (Array.isArray(players)) {
        if (players.length === 0) {
          return <span style={{ color: 'var(--text-secondary)' }}>No players</span>;
        }
        if (players[0].name !== undefined) {
          return (
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {players.map((p: any, i: number) => (
                <span key={p.user_id || i} className="badge" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-primary)', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                  {p.name} {p.username ? <span style={{ color: 'var(--text-secondary)' }}>@{p.username}</span> : ''}
                </span>
              ))}
            </div>
          );
        }
      }
    } catch (e) {
      // fallback
    }
    return <div style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={playersJson}>{playersJson}</div>;
  };

  const handleSort = (col: keyof Game) => {
    if (sortCol === col) {
      setSortDesc(!sortDesc);
    } else {
      setSortCol(col);
      setSortDesc(true);
    }
  };

  const sortedGames = [...games].sort((a, b) => {
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
          <h1>Active Rooms</h1>
          <p>Manage currently running games</p>
        </div>
        <button onClick={fetchGames}>Refresh</button>
      </div>

      <div className="glass-panel data-table-container" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
        {loading && games.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>
        ) : (
          <table className="data-table" style={{ position: 'relative' }}>
            <thead style={{ position: 'sticky', top: 0, backgroundColor: 'var(--bg-secondary)', zIndex: 1 }}>
              <tr>
                <th onClick={() => handleSort('chat_id')} style={{ cursor: 'pointer' }}>Chat ID {sortCol === 'chat_id' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th onClick={() => handleSort('game_type')} style={{ cursor: 'pointer' }}>Game Type {sortCol === 'game_type' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th onClick={() => handleSort('state')} style={{ cursor: 'pointer' }}>State {sortCol === 'state' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th onClick={() => handleSort('players')} style={{ cursor: 'pointer' }}>Players {sortCol === 'players' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedGames.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>No active games</td>
                </tr>
              ) : (
                sortedGames.map((game) => (
                  <tr key={game.chat_id}>
                    <td>{game.chat_id}</td>
                    <td><span className="badge">{game.game_type}</span></td>
                    <td>{game.state}</td>
                    <td>
                      {renderPlayers(game.players)}
                    </td>
                    <td>
                      <button 
                        className="danger" 
                        style={{ padding: '0.4rem 0.8rem', fontSize: '0.875rem' }}
                        onClick={() => deleteGame(game.chat_id)}
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
