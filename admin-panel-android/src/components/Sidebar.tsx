import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, Gamepad2, ShieldAlert, ShoppingBag, Radio, Flag, Settings as SettingsIcon, X } from 'lucide-react';
import { t } from '../i18n';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  return (
    <>
      <div className={`sidebar-overlay ${isOpen ? 'visible' : ''}`} onClick={onClose} />
      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-header flex-between">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <ShieldAlert size={28} style={{ color: 'var(--accent-color)' }} />
            <h2>TG Admin</h2>
          </div>
          <button onClick={onClose} className="burger-btn" style={{ padding: '0.25rem' }}>
            <X size={24} />
          </button>
        </div>
        
        <nav className="sidebar-nav">
          {[
            { to: "/", icon: <LayoutDashboard size={20} />, label: t('dashboard') },
            { to: "/rooms", icon: <Gamepad2 size={20} />, label: t('rooms') },
            { to: "/store", icon: <ShoppingBag size={20} />, label: t('store') },
            { to: "/users", icon: <Users size={20} />, label: t('users') },
            { to: "/admins", icon: <ShieldAlert size={20} />, label: t('admins') },
            { to: "/reports", icon: <Flag size={20} />, label: t('reports') },
            { to: "/broadcast", icon: <Radio size={20} />, label: t('broadcast') },
          ].map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}

          <div style={{ margin: '1rem 0', height: '1px', backgroundColor: 'var(--border-color)', opacity: 0.5 }}></div>

          <NavLink
            to="/settings"
            onClick={onClose}
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <SettingsIcon size={20} />
            {t('settings')}
          </NavLink>
        </nav>
      </aside>
    </>
  );
}
