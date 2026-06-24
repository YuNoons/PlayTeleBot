import { useEffect, useState } from 'react';
import { Settings as SettingsIcon, Wrench, Save, RefreshCw } from 'lucide-react';

export default function Settings() {
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchSettings = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/settings');
      if (!res.ok) throw new Error('Network error');
      const result = await res.json();
      setSettings(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const updateSetting = (key: string, value: string) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch('http://127.0.0.1:8000/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings })
      });
      alert('Settings saved successfully!');
    } catch (err) {
      alert('Failed to save settings: ' + err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header flex-between">
        <div>
          <h1>Global Settings</h1>
          <p>Configure bot behavior, limits, and maintenance modes</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button onClick={fetchSettings} disabled={loading || saving} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <RefreshCw size={16} /> Reload
          </button>
          <button className="primary" onClick={handleSave} disabled={loading || saving} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Save size={16} /> {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        
        {/* Language Selection */}
        <div className="glass-panel" style={{ padding: '2rem', gridColumn: '1 / -1' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <SettingsIcon size={24} color="var(--accent-color)" /> App Preferences
          </h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
            <div>
              <h3 style={{ margin: '0 0 0.5rem 0' }}>Interface Language</h3>
              <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Select the language for the Admin Panel. Changing this will reload the application.
              </p>
            </div>
            <select 
              value={localStorage.getItem('app_language') || 'en'}
              onChange={(e) => {
                localStorage.setItem('app_language', e.target.value);
                window.location.reload();
              }}
              style={{ padding: '0.5rem', borderRadius: '4px', background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', minWidth: '150px' }}
            >
              <option value="en">English</option>
              <option value="ru">Русский</option>
            </select>
          </div>
        </div>

        {/* Maintenance Mode */}
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Wrench size={24} color="var(--warning-color)" /> System Control
          </h2>
          
          <div style={{ padding: '1.5rem', background: 'rgba(255, 171, 0, 0.1)', border: '1px solid var(--warning-color)', borderRadius: 'var(--radius-md)' }}>
            <div className="flex-between">
              <div>
                <h3 style={{ margin: '0 0 0.5rem 0', color: 'var(--warning-color)' }}>Maintenance Mode</h3>
                <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  If enabled, all users will see a "Bot is under maintenance" message. 
                  Use this during major updates or database migrations.
                </p>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input 
                  type="checkbox" 
                  checked={settings['maintenance_mode'] === 'true'} 
                  onChange={e => updateSetting('maintenance_mode', e.target.checked ? 'true' : 'false')}
                  style={{ width: '24px', height: '24px', accentColor: 'var(--warning-color)' }}
                />
              </label>
            </div>
          </div>
        </div>

        {/* Economy & Limits */}
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <SettingsIcon size={24} color="var(--accent-color)" /> Economy & Limits
          </h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div>
              <div className="flex-between" style={{ marginBottom: '0.5rem' }}>
                <label style={{ fontWeight: 500 }}>Welcome Bonus Amount</label>
                <span className="badge" style={{ fontSize: '1rem' }}>{settings['welcome_bonus_amount'] || 0} 🪙</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max="1000" 
                step="50"
                value={settings['welcome_bonus_amount'] || 0} 
                onChange={e => updateSetting('welcome_bonus_amount', e.target.value)}
                style={{ width: '100%', cursor: 'pointer' }}
              />
              <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Coins given to a new user when they start the bot for the first time.
              </p>
            </div>

            <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)', margin: '0.5rem 0' }} />

            <div>
              <div className="flex-between" style={{ marginBottom: '0.5rem' }}>
                <label style={{ fontWeight: 500 }}>Max Concurrent Games per User</label>
                <span className="badge" style={{ fontSize: '1rem' }}>{settings['max_games_per_user'] || 1}</span>
              </div>
              <input 
                type="range" 
                min="1" 
                max="20" 
                step="1"
                value={settings['max_games_per_user'] || 1} 
                onChange={e => updateSetting('max_games_per_user', e.target.value)}
                style={{ width: '100%', cursor: 'pointer' }}
              />
              <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Prevents players from spamming too many active game sessions simultaneously.
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
