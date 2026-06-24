import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, Gamepad2, ShieldAlert, ShoppingBag, Radio, Flag, Settings as SettingsIcon } from 'lucide-react';
import { t } from '../i18n';

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <ShieldAlert size={28} className="text-accent" style={{ color: 'var(--accent-color)' }} />
        <h2>TG Admin</h2>
      </div>
      
      <nav className="sidebar-nav">
        <NavLink 
          to="/" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <LayoutDashboard size={20} />
          {t('dashboard')}
        </NavLink>
        
        <NavLink 
          to="/rooms" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <Gamepad2 size={20} />
          {t('rooms')}
        </NavLink>
        
        <NavLink 
          to="/store" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <ShoppingBag size={20} />
          {t('store')}
        </NavLink>
        
        <NavLink 
          to="/users" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <Users size={20} />
          {t('users')}
        </NavLink>

        <NavLink 
          to="/admins" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <ShieldAlert size={20} />
          {t('admins')}
        </NavLink>
        
        <NavLink 
          to="/reports" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <Flag size={20} />
          {t('reports')}
        </NavLink>

        <NavLink 
          to="/broadcast" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <Radio size={20} />
          {t('broadcast')}
        </NavLink>

        <div style={{ margin: '1rem 0', height: '1px', backgroundColor: 'var(--border-color)', opacity: 0.5 }}></div>

        <NavLink 
          to="/settings" 
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <SettingsIcon size={20} />
          {t('settings')}
        </NavLink>
      </nav>
    </aside>
  );
}
