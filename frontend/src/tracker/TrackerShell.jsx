import { useEffect, useMemo, useState } from "react";

const FLOW_OPTIONS = [
  {
    label: "Light",
    description:
      "Light menstrual flow means there is less bleeding than usual. It may occur at the beginning or end of a period or due to hormonal changes. In most cases, it is normal, but it should be tracked regularly to observe any changes over time.",
  },
  {
    label: "Normal",
    description:
      "Normal menstrual flow indicates a healthy and regular pattern of bleeding. It usually lasts between 3 to 7 days and does not require very frequent pad changes. This is considered a sign of a well-functioning menstrual cycle.",
  },
  {
    label: "Heavy",
    description:
      "Heavy menstrual flow means excessive bleeding, where pads or tampons need to be changed very frequently, sometimes every 1 to 2 hours. This may be due to hormonal imbalance or other health conditions. If it continues for several cycles, medical consultation is recommended.",
  },
];
const DISCHARGE_OPTIONS = [
  { label: "Clear", tone: "tracker-discharge-clear", description: "Clear and watery discharge is commonly seen around ovulation and often reflects healthy vaginal function." },
  { label: "Thick White", tone: "tracker-discharge-white", description: "White, thick discharge can be normal, but if itching or discomfort is present it may suggest a yeast infection." },
  { label: "Creamy", tone: "tracker-discharge-creamy", description: "Creamy discharge often appears with normal hormonal changes during different parts of the cycle." },
  { label: "Yellow/Brown/Pink", tone: "tracker-discharge-color", description: "Yellow, brown, or pink discharge may happen with spotting or irritation. If it continues, it is better to monitor and consult a doctor." },
  { label: "Cottage Cheese", tone: "tracker-discharge-alert", description: "Cottage-cheese-like discharge is commonly associated with yeast infection, especially when itching is also present." },
];
const STORAGE_KEY = "ovacare_tracker_user_id";

async function apiRequest(apiBaseUrl, path, options = {}) {
  const response = await fetch(`${apiBaseUrl}${path}`, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }
  return data;
}

function SetupModal({ open, onClose, profileForm, onChange, onSubmit, savingProfile, needsSetup }) {
  if (!open) {
    return null;
  }

  return (
    <div className="tracker-modal-overlay" onClick={onClose}>
      <div className="tracker-modal" onClick={(event) => event.stopPropagation()}>
        <div className="tracker-modal-head">
          <div>
            <p className="section-kicker">Profile Setup</p>
            <h2>Cycle Information</h2>
          </div>
          <button className="secondary-button tracker-close-button" type="button" onClick={onClose}>Close</button>
        </div>
        <form className="predict-form" onSubmit={onSubmit}>
          <div className="form-grid">
            <label className="field"><span>Name</span><input name="name" value={profileForm.name} onChange={onChange} placeholder="Enter your name" required /></label>
            <label className="field"><span>Height (cm)</span><input name="height" type="number" step="any" value={profileForm.height} onChange={onChange} placeholder="Enter height" required /></label>
            <label className="field"><span>Weight (kg)</span><input name="weight" type="number" step="any" value={profileForm.weight} onChange={onChange} placeholder="Enter weight" required /></label>
            <label className="field"><span>Cycle length</span><input name="cycle_length" type="number" value={profileForm.cycle_length} onChange={onChange} placeholder="28" required /></label>
            <label className="field"><span>Menstrual flow duration (days)</span><input name="flow_duration_days" type="number" value={profileForm.flow_duration_days} onChange={onChange} placeholder="Enter number of days" required /></label>
            <label className="field tracker-span-two"><span>Last period date</span><input name="last_period_date" type="date" value={profileForm.last_period_date} onChange={onChange} required /></label>
          </div>
          <button className="primary-button tracker-span-two" type="submit" disabled={savingProfile}>{savingProfile ? "Saving..." : needsSetup ? "Save Profile & Cycle" : "Update Profile & Cycle"}</button>
        </form>
      </div>
    </div>
  );
}

