import { useState } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { Send, Image as ImageIcon, X } from 'lucide-react';

export default function Broadcast() {
  const [message, setMessage] = useState('');
  const [imagePath, setImagePath] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const handleSelectImage = async () => {
    try {
      const selected = await open({
        multiple: false,
        filters: [{
          name: 'Image',
          extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp']
        }]
      });
      if (selected) {
        setImagePath(selected as string);
      }
    } catch (err) {
      alert('Failed to select image: ' + err);
    }
  };

  const handleBroadcast = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    
    if (!window.confirm('Are you sure you want to send this message to ALL users?')) return;
    
    setSending(true);
    try {
      await fetch('http://127.0.0.1:8000/api/broadcast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_text: message, image_path: imagePath })
      });
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
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Attachment (Optional)</label>
            {imagePath ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: 'var(--radius-md)' }}>
                <ImageIcon size={24} color="var(--accent-color)" />
                <div style={{ flex: 1, wordBreak: 'break-all', fontSize: '0.875rem' }}>{imagePath}</div>
                <button type="button" onClick={() => setImagePath(null)} className="danger" style={{ padding: '0.4rem' }}>
                  <X size={16} />
                </button>
              </div>
            ) : (
              <button type="button" onClick={handleSelectImage} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--bg-tertiary)' }}>
                <ImageIcon size={20} /> Select Image File
              </button>
            )}
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
