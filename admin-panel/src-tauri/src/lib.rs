use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use std::fs;
use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64};
use tauri::State;
use dotenvy::dotenv;

mod plotter;


struct AppState {
    db: Mutex<Connection>,
}

#[derive(Serialize)]
struct DashboardStats {
    total_users: i64,
    active_rooms: i64,
    total_coins: i64,
}

#[derive(Serialize)]
struct Game {
    chat_id: i64,
    players: String,
    game_type: String,
    game_state: String,
    state: String,
}

#[derive(Serialize, Deserialize)]
struct User {
    user_id: i64,
    name: String,
    username: String,
    games_played: i64,
    wins: i64,
    coins: i64,
    title: String,
    last_chat_id: Option<i64>,
    is_banned: bool,
    ban_reason: String,
    ban_until: Option<f64>,
    minutes_since_active: f64,
}

#[derive(Serialize)]
struct Admin {
    user_id: i64,
    username: String,
    level: i64,
    added_by: i64,
    added_at: String,
}

#[derive(Serialize)]
struct AdminLog {
    id: i64,
    admin_id: i64,
    admin_name: String,
    action: String,
    target_user: String,
    target_chat: i64,
    details: String,
    timestamp: String,
}

#[derive(Serialize, Deserialize)]
struct StoreItem {
    id: i64,
    name: String,
    description: String,
    price: i64,
    item_type: String,
    value: String,
    is_active: bool,
}

#[derive(Serialize)]
struct Report {
    id: i64,
    sender_id: i64,
    sender_name: String,
    target_id: Option<i64>,
    reason: String,
    status: String,
    created_at: String,
}

#[derive(Serialize, Deserialize)]
struct Setting {
    key: String,
    value: String,
}

#[tauri::command]
fn get_dashboard_stats(state: State<AppState>) -> Result<DashboardStats, String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    
    let total_users: i64 = conn
        .query_row("SELECT COUNT(*) FROM users", [], |row| row.get(0))
        .unwrap_or(0);
        
    let active_rooms: i64 = conn
        .query_row("SELECT COUNT(*) FROM games", [], |row| row.get(0))
        .unwrap_or(0);
        
    let total_coins: i64 = conn
        .query_row("SELECT COALESCE(SUM(coins), 0) FROM users", [], |row| row.get(0))
        .unwrap_or(0);

    Ok(DashboardStats {
        total_users,
        active_rooms,
        total_coins,
    })
}

#[tauri::command]
fn get_games(state: State<AppState>) -> Result<Vec<Game>, String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn.prepare("SELECT chat_id, players, game_type, game_state, state FROM games").map_err(|e| e.to_string())?;
    
    let iter = stmt.query_map([], |row| {
        Ok(Game {
            chat_id: row.get(0)?,
            players: row.get(1)?,
            game_type: row.get(2)?,
            game_state: row.get(3)?,
            state: row.get(4)?,
        })
    }).map_err(|e| e.to_string())?;

    let mut games = Vec::new();
    for game in iter {
        if let Ok(g) = game {
            games.push(g);
        }
    }
    
    Ok(games)
}

