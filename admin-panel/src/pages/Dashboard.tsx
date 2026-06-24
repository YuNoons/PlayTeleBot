import { useEffect, useState } from 'react';
import { Users, Gamepad2, Coins, RefreshCw } from 'lucide-react';
import { apiRequest } from '../api';

interface DashboardStats {
  total_users: number;
  active_rooms: number;
  total_coins: number;
}

interface MetricPoint {
  timestamp: string;
  total_users: number;
  total_coins: number;
  active_games: number;
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [metrics, setMetrics] = useState<MetricPoint[]>([]);
  const [chartType, setChartType] = useState<'users' | 'economy' | 'games'>('users');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchStats = async () => {
    try {
      const result = await apiRequest<DashboardStats>('/api/dashboard_stats');
      // Если запрос прошел оффлайн, apiRequest вернет { offline: true }
      if (result && !('offline' in result)) {
        setStats(result);
      }
      setError('');
    } catch (err: any) {
      setError(err.toString());
    } finally {
      setLoading(false);
    }
  };

  const fetchMetrics = async () => {
    try {
      const result = await apiRequest<MetricPoint[]>('/api/metrics');
      if (Array.isArray(result)) {
        setMetrics(result);
      }
    } catch (err) {
      console.error('Failed to fetch metrics:', err);
    }
  };

  const refreshAll = () => {
    fetchStats();
    fetchMetrics();
  };

  useEffect(() => {
    refreshAll();
    const interval = setInterval(refreshAll, 15000); // авто-обновление каждые 15 сек
    return () => clearInterval(interval);
  }, []);

  // Вычисление координат для SVG графика
  const getChartColor = () => {
    if (chartType === 'economy') return '#a371f7'; // Фиолетовый
    if (chartType === 'games') return '#58a6ff'; // Синий
    return '#3fb950'; // Зеленый
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
      const y = 170 - ((val - min) / range) * 130; // 30px padding bottom, 10px top
      
      // Парсим время из таймстемпа (например, "2026-06-24 12:00:00" -> "12:00")
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
    <div className="animate-fade-in">
      <div className="page-header flex-between">
        <div>
          <h1>Dashboard</h1>
          <p>Real-time overview of your Telegram Bot</p>
        </div>
        <button onClick={refreshAll} className="flex-center" style={{ gap: '0.5rem' }}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {error && (
        <div className="glass-panel" style={{ padding: '1rem', color: 'var(--danger-color)', marginBottom: '1rem' }}>
          Error: {error}
        </div>
      )}

      {loading && !stats ? (
        <p>Loading stats...</p>
      ) : stats ? (
        <div className="stats-grid">
          <div className="glass-panel stat-card">
            <div className="stat-icon">
              <Users size={24} />
            </div>
            <div className="stat-info">
              <h3>Total Users</h3>
              <p>{(stats.total_users || 0).toLocaleString()}</p>
            </div>
          </div>
          
          <div className="glass-panel stat-card">
            <div className="stat-icon" style={{ background: 'rgba(88, 166, 255, 0.1)', color: '#58a6ff' }}>
              <Gamepad2 size={24} />
            </div>
            <div className="stat-info">
              <h3>Active Rooms</h3>
              <p>{(stats.active_rooms || 0).toLocaleString()}</p>
            </div>
          </div>
          
          <div className="glass-panel stat-card">
            <div className="stat-icon" style={{ background: 'rgba(163, 113, 247, 0.1)', color: '#a371f7' }}>
              <Coins size={24} />
            </div>
            <div className="stat-info">
              <h3>Economy Total</h3>
              <p>{(stats.total_coins || 0).toLocaleString()} 🪙</p>
            </div>
          </div>
        </div>
      ) : null}

      {/* Раздел Неонового Интерактивного Графика */}
      <div className="glass-panel" style={{ marginTop: '2rem', padding: '1.5rem' }}>
        <div className="flex-between" style={{ marginBottom: '1.5rem' }}>
          <h3>Performance & Activity Graph</h3>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className={chartType === 'users' ? 'primary' : ''} onClick={() => setChartType('users')} style={{ fontSize: '0.875rem', padding: '0.4rem 0.8rem' }}>Users Online</button>
            <button className={chartType === 'economy' ? 'primary' : ''} onClick={() => setChartType('economy')} style={{ fontSize: '0.875rem', padding: '0.4rem 0.8rem' }}>Economy (Coins)</button>
            <button className={chartType === 'games' ? 'primary' : ''} onClick={() => setChartType('games')} style={{ fontSize: '0.875rem', padding: '0.4rem 0.8rem' }}>Active Games</button>
          </div>
        </div>

        {metrics.length === 0 ? (
          <div style={{ padding: '4rem 2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <p>No activity metrics data available yet.</p>
            <p style={{ fontSize: '0.875rem' }}>The bot needs to run longer to collect enough history points.</p>
          </div>
        ) : (
          <div style={{ position: 'relative', width: '100%', padding: '0.5rem' }}>
            {/* SVG Линейный График с неоновым свечением */}
            <svg viewBox="0 0 500 200" width="100%" height="250" style={{ overflow: 'visible' }}>
              <defs>
                {/* Неоновое свечение (glow) */}
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="6" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                
                {/* Градиент заливки под линией */}
                <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={activeColor} stopOpacity="0.3" />
                  <stop offset="100%" stopColor={activeColor} stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Сетка горизонтальных линий */}
              <line x1="0" y1="40" x2="500" y2="40" stroke="#21262d" strokeDasharray="3" />
              <line x1="0" y1="105" x2="500" y2="105" stroke="#21262d" strokeDasharray="3" />
              <line x1="0" y1="170" x2="500" y2="170" stroke="#21262d" strokeDasharray="3" />

              {/* Заливка области под линией */}
              {areaD && <path d={areaD} fill="url(#chartGrad)" />}

              {/* Светящаяся неоновая линия графика */}
              {pathD && (
                <path 
                  d={pathD} 
                  fill="none" 
                  stroke={activeColor} 
                  strokeWidth="3.5" 
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  filter="url(#glow)"
                />
              )}

              {/* Точки на графике с подписями значений */}
              {points.map((p, idx) => (
                <g key={idx}>
                  <circle 
                    cx={p.x} 
                    cy={p.y} 
                    r="4.5" 
                    fill="var(--bg-main)" 
                    stroke={activeColor} 
                    strokeWidth="2.5" 
                  />
                  {/* Подписи значений над точками (показываем каждую вторую/третью если точек много) */}
                  {(points.length < 10 || idx % 2 === 0 || idx === points.length - 1) && (
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
                  {/* Подписи оси X (времени) под графиком */}
                  {(points.length < 10 || idx % 2 === 0 || idx === points.length - 1) && (
                    <text 
                      x={p.x} 
                      y="192" 
                      fill="var(--text-secondary)" 
                      fontSize="9" 
                      textAnchor="middle"
                    >
                      {p.label}
                    </text>
                  )}
                </g>
              ))}
            </svg>
          </div>
        )}
      </div>
    </div>
  );
}
