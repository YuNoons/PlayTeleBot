import { useEffect, useState } from 'react';
import { Flag, CheckCircle, XCircle } from 'lucide-react';
import { api } from '../api';

interface Report {
  id: number;
  sender_name: string;
  target_id: number | null;
  reason: string;
  status: string;
  created_at?: string; // Optional as not in current API snippet but was in old code
}

export default function Reports() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchReports = async () => {
    try {
      const res = await api.getReports();
      setReports(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleResolve = async (id: number, status: string) => {
    try {
      await api.updateReportStatus(id, status);
      fetchReports();
    } catch (err) {
      alert('Failed to update report: ' + err);
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header flex-between">
        <div>
          <h1>User Reports</h1>
          <p>Review and moderate complaints from players</p>
        </div>
        <button onClick={fetchReports}>Refresh</button>
      </div>

      <div className="glass-panel data-table-container" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center' }}>Loading reports...</div>
        ) : reports.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <Flag size={48} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
            <p>No reports found. Everyone is happy!</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', padding: '1rem' }}>
            {reports.map(r => (
              <div key={r.id} style={{ 
                padding: '1.5rem', 
                background: 'rgba(0,0,0,0.2)', 
                borderRadius: 'var(--radius-md)', 
                borderLeft: `4px solid ${r.status === 'pending' ? 'var(--warning-color)' : r.status === 'resolved' ? 'var(--success-color)' : 'var(--danger-color)'}` 
              }}>
                <div className="flex-between" style={{ marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontWeight: 600 }}>Report #{r.id}</span>
                    <span className={`badge ${r.status === 'pending' ? 'warning' : r.status === 'resolved' ? 'success' : 'danger'}`}>
                      {r.status.toUpperCase()}
                    </span>
                  </div>
                  {r.created_at && <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{r.created_at}</span>}
                </div>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem', fontSize: '0.875rem' }}>
                  <div>
                    <div style={{ color: 'var(--text-secondary)' }}>Sender</div>
                    <div style={{ fontWeight: 500 }}>{r.sender_name}</div>
                  </div>
                  {r.target_id && (
                    <div>
                      <div style={{ color: 'var(--text-secondary)' }}>Target User ID</div>
                      <div style={{ fontWeight: 500 }}><code>{r.target_id}</code></div>
                    </div>
                  )}
                </div>

                <div style={{ background: 'var(--bg-secondary)', padding: '1rem', borderRadius: '4px', marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem', textTransform: 'uppercase' }}>Complaint Reason</div>
                  <div>{r.reason}</div>
                </div>

                {r.status === 'pending' && (
                  <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                    <button className="danger" onClick={() => handleResolve(r.id, 'rejected')} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <XCircle size={16} /> Reject Report
                    </button>
                    <button className="primary" onClick={() => handleResolve(r.id, 'resolved')} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <CheckCircle size={16} /> Mark as Resolved
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