#[tauri::command]
fn delete_game(state: State<AppState>, chat_id: i64) -> Result<(), String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM games WHERE chat_id = ?1", [chat_id])
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn get_users(state: State<AppState>, query: String) -> Result<Vec<User>, String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    let sql = format!(
        "SELECT user_id, name, username, games_played, wins, coins, title, last_chat_id, is_banned, ban_reason, ban_until, 
         (julianday('now') - julianday(last_active)) * 24 * 60 AS minutes_since_active
         FROM users 
         WHERE name LIKE '%{}%' OR username LIKE '%{}%' OR CAST(user_id AS TEXT) LIKE '%{}%' 
         LIMIT 100", 
        query, query, query
    );
    
    let mut stmt = conn.prepare(&sql).map_err(|e| e.to_string())?;
    
    let iter = stmt.query_map([], |row| {
        let is_banned_int: i64 = row.get(8).unwrap_or(0);
        let minutes_since_active: f64 = row.get(11).unwrap_or(9999.0);
        
        Ok(User {
            user_id: row.get(0)?,
            name: row.get(1).unwrap_or_default(),
            username: row.get(2).unwrap_or_default(),
            games_played: row.get(3).unwrap_or(0),
            wins: row.get(4).unwrap_or(0),
            coins: row.get(5).unwrap_or(0),
            title: row.get(6).unwrap_or_default(),
            last_chat_id: row.get(7).unwrap_or_default(),
            is_banned: is_banned_int > 0,
            ban_reason: row.get(9).unwrap_or_default(),
            ban_until: row.get(10).unwrap_or_default(),
            minutes_since_active,
        })
    }).map_err(|e| e.to_string())?;

    let mut users = Vec::new();
    for user in iter {
        if let Ok(u) = user {
            users.push(u);
        }
    }
    
    Ok(users)
}

#[tauri::command]
fn update_user(
    state: State<AppState>, 
    user_id: i64, 
    coins: i64, 
    title: String, 
    is_banned: bool, 
    ban_reason: String,
    ban_until: Option<f64>
) -> Result<(), String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    let is_banned_int = if is_banned { 1 } else { 0 };
    
    conn.execute(
        "UPDATE users SET coins = ?1, title = ?2, is_banned = ?3, ban_reason = ?4, ban_until = ?5 WHERE user_id = ?6",
        (coins, title, is_banned_int, ban_reason, ban_until, user_id),
    ).map_err(|e| e.to_string())?;
    
    Ok(())
}

#[tauri::command]
fn get_admins(state: State<AppState>) -> Result<Vec<Admin>, String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn.prepare("SELECT user_id, username, level, added_by, added_at FROM admins").map_err(|e| e.to_string())?;
    
    let iter = stmt.query_map([], |row| {
        Ok(Admin {
            user_id: row.get(0)?,
            username: row.get(1).unwrap_or_default(),
            level: row.get(2).unwrap_or(1),
            added_by: row.get(3).unwrap_or(0),
            added_at: row.get(4).unwrap_or_default(),
        })
    }).map_err(|e| e.to_string())?;

    let mut admins = Vec::new();
    for admin in iter {
        if let Ok(a) = admin {
            admins.push(a);
        }
    }
    
    Ok(admins)
}

#[tauri::command]
fn add_admin(state: State<AppState>, user_id: i64, username: String, level: i64) -> Result<(), String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO admins (user_id, username, level, added_by, added_at) VALUES (?1, ?2, ?3, 0, datetime('now')) ON CONFLICT(user_id) DO UPDATE SET level = ?3, username = ?2",
        (user_id, username, level),
    ).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn remove_admin(state: State<AppState>, user_id: i64) -> Result<(), String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM admins WHERE user_id = ?1", [user_id])
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn get_admin_logs(state: State<AppState>) -> Result<Vec<AdminLog>, String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn.prepare("SELECT id, admin_id, admin_name, action, target_user, target_chat, details, timestamp FROM admin_logs ORDER BY timestamp DESC LIMIT 100").map_err(|e| e.to_string())?;
    
    let iter = stmt.query_map([], |row| {
        Ok(AdminLog {
            id: row.get(0)?,
            admin_id: row.get(1).unwrap_or(0),
            admin_name: row.get(2).unwrap_or_default(),
            action: row.get(3).unwrap_or_default(),
            target_user: row.get(4).unwrap_or_default(),
            target_chat: row.get(5).unwrap_or(0),
            details: row.get(6).unwrap_or_default(),
            timestamp: row.get(7).unwrap_or_default(),
        })
    }).map_err(|e| e.to_string())?;

    let mut logs = Vec::new();
    for log in iter {
        if let Ok(l) = log {
            logs.push(l);
        }
    }
    
    Ok(logs)
}

