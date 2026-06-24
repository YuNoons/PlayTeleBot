import { useState } from 'react';
import { Send, Image as ImageIcon, X } from 'lucide-react';
import { api } from '../api';

export default function Broadcast() {
  const [message, setMessage] = useState('');
  const [imagePath, setImagePath] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const handleBroadcast = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    
    if (!window.confirm('Are you sure you want to send this message to ALL users?')) return;
    
    setSending(true);
    try {
      await api.broadcast(message, imagePath);
      alert('Broadcast task added to queue! The bot will send it out shortly.');
      setMessage('');
      setImagePath(null);
    } catch (err) {
      alert('Failed to queue broadcast: ' + err);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1>Global Broadcasting</h1>
        <p>Send a message to all users of the Telegram Bot</p>
      </div>

      <div className="glass-panel" style={{ maxWidth: '800px', margin: '0 auto', padding: '2rem' }}>
        <form onSubmit={handleBroadcast} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Message Text</label>
            <textarea 
              required 
              value={message} 
              onChange={e => setMessage(e.target.value)} 
              placeholder="Hello everyone! We have a huge update today..."
              style={{ 
                width: '100%', 
                minHeight: '200px', 
                boxSizing: 'border-box', 
                resize: 'vertical',
                fontSize: '1rem',
                padding: '1rem'
              }} 
            />
            <div style={{ textAlign: 'right', fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              {message.length} characters
            </div>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
              Server Image Path (Optional)
            </label>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
               <div style={{ position: 'relative', flex: 1 }}>
                <ImageIcon size={18} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                <input
                  type="text"
                  value={imagePath || ''}
                  onChange={e => setImagePath(e.target.value || null)}
                  placeholder="/var/bot/images/promo.jpg"
                  style={{ paddingLeft: '2.5rem', width: '100%', boxSizing: 'border-box' }}
                />
              </div>
              {imagePath && (
                <button type="button" onClick={() => setImagePath(null)} className="danger" style={{ padding: '0.6rem' }}>
                  <X size={16} />
                </button>
              )}
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              Enter the full path to the image file located on the server.
            </p>
          </div>

          <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(255, 171, 0, 0.1)', borderLeft: '4px solid var(--warning-color)', borderRadius: '4px' }}>
            <strong>Warning:</strong> Broadcasting to thousands of users can take several minutes to avoid Telegram API limits. The bot will process this in the background.
          </div>

          <button type="submit" className="primary" disabled={sending || !message.trim()} style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', padding: '1rem', fontSize: '1.1rem' }}>
            <Send size={20} /> {sending ? 'Queueing Broadcast...' : 'Send Global Broadcast'}
          </button>
        </form>
      </div>
    </div>
  );
}
