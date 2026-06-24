import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Users, Gamepad2, Coins, Settings, RefreshCw } from 'lucide-react';
import { api } from '../api';

interface Metric {
  timestamp: string;
  total_users: number;
  total_coins: number;
  active_games: number;
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [chartType, setChartType] = useState<'users' | 'economy' | 'games'>('users');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = async () => {
    try {
      const data = await api.getMetrics();
      if (Array.isArray(data)) {
        setMetrics(data);
      }
      setError('');
    } catch (err: any) {
      setError(err.toString());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 20000); // Обновление каждые 20 сек
    return () => clearInterval(interval);
  }, []);

  const latest = metrics.length > 0 ? metrics[metrics.length - 1] : null;

  // Координаты для SVG-графика на мобильном
  const getChartColor = () => {
    if (chartType === 'economy') return '#a371f7';
    if (chartType === 'games') return '#58a6ff';
    return '#3fb950';
  };

  const getChartDataPoints = () => {
    if (metrics.length === 0) return [];
    
    const values = metrics.map(m => {
      if (chartType === 'economy') return m.total_coins;
      if (chartType === 'games') return m.active_games;
      return m.total_users;
    });

    const max = Math.max(...values, 5);
    const min = Math.min(...values, 0);
    const range = max - min || 1;

    return values.map((val, idx) => {
      const x = (idx / (values.length - 1 || 1)) * 500;
      const y = 170 - ((val - min) / range) * 130;
      
      let label = '';
      if (metrics[idx].timestamp) {
        const parts = metrics[idx].timestamp.split(' ');
        if (parts[1]) {
          const timeParts = parts[1].split(':');
          label = `${timeParts[0]}:${timeParts[1]}`;
        }
      }

      return { x, y, value: val, label };
    });
  };

  const points = getChartDataPoints();
  const pathD = points.length > 0 ? `M ${points.map(p => `${p.x},${p.y}`).join(' L ')}` : '';
  const areaD = points.length > 0 ? `${pathD} L 500,180 L 0,180 Z` : '';
  const activeColor = getChartColor();

  return (
    <div className="animate-fade-in" style={{ paddingBottom: '2rem' }}>
      <div className="page-header flex-between">
        <div>
          <h1>Dashboard</h1>
          <p>Real-time overview of your Telegram Bot</p>
        </div>
        <button onClick={fetchData} className="flex-center" style={{ gap: '0.3rem' }}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {error && (
        <div className="glass-panel" style={{ padding: '1.5rem', color: 'var(--danger-color)', marginBottom: '1.5rem', background: 'rgba(248, 81, 73, 0.1)' }}>
          <h3 style={{ marginTop: 0, marginBottom: '0.5rem' }}>Connection Failed</h3>
          <p style={{ margin: '0 0 1rem 0' }}>{error}</p>
          <p style={{ margin: '0 0 1rem 0', color: 'var(--text-primary)' }}>
            The app is trying to connect to <strong>{localStorage.getItem('api_base_url') || 'http://localhost:8000'}</strong>.
            If you are running on an Android device, <code>localhost</code> points to the phone itself. 
            You must use the IPv4 address of your computer (e.g. <code>http://192.168.x.x:8000</code>).
          </p>
          <Link to="/settings" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', background: 'var(--bg-tertiary)', padding: '0.5rem 1rem', borderRadius: 'var(--radius-md)', color: 'var(--text-primary)' }}>
            <Settings size={18} /> Go to Settings to change API URL
          </Link>
        </div>
      )}

      {loading && !latest ? (
        <p>Loading stats...</p>
      ) : latest ? (
        <div className="stats-grid">
          <div className="glass-panel stat-card">
            <div className="stat-icon">
              <Users size={24} />
            </div>
            <div className="stat-info">
              <h3>Total Users</h3>
              <p>{(latest.total_users || 0).toLocaleString()}</p>
            </div>
          </div>
          
          <div className="glass-panel stat-card">
            <div className="stat-icon" style={{ background: 'rgba(88, 166, 255, 0.1)', color: '#58a6ff' }}>
              <Gamepad2 size={24} />
            </div>
            <div className="stat-info">
              <h3>Active Games</h3>
              <p>{(latest.active_games || 0).toLocaleString()}</p>
            </div>
          </div>
          
          <div className="glass-panel stat-card">
            <div className="stat-icon" style={{ background: 'rgba(163, 113, 247, 0.1)', color: '#a371f7' }}>
              <Coins size={24} />
            </div>
            <div className="stat-info">
              <h3>Economy Total</h3>
              <p>{(latest.total_coins || 0).toLocaleString()} 🪙</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center' }}>
          No metrics data available.
        </div>
      )}

      {/* Раздел Неонового Графика */}
      {metrics.length > 0 && (
        <div className="glass-panel" style={{ marginTop: '1.5rem', padding: '1.25rem' }}>
          <div className="flex-between" style={{ marginBottom: '1.25rem', flexDirection: 'column', gap: '0.75rem', alignItems: 'stretch' }}>
            <h3 style={{ margin: 0 }}>Performance & Activity</h3>
            <div style={{ display: 'flex', gap: '0.3rem', width: '100%' }}>
              <button className={chartType === 'users' ? 'primary' : ''} onClick={() => setChartType('users')} style={{ flex: 1, fontSize: '0.75rem', padding: '0.4rem 0.5rem' }}>Users</button>
              <button className={chartType === 'economy' ? 'primary' : ''} onClick={() => setChartType('economy')} style={{ flex: 1, fontSize: '0.75rem', padding: '0.4rem 0.5rem' }}>Coins</button>
              <button className={chartType === 'games' ? 'primary' : ''} onClick={() => setChartType('games')} style={{ flex: 1, fontSize: '0.75rem', padding: '0.4rem 0.5rem' }}>Games</button>
            </div>
          </div>
          
          <div style={{ position: 'relative', width: '100%', overflow: 'visible' }}>
            <svg viewBox="0 0 500 200" width="100%" height="180" style={{ overflow: 'visible' }}>
              <defs>
                <filter id="android-glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="5" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                <linearGradient id="androidChartGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={activeColor} stopOpacity="0.25" />
                  <stop offset="100%" stopColor={activeColor} stopOpacity="0.0" />
                </linearGradient>
              </defs>

              <line x1="0" y1="40" x2="500" y2="40" stroke="#21262d" strokeDasharray="3" />
              <line x1="0" y1="105" x2="500" y2="105" stroke="#21262d" strokeDasharray="3" />
              <line x1="0" y1="170" x2="500" y2="170" stroke="#21262d" strokeDasharray="3" />

              {areaD && <path d={areaD} fill="url(#androidChartGrad)" />}

              {pathD && (
                <path 
                  d={pathD} 
                  fill="none" 
                  stroke={activeColor} 
                  strokeWidth="3" 
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  filter="url(#android-glow)"
                />
              )}

              {points.map((p, idx) => (
                <g key={idx}>
                  <circle 
                    cx={p.x} 
                    cy={p.y} 
                    r="4" 
                    fill="var(--bg-main)" 
                    stroke={activeColor} 
                    strokeWidth="2" 
                  />
                  {(points.length < 8 || idx % 3 === 0 || idx === points.length - 1) && (
                    <text 
                      x={p.x} 
                      y={p.y - 10} 
                      fill="var(--text-main)" 
                      fontSize="9" 
                      textAnchor="middle"
                      fontWeight="bold"
                    >
                      {p.value}
                    </text>
                  )}
                  {(points.length < 8 || idx % 3 === 0 || idx === points.length - 1) && (
                    <text 
                      x={p.x} 
                      y="192" 
                      fill="var(--text-secondary)" 
                      fontSize="8" 
                      textAnchor="middle"
                    >
                      {p.label}
                    </text>
                  )}
                </g>
              ))}
            </svg>
          </div>
        </div>
      )}
    </div>
  );
}
