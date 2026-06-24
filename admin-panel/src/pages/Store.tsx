import { useEffect, useState } from 'react';
import { ShoppingBag, Plus, Edit2, Trash2, Tag, Box } from 'lucide-react';

interface StoreItem {
  id: number;
  name: string;
  description: string;
  price: number;
  item_type: string;
  value: string;
  is_active: boolean;
}

export default function Store() {
  const [items, setItems] = useState<StoreItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortCol, setSortCol] = useState<keyof StoreItem | null>(null);
  const [sortDesc, setSortDesc] = useState(true);

  const [editingItem, setEditingItem] = useState<Partial<StoreItem> | null>(null);

  const fetchItems = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/items');
      if (!res.ok) throw new Error('Network error');
      const result = await res.json();
      setItems(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem) return;
    
    try {
      if (editingItem.id) {
        await fetch('http://127.0.0.1:8000/api/items/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: editingItem.id,
            name: editingItem.name,
            description: editingItem.description,
            price: Number(editingItem.price),
            item_type: editingItem.item_type,
            value: editingItem.value,
            is_active: editingItem.is_active
          })
        });
      } else {
        await fetch('http://127.0.0.1:8000/api/items', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: editingItem.name,
            description: editingItem.description,
            price: Number(editingItem.price),
            item_type: editingItem.item_type || 'title',
            value: editingItem.value,
            is_active: editingItem.is_active ?? true
          })
        });
      }
      setEditingItem(null);
      fetchItems();
    } catch (err) {
      alert('Failed to save item: ' + err);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Delete this item from the store completely?')) return;
    try {
      await fetch(`http://127.0.0.1:8000/api/items/${id}`, { method: 'DELETE' });
      fetchItems();
    } catch (err) {
      alert('Failed to delete item: ' + err);
    }
  };

  const handleSort = (col: keyof StoreItem) => {
    if (sortCol === col) {
      setSortDesc(!sortDesc);
    } else {
      setSortCol(col);
      setSortDesc(true);
    }
  };

  const sortedItems = [...items].sort((a, b) => {
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
          <h1>Global Economy Store</h1>
          <p>Manage items that players can buy with coins</p>
        </div>
        <button className="primary" onClick={() => setEditingItem({ name: '', description: '', price: 100, item_type: 'title', value: '', is_active: true })}>
          <Plus size={20} /> Add New Item
        </button>
      </div>

      <div className="glass-panel data-table-container" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center' }}>Loading store inventory...</div>
        ) : items.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <Box size={48} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
            <p>Store is empty. Click "Add New Item" to create one.</p>
          </div>
        ) : (
          <table className="data-table" style={{ position: 'relative' }}>
            <thead style={{ position: 'sticky', top: 0, backgroundColor: 'var(--bg-secondary)', zIndex: 1 }}>
              <tr>
                <th onClick={() => handleSort('id')} style={{ cursor: 'pointer' }}>ID {sortCol === 'id' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th onClick={() => handleSort('name')} style={{ cursor: 'pointer' }}>Item Details {sortCol === 'name' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th onClick={() => handleSort('price')} style={{ cursor: 'pointer' }}>Price {sortCol === 'price' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th onClick={() => handleSort('item_type')} style={{ cursor: 'pointer' }}>Effect Type {sortCol === 'item_type' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th onClick={() => handleSort('is_active')} style={{ cursor: 'pointer' }}>Status {sortCol === 'is_active' ? (sortDesc ? '↓' : '↑') : ''}</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedItems.map(item => (
                <tr key={item.id}>
                  <td><code>{item.id}</code></td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{item.name}</div>
                    <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{item.description}</div>
                  </td>
                  <td style={{ color: '#e3b341', fontWeight: 600 }}>{item.price} 🪙</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Tag size={16} color="var(--accent-color)" />
                      <span>{item.item_type} <span style={{ color: 'var(--text-secondary)' }}>({item.value})</span></span>
                    </div>
                  </td>
                  <td>
                    {item.is_active ? <span className="badge success">On Sale</span> : <span className="badge danger">Hidden</span>}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button onClick={() => setEditingItem(item)} style={{ padding: '0.4rem', fontSize: '0.875rem' }}>
                        <Edit2 size={16} />
                      </button>
                      <button className="danger" onClick={() => handleDelete(item.id)} style={{ padding: '0.4rem', fontSize: '0.875rem' }}>
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {editingItem && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
          zIndex: 50, overflowY: 'auto', padding: '5vh 1rem'
        }}>
          <div className="glass-panel" style={{ 
            padding: '2rem', width: '100%', maxWidth: '500px',
            margin: '0 auto'
          }}>
            <h2 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShoppingBag size={24} color="var(--accent-color)" /> {editingItem.id ? 'Edit Store Item' : 'New Store Item'}
            </h2>
            <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              
              <div>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>Item Name</label>
                <input required type="text" value={editingItem.name || ''} onChange={(e) => setEditingItem({...editingItem, name: e.target.value})} style={{ width: '100%', boxSizing: 'border-box' }} placeholder="e.g. Pro Player Title" />
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>Description</label>
                <textarea value={editingItem.description || ''} onChange={(e) => setEditingItem({...editingItem, description: e.target.value})} style={{ width: '100%', boxSizing: 'border-box', resize: 'vertical' }} placeholder="What does it do?"></textarea>
              </div>

              <div style={{ display: 'flex', gap: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>Price (Coins)</label>
                  <input required type="number" min="0" value={editingItem.price || 0} onChange={(e) => setEditingItem({...editingItem, price: parseInt(e.target.value)})} style={{ width: '100%', boxSizing: 'border-box' }} />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>Item Type</label>
                  <select value={editingItem.item_type || 'title'} onChange={(e) => setEditingItem({...editingItem, item_type: e.target.value})} style={{ width: '100%', boxSizing: 'border-box' }}>
                    <option value="title">Title / Role</option>
                    <option value="emoji">Profile Emoji</option>
                    <option value="other">Other Effect</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem' }}>Effect Value</label>
                <input required type="text" value={editingItem.value || ''} onChange={(e) => setEditingItem({...editingItem, value: e.target.value})} style={{ width: '100%', boxSizing: 'border-box' }} placeholder="e.g. 👑 Pro" />
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>The exact string that will be applied to the user.</p>
              </div>

              <div style={{ marginTop: '0.5rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={editingItem.is_active ?? true} onChange={(e) => setEditingItem({...editingItem, is_active: e.target.checked})} style={{ width: '20px', height: '20px' }} />
                  <span style={{ fontWeight: 500 }}>Active (Available in Shop)</span>
                </label>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                <button type="button" onClick={() => setEditingItem(null)}>Cancel</button>
                <button type="submit" className="primary">{editingItem.id ? 'Save Changes' : 'Create Item'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
