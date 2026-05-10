import { useState, useEffect, useCallback } from "react";
import styles from "./styles";

const API_BASE = "http://localhost:8000";

// ─── API helpers ─────────────────────────────────────────────────────────────

async function apiLogin(username, password) {
  const res = await fetch(`${API_BASE}/users/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Login failed");
  return data;
}

async function apiGetSlots(lotId, token) {
  const res = await fetch(`${API_BASE}/slots/${lotId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to fetch slots");
  return data;
}

// ─── Fixed slot layout ───────────────────────────────────────────────────────

const ROW_A = ["A1","A2","A3","A4","A5","A6","A7","A8","A9","A10"];
const ROW_B = ["B1","B2","B3","B4","B5","B6","B7","B8","B9","B10"];

// ─── Login Screen ─────────────────────────────────────────────────────────────

function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await apiLogin(username, password);
      onLogin(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.loginPage}>
      <div style={styles.loginCard}>
        <div style={styles.loginHeader}>
          <span style={styles.loginIcon}>🅿️</span>
          <h1 style={styles.loginTitle}>Smart Parking</h1>
          <p style={styles.loginSubtitle}>Parking Management System</p>
        </div>
        <form onSubmit={handleSubmit} style={styles.loginForm}>
          <div style={styles.inputGroup}>
            <label style={styles.label}>Username</label>
            <input
              style={styles.input}
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              required
              autoFocus
            />
          </div>
          <div style={styles.inputGroup}>
            <label style={styles.label}>Password</label>
            <input
              style={styles.input}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
            />
          </div>
          {error && <div style={styles.errorBox}>{error}</div>}
          <button
            type="submit"
            style={{ ...styles.loginBtn, opacity: loading ? 0.7 : 1 }}
            disabled={loading}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}

// ─── Slot Card ────────────────────────────────────────────────────────────────

function SlotCard({ slotNumber, status }) {
  const [localStatus, setLocalStatus] = useState(status);

  useEffect(() => {
    setLocalStatus(status);
  }, [status]);

  const isFree = localStatus === "free";
  const isUnknown = localStatus === "unknown";

  function handleToggle() {
    if (isUnknown) return;
    setLocalStatus(isFree ? "occupied" : "free");
  }

  return (
    <div
      style={{
        ...styles.slotCard,
        ...(isUnknown ? styles.slotUnknown : isFree ? styles.slotFree : styles.slotOccupied),
        cursor: isUnknown ? "default" : "pointer",
      }}
      onClick={handleToggle}
      title={isUnknown ? "" : "Click to toggle"}
    >
      <div style={styles.slotNumber}>{slotNumber}</div>
      <div style={styles.slotStatusText}>
        {isUnknown ? "—" : isFree ? "FREE" : "OCCUPIED"}
      </div>
    </div>
  );
}

// ─── Dashboard Screen ─────────────────────────────────────────────────────────

function DashboardScreen({ auth, onLogout }) {
  const [slotMap, setSlotMap] = useState({});
  const [lotData, setLotData] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [error, setError] = useState("");

  const fetchSlots = useCallback(async () => {
    try {
      const data = await apiGetSlots(auth.lot_id, auth.access_token);
      setLotData(data);
      // Build a map: { "A1": "free", "B3": "occupied", ... }
      const map = {};
      for (const slot of data.slots) {
        map[slot.slot_number] = slot.status;
      }
      setSlotMap(map);
      setLastUpdated(new Date());
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, [auth]);

  useEffect(() => {
    fetchSlots();
    const interval = setInterval(fetchSlots, 10000);
    return () => clearInterval(interval);
  }, [fetchSlots]);

  const free = lotData?.free ?? 0;
  const occupied = lotData?.occupied ?? 0;
  const total = lotData?.total_slots ?? 0;

  return (
    <div style={styles.dashPage}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.headerIcon}>🅿️</span>
          <div>
            <div style={styles.headerTitle}>Smart Parking</div>
            <div style={styles.headerSub}>{lotData?.lot_name || "Loading..."}</div>
          </div>
        </div>
        <div style={styles.headerRight}>
          <div style={styles.statsInline}>
            <span style={styles.statBadgeFree}>🟢 {free} Free</span>
            <span style={styles.statBadgeOccupied}>🔴 {occupied} Occupied</span>
            <span style={styles.statBadgeTotal}>Total: {total}</span>
          </div>
          <span style={styles.headerUser}>👤 {auth.username}</span>
          <button style={styles.logoutBtn} onClick={onLogout}>Logout</button>
        </div>
      </div>

      {error && <div style={styles.errorBox}>⚠️ {error}</div>}

      {/* Parking Grid */}
      <div style={styles.parkingArea}>
        {/* Row A */}
        <div style={styles.rowLabel}>Row A</div>
        <div style={styles.slotRow}>
          {ROW_A.map((id) => (
            <SlotCard key={id} slotNumber={id} status={slotMap[id] ?? "free"} />
          ))}
        </div>

        {/* Divider — road between rows */}
        <div style={styles.roadDivider}>
          <span style={styles.roadLabel}>← ENTRANCE / EXIT →</span>
        </div>

        {/* Row B */}
        <div style={styles.rowLabel}>Row B</div>
        <div style={styles.slotRow}>
          {ROW_B.map((id) => (
            <SlotCard key={id} slotNumber={id} status={slotMap[id] ?? "free"} />
          ))}
        </div>
      </div>

      {/* Footer */}
      <div style={styles.footer}>
        <div style={styles.legend}>
          <span style={styles.legendFree}>🟢 Free</span>
          <span style={styles.legendOccupied}>🔴 Occupied</span>
          <span style={styles.legendUnknown}>⬜ No data</span>
        </div>
        {lastUpdated && (
          <div style={styles.lastUpdated}>
            Last updated: {lastUpdated.toLocaleTimeString()} · Auto-refreshes every 10s
          </div>
        )}
        <button style={styles.refreshBtn} onClick={fetchSlots}>🔄 Refresh</button>
      </div>
    </div>
  );
}

// ─── App Root ─────────────────────────────────────────────────────────────────

export default function App() {
  const [auth, setAuth] = useState(() => {
    const saved = sessionStorage.getItem("parking_auth");
    return saved ? JSON.parse(saved) : null;
  });

  function handleLogin(data) {
    sessionStorage.setItem("parking_auth", JSON.stringify(data));
    setAuth(data);
  }

  function handleLogout() {
    sessionStorage.removeItem("parking_auth");
    setAuth(null);
  }

  if (!auth) return <LoginScreen onLogin={handleLogin} />;
  return <DashboardScreen auth={auth} onLogout={handleLogout} />;
}