#[tauri::command]
fn get_store_items(state: State<AppState>) -> Result<Vec<StoreItem>, String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn.prepare("SELECT id, name, description, price, item_type, value, is_active FROM items").map_err(|e| e.to_string())?;
    
    let iter = stmt.query_map([], |row| {
        let is_active_int: i64 = row.get(6).unwrap_or(1);
        Ok(StoreItem {
            id: row.get(0)?,
            name: row.get(1)?,
            description: row.get(2).unwrap_or_default(),
            price: row.get(3)?,
            item_type: row.get(4)?,
            value: row.get(5)?,
            is_active: is_active_int > 0,
        })
    }).map_err(|e| e.to_string())?;

    let mut items = Vec::new();
    for item in iter {
        if let Ok(i) = item {
            items.push(i);
        }
    }
    Ok(items)
}

#[tauri::command]
fn add_store_item(
    state: State<AppState>,
    name: String,
    description: String,
    price: i64,
    item_type: String,
    value: String,
    is_active: bool
) -> Result<(), String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    let is_active_int = if is_active { 1 } else { 0 };
    
    conn.execute(
        "INSERT INTO items (name, description, price, item_type, value, is_active) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        (name, description, price, item_type, value, is_active_int),
    ).map_err(|e| e.to_string())?;
    
    Ok(())
}

#[tauri::command]
fn update_store_item(
    state: State<AppState>,
    id: i64,
    name: String,
    description: String,
    price: i64,
    item_type: String,
    value: String,
    is_active: bool
) -> Result<(), String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    let is_active_int = if is_active { 1 } else { 0 };
    
    conn.execute(
        "UPDATE items SET name = ?1, description = ?2, price = ?3, item_type = ?4, value = ?5, is_active = ?6 WHERE id = ?7",
        (name, description, price, item_type, value, is_active_int, id),
    ).map_err(|e| e.to_string())?;
    
    Ok(())
}

#[tauri::command]
fn delete_store_item(state: State<AppState>, id: i64) -> Result<(), String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    // Cascade delete user_items manually to avoid foreign key errors
    conn.execute("DELETE FROM user_items WHERE item_id = ?1", [id]).ok();
    conn.execute("DELETE FROM items WHERE id = ?1", [id]).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn generate_chart(state: State<AppState>, chart_type: String) -> Result<String, String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    
    // Check if table exists and has data
    let mut stmt = conn.prepare("SELECT timestamp, total_users, total_coins, active_games FROM metrics_history ORDER BY id DESC LIMIT 20").map_err(|e| e.to_string())?;
    
    let mut x_data = Vec::new();
    let mut users_data = Vec::new();
    let mut coins_data = Vec::new();
    let mut games_data = Vec::new();
    
    let iter = stmt.query_map([], |row| {
        let ts: String = row.get(0)?;
        let time_part = ts.split(' ').last().unwrap_or(&ts).to_string();
        
        let users: i64 = row.get(1)?;
        let coins: i64 = row.get(2)?;
        let games: i64 = row.get(3)?;
        
        Ok((time_part, users as f64, coins as f64, games as f64))
    }).map_err(|e| e.to_string())?;
    
    let mut results = Vec::new();
    for row in iter {
        if let Ok(r) = row {
            results.push(r);
        }
    }
    
    // Reverse to get chronological order
    results.reverse();
    
    // Ensure we have exactly 20 points by padding the beginning with the earliest known value (or 0)
    let target_len = 20;
    if results.is_empty() {
        for i in 0..target_len {
            results.push((format!("T-{}", target_len - i), 0.0, 0.0, 0.0));
        }
    } else if results.len() < target_len {
        let first = results[0].clone();
        let diff = target_len - results.len();
        let mut padded = Vec::new();
        for i in 0..diff {
            padded.push((format!("T-{}", diff - i), first.1, first.2, first.3));
        }
        padded.extend(results);
        results = padded;
    }
    
    for (t, u, c, g) in results {
        x_data.push(t);
        users_data.push(u);
        coins_data.push(c);
        games_data.push(g);
    }
    
    let output_path = "/tmp/tg_bot_dashboard_chart.png";
    let mut series = Vec::new();
    
    if chart_type == "economy" {
        series.push(plotter::Series {
            name: "Total Coins".to_string(),
            data: coins_data,
            style: plotter::SeriesStyling {
                color: "#a371f7".to_string(),
                thickness: 3,
            },
        });
    } else if chart_type == "games" {
        series.push(plotter::Series {
            name: "Active Games".to_string(),
            data: games_data,
            style: plotter::SeriesStyling {
                color: "#58a6ff".to_string(),
                thickness: 3,
            },
        });
    } else {
        series.push(plotter::Series {
            name: "Total Users".to_string(),
            data: users_data,
            style: plotter::SeriesStyling {
                color: "#3fb950".to_string(),
                thickness: 3,
            },
        });
    }
    
    let plot_config = plotter::PlotConfig {
        x_label: format!("Bot Analytics ({})", chart_type),
        x_data,
        series,
        bg_color: "#0d1117".to_string(),
        output_path: output_path.to_string(),
    };
    
    plotter::generate_plot(&plot_config).map_err(|e| e.to_string())?;
    
    let image_data = fs::read(output_path).map_err(|e| format!("Failed to read generated image: {}", e))?;
    let base64_img = BASE64.encode(image_data);
    
    Ok(format!("data:image/png;base64,{}", base64_img))
}