export default function MenstrualTrackerShell({ apiBaseUrl, onBack }) {
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({ name: "", email: "", password: "" });
  const [profileForm, setProfileForm] = useState({
    name: "",
    height: "",
    weight: "",
    cycle_length: 28,
    flow_duration_days: "",
    last_period_date: "",
  });
  const [periodStartDate, setPeriodStartDate] = useState("");
  const [symptomForm, setSymptomForm] = useState({ flow: "Normal", discharge: "Clear" });
  const [userId, setUserId] = useState(() => localStorage.getItem(STORAGE_KEY) || "");
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [trackingPeriod, setTrackingPeriod] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showSetupModal, setShowSetupModal] = useState(false);
  const [selectedHistoryEntry, setSelectedHistoryEntry] = useState(null);

  const needsSetup = useMemo(() => !dashboard?.profile?.last_period_date, [dashboard]);

  const getSuggestedPeriodStartDate = (data) => {
    return data?.cycle_summary?.next_period_date || data?.profile?.last_period_date || "";
  };

  const getCycleOverviewText = () => {
    const nextPeriod = dashboard?.cycle_summary?.next_period_date;
    if (!nextPeriod) {
      return "Save your cycle details to see your next prediction.";
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const nextDate = new Date(`${nextPeriod}T00:00:00`);
    if (Number.isNaN(nextDate.getTime())) {
      return "Your next cycle date is ready.";
    }

    const diffMs = nextDate.getTime() - today.getTime();
    const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays > 1) {
      return `Next period in ${diffDays} days`;
    }
    if (diffDays == 1) {
      return "Next period is tomorrow";
    }
    if (diffDays == 0) {
      return "Next period is expected today";
    }
    if (diffDays == -1) {
      return "Your predicted period date was yesterday";
    }
    return `Your predicted period date was ${Math.abs(diffDays)} days ago`;
  };

  const getCycleProgressPercent = () => {
    const lastPeriod = dashboard?.cycle_summary?.last_period_date;
    const cycleLength = Number(dashboard?.cycle_summary?.cycle_length || 0);
    if (!lastPeriod || !cycleLength) {
      return 0;
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const lastDate = new Date(`${lastPeriod}T00:00:00`);
    if (Number.isNaN(lastDate.getTime())) {
      return 0;
    }

    const elapsedDays = Math.max(0, Math.round((today.getTime() - lastDate.getTime()) / (1000 * 60 * 60 * 24)));
    const rawPercent = (elapsedDays / cycleLength) * 100;
    return Math.min(100, Math.max(6, Math.round(rawPercent)));
  };

  const getCyclePatternStatus = () => {
    const history = (dashboard?.cycle_history || [])
      .map((entry) => Number(entry?.cycle_length || 0))
      .filter((value) => Number.isFinite(value) && value > 0)
      .slice(-5);

    if (history.length < 2) {
      return { label: "Tracking", detail: "Need more cycles to confirm pattern" };
    }

    const minLength = Math.min(...history);
    const maxLength = Math.max(...history);
    const variation = maxLength - minLength;

    if (variation <= 5) {
      return { label: "Regular", detail: `Cycle variation is about ${variation} days` };
    }

    return { label: "Irregular", detail: `Cycle variation is about ${variation} days` };
  };

  const getBmiDetails = () => {
    const heightCm = Number(dashboard?.profile?.height || 0);
    const weightKg = Number(dashboard?.profile?.weight || 0);
    if (!heightCm || !weightKg) {
      return { value: null, label: "Not available" };
    }

    const heightM = heightCm / 100;
    const bmi = weightKg / (heightM * heightM);
    const roundedBmi = Number(bmi.toFixed(1));

    if (roundedBmi < 18.5) {
      return { value: roundedBmi, label: "Underweight" };
    }
    if (roundedBmi < 25) {
      return { value: roundedBmi, label: "Healthy Weight" };
    }
    if (roundedBmi < 30) {
      return { value: roundedBmi, label: "Overweight" };
    }
    return { value: roundedBmi, label: "Obesity" };
  };

  useEffect(() => {
    if (!userId) {
      setDashboard(null);
      return;
    }

    let active = true;
    setLoading(true);
    setError("");

    apiRequest(apiBaseUrl, `/tracker/dashboard/${userId}`)
      .then((data) => {
        if (!active) {
          return;
        }
        setDashboard(data);
        setProfileForm({
          name: data.profile?.name || data.name || "",
          height: data.profile?.height || "",
          weight: data.profile?.weight || "",
          cycle_length: data.profile?.cycle_length || 28,
          flow_duration_days: data.profile?.flow_duration_days || "",
          last_period_date: data.profile?.last_period_date || "",
        });
        setPeriodStartDate(getSuggestedPeriodStartDate(data));
        setShowSetupModal(!data.profile?.last_period_date);
      })
      .catch((requestError) => {
        if (!active) {
          return;
        }
        setError(requestError.message);
        localStorage.removeItem(STORAGE_KEY);
        setUserId("");
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [apiBaseUrl, userId]);

  const handleAuthChange = (event) => {
    const { name, value } = event.target;
    setAuthForm((current) => ({ ...current, [name]: value }));
  };

  const handleProfileChange = (event) => {
    const { name, value } = event.target;
    setProfileForm((current) => ({ ...current, [name]: value }));
  };

  const handleAuthSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const path = authMode === "signup" ? "/tracker/signup" : "/tracker/login";
      const payload = { email: authForm.email, password: authForm.password };
      if (authMode === "signup") {
        payload.name = authForm.name;
      }

      const data = await apiRequest(apiBaseUrl, path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      localStorage.setItem(STORAGE_KEY, data.user_id);
      setUserId(data.user_id);
      setDashboard(data);
      setProfileForm({
        name: data.profile?.name || data.name || authForm.name || "",
        height: data.profile?.height || "",
        weight: data.profile?.weight || "",
        cycle_length: data.profile?.cycle_length || 28,
        flow_duration_days: data.profile?.flow_duration_days || "",
        last_period_date: data.profile?.last_period_date || "",
      });
      setPeriodStartDate(getSuggestedPeriodStartDate(data));
      setSuccess(authMode === "signup" ? "Account created successfully." : "Logged in successfully.");
      setShowSetupModal(!data.profile?.last_period_date);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  const handleProfileSubmit = async (event) => {
    event.preventDefault();
    setSavingProfile(true);
    setError("");
    setSuccess("");

    try {
      const data = await apiRequest(apiBaseUrl, `/tracker/profile/${userId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: profileForm.name,
          height: Number(profileForm.height),
          weight: Number(profileForm.weight),
          cycle_length: Number(profileForm.cycle_length || 28),
          flow_duration_days: Number(profileForm.flow_duration_days || 0),
          last_period_date: profileForm.last_period_date,
        }),
      });
      setDashboard(data);
      setPeriodStartDate(getSuggestedPeriodStartDate(data));
      setSuccess("Profile and cycle setup saved.");
      setShowSetupModal(false);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSavingProfile(false);
    }
  };

  const handlePeriodStarted = async () => {
    setTrackingPeriod(true);
    setError("");
    setSuccess("");

    try {
      const data = await apiRequest(apiBaseUrl, `/tracker/period-started/${userId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ period_start_date: periodStartDate }),
      });
      setDashboard(data);
      setSuccess("Period start recorded and cycle recalculated.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setTrackingPeriod(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setUserId("");
    setDashboard(null);
    setSuccess("");
    setError("");
    setShowSetupModal(false);
  };

  if (!userId) {
    return (
      <div>
        <header className="site-header">
          <div className="brand-wrap">
            <div className="brand-logo" aria-hidden="true">
              <span className="brand-logo-core" />
              <span className="brand-logo-leaf brand-logo-leaf-one" />
              <span className="brand-logo-leaf brand-logo-leaf-two" />
            </div>
            <div className="brand-mark">OvaCare</div>
          </div>
          <div className="header-cta-wrap">
            <button className="back-link" type="button" onClick={onBack}>Back to Home</button>
          </div>
        </header>

        <div className="auth-page-shell">
          <div className="predict-card auth-card">
            <div className="predict-topbar">
              <p className="predict-badge">Menstrual Tracker</p>
            </div>

          <div className="predict-header">
            <p className="section-kicker">Access Required</p>
            <h1>{authMode === "signup" ? "Create Your Account" : "Login to Continue"}</h1>
            <p>Login to access your personal menstrual tracking dashboard and cycle insights.</p>
          </div>

          <form className="predict-form" onSubmit={handleAuthSubmit}>
            <div className="form-grid">
              {authMode === "signup" ? <label className="field"><span>Name</span><input name="name" value={authForm.name} onChange={handleAuthChange} placeholder="Enter your name" required /></label> : null}
              <label className="field"><span>Email</span><input name="email" type="email" value={authForm.email} onChange={handleAuthChange} placeholder="Enter your email" required /></label>
              <label className="field"><span>Password</span><input name="password" type="password" value={authForm.password} onChange={handleAuthChange} placeholder="Enter your password" required /></label>
            </div>
            <button className="primary-button" type="submit" disabled={loading}>{loading ? "Please wait..." : authMode === "signup" ? "Create Account" : "Login"}</button>
          </form>

          <div className="predict-actions">
            <button className="secondary-button" type="button" onClick={() => setAuthMode((current) => current === "login" ? "signup" : "login")}>{authMode === "login" ? "Need a new account? Create one" : "Already have an account? Login"}</button>
          </div>

          {error ? <p className="error-text">{error}</p> : null}
          {success ? <p className="tracker-success">{success}</p> : null}
        </div>
      </div>
    </div>
  );
}

return (
    <div>
      <header className="site-header">
        <div className="brand-wrap">
          <div className="brand-logo" aria-hidden="true">
            <span className="brand-logo-core" />
            <span className="brand-logo-leaf brand-logo-leaf-one" />
            <span className="brand-logo-leaf brand-logo-leaf-two" />
          </div>
          <div>
            <div className="brand-mark">OvaCare</div>
            <p className="welcome-message">{dashboard?.name ? `Welcome back, ${dashboard.name}` : "Menstrual tracker"}</p>
          </div>
        </div>
        <div className="header-cta-wrap">
          <button className="secondary-button" type="button" onClick={() => setShowSetupModal(true)}>Edit Cycle</button>
          <button className="secondary-button" type="button" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <div className="predict-page-shell">
        <div className="predict-card">
        <div className="predict-topbar">
          <button className="back-link" type="button" onClick={onBack}>Back to Home</button>
          <p className="predict-badge">Menstrual Tracker</p>
        </div>

        {error ? <p className="error-text tracker-message">{error}</p> : null}
        {success ? <p className="tracker-success">{success}</p> : null}

        <div className="tracker-dashboard-grid">
          <div className="tracker-dashboard-main">
            <section className="soft-card tracker-current-cycle-card">
              <div className="tracker-current-cycle-info">
                <h3>Current Cycle Overview</h3>
                <div className="tracker-metric-list">
                  <div><span>Last Period</span><strong>{dashboard?.cycle_summary?.last_period_date || "-"}</strong></div>
                  <div><span>Next Period</span><strong>{dashboard?.cycle_summary?.next_period_date || "-"}</strong></div>
                  <div><span>Cycle Length</span><strong>{dashboard?.cycle_summary?.cycle_length ? `${dashboard.cycle_summary.cycle_length} Days` : "-"}</strong></div>
                  <div><span>Flow Days</span><strong>{dashboard?.profile?.flow_duration_days ? `${dashboard.profile.flow_duration_days} Days` : "-"}</strong></div>
                  <div><span>Status</span><strong>{getCyclePatternStatus().label}</strong></div>
                  <div><span>BMI</span><strong>{getBmiDetails().value ? `${getBmiDetails().value}` : "-"}</strong></div>
                </div>
                <div className="tracker-progress-copy">{getCycleOverviewText()}</div>
                <div className="tracker-status-note">{getCyclePatternStatus().detail}</div>
                <div className="tracker-bmi-note">BMI status: {getBmiDetails().label}</div>
                <div className="tracker-progress-bar"><span style={{ width: `${getCycleProgressPercent()}%` }} /></div>
              </div>
              <div className="tracker-cycle-illustration">
                <div className="tracker-mascot-card">28</div>
              </div>
            </section>

            <div className="tracker-card-row">
              <section className="soft-card tracker-choice-card">
                <h3>Menstrual Flow</h3>
                <p>Select the flow level that best matches your current cycle.</p>
                <div className="tracker-choice-grid tracker-flow-grid">
                  {FLOW_OPTIONS.map((option) => (
                    <button
                      key={option.label}
                      type="button"
                      className={`tracker-choice-pill ${symptomForm.flow === option.label ? "tracker-choice-pill-active" : ""}`}
                      onClick={() => setSymptomForm((current) => ({ ...current, flow: option.label }))}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
                <div className="tracker-discharge-detail tracker-flow-detail">
                  <strong>{symptomForm.flow}</strong>
                  <p>{FLOW_OPTIONS.find((option) => option.label === symptomForm.flow)?.description}</p>
                </div>
              </section>

              <section className="soft-card tracker-choice-card">
                <h3>Vaginal Discharge</h3>
                <p>Choose the discharge type to view a simple explanation below.</p>
                <div className="tracker-choice-grid tracker-discharge-grid">
                  {DISCHARGE_OPTIONS.map((option) => (
                    <button
                      key={option.label}
                      type="button"
                      className={`tracker-choice-pill tracker-discharge-pill ${option.tone} ${symptomForm.discharge === option.label ? "tracker-choice-pill-active" : ""}`}
                      onClick={() => setSymptomForm((current) => ({ ...current, discharge: option.label }))}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
                <div className="tracker-discharge-detail">
                  <strong>{symptomForm.discharge}</strong>
                  <p>{DISCHARGE_OPTIONS.find((option) => option.label === symptomForm.discharge)?.description}</p>
                </div>
              </section>
            </div>

            <div className="tracker-card-row tracker-card-row-secondary">
              <section className="soft-card tracker-fertility-card">
                <div className="tracker-card-head-row">
                  <h3>Fertility Insights</h3>
                  <p>These dates are predicted from the last period date you entered during setup. If your period starts on a different date than the predicted next period date, change it below and save it.</p>
                </div>
                <div className="tracker-calendar-mini">
                  <div><span>Ovulation</span><strong>{dashboard?.cycle_summary?.ovulation_date || "-"}</strong></div>
                  <div><span>Fertile Window</span><strong>{dashboard?.cycle_summary?.fertile_window?.start || "-"}</strong></div>
                  <div><span>Next Period Date</span><strong>{dashboard?.cycle_summary?.next_period_date || "-"}</strong></div>
                </div>
                <label className="field">
                  <span>Change only if your period actually started on a different date</span>
                  <input type="date" value={periodStartDate} onChange={(event) => setPeriodStartDate(event.target.value)} />
                </label>
                <button className="primary-button tracker-period-button" type="button" onClick={handlePeriodStarted} disabled={trackingPeriod || !periodStartDate}>
                  {trackingPeriod ? "Saving..." : "Period Started"}
                </button>
              </section>

              <section className="soft-card tracker-fertility-card tracker-care-card">
                <div className="tracker-card-head-row">
                  <h3>Cycle Care Tips</h3>
                  <p>Simple everyday reminders to stay comfortable and take better care during your cycle.</p>
                </div>
                <ul className="tracker-care-list">
                  <li>Stay hydrated during your cycle.</li>
                  <li>Sleep 7 to 8 hours each night.</li>
                  <li>Track flow and dates regularly.</li>
                  <li>Use a warm pad if cramps occur.</li>
                  <li>Consult a doctor if flow becomes too heavy or irregular.</li>
                </ul>
              </section>
            </div>

            <section className="soft-card tracker-history-strip">
              <div className="tracker-card-head-row">
                <h3>Recent History</h3>
                <p>Showing the latest 5 period entries.</p>
              </div>
              <div className="tracker-history-grid">
                {(dashboard?.cycle_history || []).slice(-5).reverse().map((entry, index) => (
                  <button key={`${entry.period_start}-${index}`} type="button" className="tracker-history-card" onClick={() => setSelectedHistoryEntry(entry)}>
                    <strong>{entry.period_start}</strong>
                    <span>{entry.cycle_length} days cycle</span>
                    <span>{entry.flow_duration_days || "-"} days flow</span>
                  </button>
                ))}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>

      {selectedHistoryEntry ? (
        <div className="tracker-modal-overlay" onClick={() => setSelectedHistoryEntry(null)}>
          <div className="tracker-modal" onClick={(event) => event.stopPropagation()}>
            <div className="tracker-modal-head">
              <div>
                <p className="section-kicker">History Detail</p>
                <h2>{selectedHistoryEntry.period_start}</h2>
              </div>
              <button className="secondary-button tracker-close-button" type="button" onClick={() => setSelectedHistoryEntry(null)}>Close</button>
            </div>
            <div className="tracker-two-column">
              <div className="tracker-insight-box"><strong>Period start</strong><p>{selectedHistoryEntry.period_start}</p></div>
              <div className="tracker-insight-box"><strong>Cycle length</strong><p>{selectedHistoryEntry.cycle_length} days</p></div>
              <div className="tracker-insight-box"><strong>Flow duration</strong><p>{selectedHistoryEntry.flow_duration_days || "-"} days</p></div>
              <div className="tracker-insight-box"><strong>Saved from</strong><p>{selectedHistoryEntry.source}</p></div>
            </div>
          </div>
        </div>
      ) : null}

      <SetupModal
        open={showSetupModal}
        onClose={() => setShowSetupModal(false)}
        profileForm={profileForm}
        onChange={handleProfileChange}
        onSubmit={handleProfileSubmit}
        savingProfile={savingProfile}
        needsSetup={needsSetup}
      />
    </div>
  );
}