#[tauri::command]
fn get_reports(state: State<AppState>) -> Result<Vec<Report>, String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn.prepare("SELECT id, sender_id, sender_name, target_id, reason, status, created_at FROM reports ORDER BY id DESC").map_err(|e| e.to_string())?;
    
    let iter = stmt.query_map([], |row| {
        Ok(Report {
            id: row.get(0)?,
            sender_id: row.get(1)?,
            sender_name: row.get(2).unwrap_or_default(),
            target_id: row.get(3).unwrap_or(None),
            reason: row.get(4)?,
            status: row.get(5)?,
            created_at: row.get(6)?,
        })
    }).map_err(|e| e.to_string())?;

    let mut reports = Vec::new();
    for r in iter {
        if let Ok(report) = r {
            reports.push(report);
        }
    }
    
    Ok(reports)
}

#[tauri::command]
fn resolve_report(state: State<AppState>, id: i64, status: String) -> Result<(), String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    conn.execute("UPDATE reports SET status = ?1 WHERE id = ?2", (status, id))
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn create_broadcast(state: State<AppState>, text: String, image_path: Option<String>) -> Result<(), String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO broadcast_tasks (message_text, image_path, status) VALUES (?1, ?2, 'pending')",
        (text, image_path)
    ).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn get_settings(state: State<AppState>) -> Result<Vec<Setting>, String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn.prepare("SELECT key, value FROM bot_settings").map_err(|e| e.to_string())?;
    
    let iter = stmt.query_map([], |row| {
        Ok(Setting {
            key: row.get(0)?,
            value: row.get(1)?,
        })
    }).map_err(|e| e.to_string())?;

    let mut settings = Vec::new();
    for s in iter {
        if let Ok(setting) = s {
            settings.push(setting);
        }
    }
    
    Ok(settings)
}

#[tauri::command]
fn update_setting(state: State<AppState>, key: String, value: String) -> Result<(), String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO bot_settings (key, value) VALUES (?1, ?2) ON CONFLICT(key) DO UPDATE SET value = ?2",
        (key, value)
    ).map_err(|e| e.to_string())?;
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let _ = dotenv();
    
    // Автозапуск только API, если порт 8000 закрыт
    if let Ok(addr) = "127.0.0.1:8000".parse::<std::net::SocketAddr>() {
        if std::net::TcpStream::connect_timeout(&addr, std::time::Duration::from_millis(300)).is_err() {
            let uvicorn_cmd = if std::path::Path::new(".venv/bin/uvicorn").exists() {
                ".venv/bin/uvicorn".to_string()
            } else if std::path::Path::new("../.venv/bin/uvicorn").exists() {
                "../.venv/bin/uvicorn".to_string()
            } else if std::path::Path::new("../../.venv/bin/uvicorn").exists() {
                "../../.venv/bin/uvicorn".to_string()
            } else {
                "uvicorn".to_string()
            };

            let api_dir = if std::path::Path::new("bot-api").exists() {
                "bot-api".to_string()
            } else if std::path::Path::new("../bot-api").exists() {
                "../bot-api".to_string()
            } else if std::path::Path::new("../../bot-api").exists() {
                "../../bot-api".to_string()
            } else {
                ".".to_string()
            };

            let _ = std::process::Command::new(uvicorn_cmd)
                .args(["main:app", "--host", "0.0.0.0", "--port", "8000"])
                .current_dir(api_dir)
                .spawn();
        }
    }

    let db_path = std::env::var("DB_PATH").unwrap_or_else(|_| {
        if std::path::Path::new("bot/game.db").exists() {
            "bot/game.db".to_string()
        } else if std::path::Path::new("../bot/game.db").exists() {
            "../bot/game.db".to_string()
        } else if std::path::Path::new("../../bot/game.db").exists() {
            "../../bot/game.db".to_string()
        } else {
            "game.db".to_string()
        }
    });
    
    // Create parent directories if they do not exist
    if let Some(parent) = std::path::Path::new(&db_path).parent() {
        if !parent.exists() {
            std::fs::create_dir_all(parent).expect("Failed to create DB parent directories");
        }
    }
    
    let conn = Connection::open(&db_path).expect("Failed to open DB");
    conn.execute_batch("PRAGMA journal_mode=WAL;").expect("Failed to enable WAL mode");
    
    // Attempt to create tables if they don't exist (useful for testing or first run)
    let _ = conn.execute_batch("
        CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, username TEXT DEFAULT '', games_played INTEGER, wins INTEGER, coins INTEGER, title TEXT, last_chat_id INTEGER, is_banned INTEGER, ban_reason TEXT, ban_until REAL);
        
        -- Safe way to add columns if they don't exist
        ALTER TABLE users ADD COLUMN last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE users ADD COLUMN ban_until REAL;
        
        CREATE TABLE IF NOT EXISTS games (chat_id INTEGER PRIMARY KEY, players TEXT, game_type TEXT, game_state TEXT, state TEXT);
        CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, username TEXT, level INTEGER, added_by INTEGER, added_at TIMESTAMP);
        CREATE TABLE IF NOT EXISTS admin_logs (id INTEGER PRIMARY KEY, admin_id INTEGER, admin_name TEXT, action TEXT, target_user TEXT, target_chat INTEGER, details TEXT, timestamp TIMESTAMP);
        CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT, price INTEGER NOT NULL, item_type TEXT NOT NULL, value TEXT NOT NULL, is_active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS user_items (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, item_id INTEGER NOT NULL, purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(user_id), FOREIGN KEY(item_id) REFERENCES items(id));
        CREATE TABLE IF NOT EXISTS metrics_history (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, total_users INTEGER DEFAULT 0, total_coins INTEGER DEFAULT 0, active_games INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER NOT NULL, sender_name TEXT, target_id INTEGER, reason TEXT NOT NULL, status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS broadcast_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, message_text TEXT NOT NULL, image_path TEXT, status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        
        INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('maintenance_mode', 'false');
        INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('welcome_bonus_amount', '100');
        INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('max_games_per_user', '5');
    ");

    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(AppState {
            db: Mutex::new(conn),
        })
        .invoke_handler(tauri::generate_handler![
            get_dashboard_stats,
            get_games,
            delete_game,
            get_users,
            update_user,
            get_admins,
            add_admin,
            remove_admin,
            get_admin_logs,
            get_store_items,
            add_store_item,
            update_store_item,
            delete_store_item,
            generate_chart,
            get_reports,
            resolve_report,
            create_broadcast,
            get_settings,
            update_setting
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
