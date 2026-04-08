import { useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");

const initialStage1Form = {
  age: "",
  weight: "",
  bmi: "",
  cycle_ri: "",
  cycle_length: "",
  weight_gain: "",
  hair_growth: "",
  skin_darkening: "",
  hair_loss: "",
  pimples: "",
  fast_food: "",
  reg_exercise: "",
};

const stage1Fields = [
  { name: "age", label: "Age (yrs)", type: "number", step: "any" },
  { name: "weight", label: "Weight (Kg)", type: "number", step: "any" },
  { name: "bmi", label: "BMI", type: "number", step: "any" },
  {
    name: "cycle_ri",
    label: "Cycle Type",
    type: "select",
    options: [
      { label: "Regular", value: 2 },
      { label: "Irregular", value: 4 },
    ],
  },
  { name: "cycle_length", label: "Cycle Length (days)", type: "number", step: "any" },
  { name: "weight_gain", label: "Weight Gain", type: "select" },
  { name: "hair_growth", label: "Hair Growth", type: "select" },
  { name: "skin_darkening", label: "Skin Darkening", type: "select" },
  { name: "hair_loss", label: "Hair Loss", type: "select" },
  { name: "pimples", label: "Pimples", type: "select" },
  { name: "fast_food", label: "Fast Food", type: "select" },
  { name: "reg_exercise", label: "Regular Exercise", type: "select" },
];

const binaryOptions = [
  { label: "No", value: 0 },
  { label: "Yes", value: 1 },
];

const symptomTags = [
  "Irregular periods",
  "Excess hair growth",
  "Acne and oily skin",
  "Weight gain",
  "Hair thinning",
  "Fertility issues",
  "Mood changes",
  "Pelvic pain",
  "Sleep problems",
  "Darkened skin",
  "Fatigue",
  "Headaches",
];

const infoCards = [
  {
    title: "Hormonal imbalance",
    text: "Elevated androgen levels can interfere with ovulation and cause symptoms like acne and excess hair growth.",
  },
  {
    title: "Insulin resistance",
    text: "Many women with PCOS have insulin resistance, which may increase androgen activity and metabolic challenges.",
  },
  {
    title: "Manageable condition",
    text: "With early lifestyle support and timely clinical care, symptoms can often be reduced and cycles better managed.",
  },
];

const steps = [
  {
    number: "1",
    title: "Stage 1: Symptom screening",
    text: "Enter symptom details such as cycle pattern, BMI, weight change, hair growth, skin darkening, and lifestyle factors.",
  },
  {
    number: "2",
    title: "Stage 2: Lab report analysis",
    text: "Upload a blood report or paste the report text so the system can extract LH and FSH values.",
  },
  {
    number: "3",
    title: "Get both results individually",
    text: "Compare symptom-based screening and lab-based screening to understand PCOS risk more clearly.",
  },
];

const navItems = [
  { id: "about", label: "About PCOS" },
  { id: "symptoms", label: "Symptoms" },
  { id: "prediction", label: "Stages" },
  { id: "remedies", label: "Remedies" },
  { id: "resources", label: "Resources" },
];

const remedies = [
  {
    title: "Yoga",
    image: "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&w=900&q=80",
    intro: "Yoga helps reduce stress hormones, improve hormonal balance, and improve blood flow to the ovaries.",
    points: [
      "Best poses: Surya Namaskar, Bhujangasana, Setu Bandhasana, Malasana, Balasana",
      "Benefits: supports mood, anxiety control, cycle regulation, and overall balance",
      "Practice: 20 to 30 minutes daily or 4 to 5 days per week",
    ],
  },
  {
    title: "Exercise",
    image: "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=900&q=80",
    intro: "Regular movement is essential for PCOS and supports weight control, insulin sensitivity, and hormone balance.",
    points: [
      "Walking for 30 to 45 minutes daily is excellent",
      "Cycling, swimming, light cardio, and strength training 2 to 3 times per week also help",
      "Daily movement improves energy and metabolic health",
    ],
  },
  {
    title: "Diet",
    image: "https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=900&q=80",
    intro: "Diet is one of the biggest control factors in PCOS because it strongly affects insulin resistance and inflammation.",
    points: [
      "Eat high-fiber foods like broccoli, spinach, beans, and oats",
      "Choose lean proteins such as eggs, chicken, fish, and lentils",
      "Use healthy fats and anti-inflammatory foods like nuts, seeds, berries, vegetables, and omega-3 sources",
      "Avoid excess sugar, junk food, maida, soft drinks, and heavily processed foods",
    ],
  },
];

const lifestyleDos = [
  "Exercise daily",
  "Maintain a healthy weight",
  "Sleep 7 to 8 hours",
  "Drink 6 to 8 glasses of water",
  "Reduce stress with yoga or meditation",
];

const lifestyleDonts = [
  "Skip meals",
  "Eat too much junk food",
  "Sleep very late regularly",
  "Sit continuously without movement",
  "Let stress build up unchecked",
];

const dailyRoutine = [
  { time: "Morning", text: "Start with warm water and 20 minutes of yoga." },
  { time: "Afternoon", text: "Have a healthy balanced meal with fiber, protein, and good fats." },
  { time: "Evening", text: "Go for a walk or do exercise." },
  { time: "Night", text: "Keep dinner light and aim for good sleep." },
];

function buildStage1Suggestions(formData, result) {
  if (!result) {
    return [];
  }

  const suggestions = [];
  const addSuggestion = (condition, message) => {
    if (condition) {
      suggestions.push(message);
    }
  };

  const bmiValue = Number(formData.bmi);
  const isHighRisk = result.prediction === 1;

  if (isHighRisk) {
    suggestions.push("High PCOS risk was predicted, so please consider medical follow-up for a proper evaluation.");
  } else {
    suggestions.push("Low PCOS risk was predicted, so continue healthy habits and monitor your health regularly.");
  }

  addSuggestion(
    Number.isFinite(bmiValue) && bmiValue >= 25,
    "Your BMI is on the higher side, so do daily exercise for 30 to 45 minutes and reduce sugar, junk food, and sugary drinks."
  );

  addSuggestion(
    Number(formData.cycle_ri) === 4,
    "Your cycle is irregular, so focus on yoga like Surya Namaskar and Bhujangasana, maintain a good sleep cycle, and avoid stress."
  );

  addSuggestion(
    Number(formData.weight_gain) === 1,
    "Weight gain is present, so follow a low-carb diet, avoid fast food and soft drinks, and choose vegetables with protein-rich foods."
  );

  addSuggestion(
    Number(formData.hair_loss) === 1,
    "Hair loss is present, so include iron-rich foods like spinach and dates, reduce stress, and consult a doctor if it becomes severe."
  );

  addSuggestion(
    Number(formData.hair_growth) === 1,
    "Hair growth symptoms may suggest higher androgen levels, so regular exercise, healthy weight control, and medical consultation can help."
  );

  addSuggestion(
    Number(formData.pimples) === 1,
    "Pimples are present, so avoid oily food, drink more water, and eat more fruits and vegetables."
  );

  addSuggestion(
    Number(formData.fast_food) === 1,
    "Fast food intake is marked yes, so avoid burgers, pizza, packaged snacks, and replace them with home food and fruits."
  );

  addSuggestion(
    Number(formData.reg_exercise) === 0,
    "Regular exercise is marked no, so start with 30 minutes of walking daily and gradually add simple workouts."
  );

  addSuggestion(
    Number(formData.skin_darkening) === 1,
    "Skin darkening may be related to insulin resistance, so control sugar intake and exercise regularly."
  );

  if (!isHighRisk) {
    suggestions.push("Maintain a balanced diet, continue regular exercise, avoid junk food, and manage stress well.");
  }

  if (isHighRisk && suggestions.length === 1) {
    suggestions.push("Focus on healthy food, regular activity, proper sleep, and an early doctor consultation for more guidance.");
  }

  return [...new Set(suggestions)];
}

function HomePage({ onOpenStage1, onOpenStage2 }) {
  const [activeSection, setActiveSection] = useState("about");

  const renderSection = () => {
    if (activeSection === "about") {
      return (
        <section className="content-section about-grid">
          <div className="section-copy">
            <p className="section-kicker">What is PCOS?</p>
            <h2>
              A common hormonal disorder that deserves
              <span> your attention</span>
            </h2>
            <p>
              PCOS is a hormonal condition where the ovaries may produce excess androgens. It can affect menstrual cycle regularity,
              fertility, metabolism, skin health, and emotional wellbeing.
            </p>
          </div>
          <div className="card-grid">
            {infoCards.map((card) => (
              <article className="soft-card" key={card.title}>
                <div className="icon-badge">+</div>
                <h3>{card.title}</h3>
                <p>{card.text}</p>
              </article>
            ))}
          </div>
        </section>
      );
    }

    if (activeSection === "symptoms") {
      return (
        <section className="content-section">
          <div className="section-copy narrow-copy">
            <p className="section-kicker">Common Symptoms</p>
            <h2>
              Recognise the signs
              <span> early</span>
            </h2>
            <p>
              PCOS can present differently for every woman. These are some of the most commonly reported symptom patterns seen in screening.
            </p>
          </div>
          <div className="tag-grid">
            {symptomTags.map((symptom) => (
              <span className="symptom-tag" key={symptom}>
                {symptom}
              </span>
            ))}
          </div>
        </section>
      );
    }

    if (activeSection === "prediction") {
      return (
        <section className="content-section process-section">
          <div className="section-copy process-copy">
            <p className="section-kicker">Two-Stage Workflow</p>
            <h2>
              Symptom screening and
              <span> lab analysis</span>
            </h2>
            <p>
              Stage 1 predicts PCOS risk from symptoms, and Stage 2 predicts PCOS risk from LH and FSH values extracted from a blood report.
            </p>
          </div>
          <div className="step-list solo-steps">
            {steps.map((step) => (
              <article className="step-card" key={step.number}>
                <div className="step-number">{step.number}</div>
                <div>
                  <h3>{step.title}</h3>
                  <p>{step.text}</p>
                </div>
              </article>
            ))}
          </div>
          <div className="hero-actions inline-actions">
            <button className="primary-button" type="button" onClick={onOpenStage1}>
              Open Stage 1
            </button>
            <button className="secondary-button" type="button" onClick={onOpenStage2}>
              Upload Report and Predict
            </button>
          </div>
        </section>
      );
    }

    if (activeSection === "remedies") {
      return (
        <section className="content-section remedies-section">
          <div className="section-copy narrow-copy">
            <p className="section-kicker">PCOS Remedies Guide</p>
            <h2>
              Daily care that supports
              <span> hormonal balance</span>
            </h2>
            <p>
              These remedies support hormonal health, insulin control, stress reduction, and cycle management. They are useful lifestyle practices and do not depend on Stage 1 or Stage 2.
            </p>
          </div>

          <div className="remedy-grid">
            {remedies.map((item) => (
              <article className="remedy-card" key={item.title}>
                <img className="remedy-image" src={item.image} alt={item.title} />
                <div className="remedy-body">
                  <h3>{item.title}</h3>
                  <p>{item.intro}</p>
                  <ul className="remedy-list">
                    {item.points.map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                </div>
              </article>
            ))}
          </div>

          <div className="remedy-lower-grid">
            <article className="soft-card lifestyle-card">
              <h3>Lifestyle Changes</h3>
              <p>Poor sleep, high stress, and inactivity can worsen PCOS. Try to follow these simple do's and don'ts.</p>
              <div className="dos-donts-grid">
                <div>
                  <h4>Do's</h4>
                  <ul className="remedy-list compact-list">
                    {lifestyleDos.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4>Don'ts</h4>
                  <ul className="remedy-list compact-list">
                    {lifestyleDonts.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </article>

            <article className="soft-card routine-card">
              <h3>Simple Daily Routine</h3>
              <div className="routine-list">
                {dailyRoutine.map((item) => (
                  <div className="routine-item" key={item.time}>
                    <strong>{item.time}</strong>
                    <p>{item.text}</p>
                  </div>
                ))}
              </div>
            </article>
          </div>
        </section>
      );
    }

    return (
      <section className="content-section resources-section">
        <div className="section-copy narrow-copy">
          <p className="section-kicker">Resources</p>
          <h2>
            Start early and seek
            <span> informed support</span>
          </h2>
          <p>
            This project is an awareness and screening tool. It helps users understand symptom patterns, but it is not a medical diagnosis.
          </p>
        </div>
        <div className="resources-box">
          <div className="resource-item">
            <h3>Stage 1</h3>
            <p>Use symptom values to get a fast first-stage PCOS screening result.</p>
          </div>
          <div className="resource-item">
            <h3>Stage 2</h3>
            <p>Upload or paste a blood report so LH and FSH can be used for lab-based screening.</p>
          </div>
          <div className="resource-item">
            <h3>Clinical follow-up</h3>
            <p>Use the project output as supporting information when discussing symptoms or lab findings with a doctor.</p>
          </div>
        </div>
      </section>
    );
  };

  return (
    <div className="landing-page">
      <header className="site-header">
        <div className="brand-wrap">
          <div className="brand-logo" aria-hidden="true">
            <span className="brand-logo-core" />
            <span className="brand-logo-leaf brand-logo-leaf-one" />
            <span className="brand-logo-leaf brand-logo-leaf-two" />
          </div>
          <div className="brand-mark">OvaCare</div>
        </div>
        <nav className="top-nav">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-tab ${activeSection === item.id ? "nav-tab-active" : ""}`}
              onClick={() => setActiveSection(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      <section className="hero-section">
        <div className="hero-text">
          <p className="hero-kicker">AI powered health insights</p>
          <h1>
            Understand and
            <span> Predict PCOS</span>
            early
          </h1>
          <p className="hero-copy">
            Polycystic Ovary Syndrome affects many women worldwide. Use Stage 1 for symptom screening or Stage 2 to upload a blood report and predict from LH and FSH values.
          </p>
          <div className="hero-actions">
            <button className="primary-button" type="button" onClick={onOpenStage1}>
              Stage 1 Predict
            </button>
            <button className="secondary-button" type="button" onClick={onOpenStage2}>
              Upload Report and Predict
            </button>
          </div>
        </div>

        <div className="hero-visual">
          <div className="ring-shell">
            <div className="ring-core">
              <strong>2</strong>
              <span>stages</span>
              <p>symptom-based and lab-based PCOS screening</p>
            </div>
          </div>
          <span className="floating-dot dot-one" />
          <span className="floating-dot dot-two" />
          <span className="floating-dot dot-three" />
        </div>
      </section>

      <section className="stat-strip">
        <article>
          <strong>Stage 1</strong>
          <span>symptom screening</span>
        </article>
        <article>
          <strong>Stage 2</strong>
          <span>lab report analysis</span>
        </article>
        <article>
          <strong>LH + FSH</strong>
          <span>blood-test based prediction</span>
        </article>
      </section>

      {renderSection()}

      <footer className="site-footer">
        <span>OvaCare</span>
        <span>For informational purposes only. Not a substitute for medical advice.</span>
      </footer>
    </div>
  );
}

function Stage1Page({ formData, setFormData, result, setResult, error, setError, loading, setLoading, onBack }) {
  const [heightCm, setHeightCm] = useState("");
  const suggestions = buildStage1Suggestions(formData, result);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((current) => ({
      ...current,
      [name]: value === "" ? "" : Number(value),
    }));
  };

  const calculateBmi = () => {
    const weightValue = Number(formData.weight);
    const heightValue = Number(heightCm);

    if (!weightValue || !heightValue) {
      setError("Enter weight and height to calculate BMI.");
      return;
    }

    const heightInMeters = heightValue / 100;
    if (heightInMeters <= 0) {
      setError("Height must be greater than zero.");
      return;
    }

    const bmiValue = Number((weightValue / (heightInMeters * heightInMeters)).toFixed(2));
    setFormData((current) => ({
      ...current,
      bmi: bmiValue,
    }));
    setError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Prediction request failed.");
      }
      setResult(data);
    } catch (requestError) {
      setResult(null);
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="predict-page-shell">
      <div className="predict-card">
        <div className="predict-topbar">
          <button className="back-link" type="button" onClick={onBack}>Back to Home</button>
          <p className="predict-badge">Stage 1 | Symptom-based screening</p>
        </div>

        <div className="predict-header">
          <p className="section-kicker">Stage 1</p>
          <h1>PCOS Risk Prediction Form</h1>
          <p>Fill in all values manually. The form estimates PCOS risk based on symptom-only inputs.</p>
        </div>

        <form className="predict-form" onSubmit={handleSubmit}>
          <div className="form-grid">
            {stage1Fields.map((field) => (
              <label className="field" key={field.name}>
                <span>{field.label}</span>
                {field.type === "select" ? (
                  <select name={field.name} value={formData[field.name]} onChange={handleChange} required>
                    <option value="" disabled>Select an option</option>
                    {(field.options || binaryOptions).map((option) => (
                      <option key={`${field.name}-${option.value}`} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                ) : field.name === "bmi" ? (
                  <div className="bmi-stack">
                    <input
                      name={field.name}
                      type={field.type}
                      step={field.step}
                      value={formData[field.name]}
                      onChange={handleChange}
                      placeholder={`Enter ${field.label}`}
                      required
                    />
                    <div className="bmi-helper">
                      <input
                        className="bmi-helper-input"
                        type="number"
                        step="any"
                        value={heightCm}
                        onChange={(event) => setHeightCm(event.target.value)}
                        placeholder="Enter Height (cm)"
                      />
                      <button className="secondary-button bmi-button" type="button" onClick={calculateBmi}>
                        Calculate Your BMI
                      </button>
                    </div>
                  </div>
                ) : (
                  <input
                    name={field.name}
                    type={field.type}
                    step={field.step}
                    value={formData[field.name]}
                    onChange={handleChange}
                    placeholder={`Enter ${field.label}`}
                    required
                  />
                )}
              </label>
            ))}
          </div>

          <div className="predict-actions">
            <button className="primary-button" type="submit" disabled={loading}>{loading ? "Predicting..." : "Predict PCOS Risk"}</button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => {
                setFormData(initialStage1Form);
                setHeightCm("");
                setResult(null);
                setError("");
              }}
            >
              Clear Form
            </button>
          </div>
        </form>

        <div className="result-card">
          {error ? <p className="error-text">{error}</p> : null}
          {result ? (
            <>
              <p className="section-kicker">Prediction Result</p>
              <h2>{result.risk_label}</h2>
              <p className="probability">Probability of PCOS: {(result.probability * 100).toFixed(2)}%</p>
              <p className="class-line">Predicted Class: {result.prediction}</p>
              <div className="suggestion-block">
                <h3>Suggestions</h3>
                <ul className="suggestion-list">
                  {suggestions.map((suggestion) => (
                    <li key={suggestion}>{suggestion}</li>
                  ))}
                </ul>
              </div>
            </>
          ) : (
            <p className="placeholder">Enter the symptom values and submit the form to view the prediction result.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function Stage2Page({ onBack }) {
  const [reportFile, setReportFile] = useState(null);
  const [reportText, setReportText] = useState("");
  const [lh, setLh] = useState("");
  const [fsh, setFsh] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);

  const handleExtract = async () => {
    setExtracting(true);
    setError("");
    setResult(null);

    try {
      const formData = new FormData();
      if (reportFile) {
        formData.append("report_file", reportFile);
      }
      if (reportText.trim()) {
        formData.append("report_text", reportText);
      }

      const response = await fetch(`${API_BASE_URL}/upload-stage2-report`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Report analysis failed.");
      }

      setLh(String(data.lh));
      setFsh(String(data.fsh));
      setResult(data);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setExtracting(false);
    }
  };

  const handlePredict = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/predict-stage2`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lh: Number(lh), fsh: Number(fsh) }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Stage 2 prediction failed.");
      }
      setResult(data);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="predict-page-shell">
      <div className="predict-card">
        <div className="predict-topbar">
          <button className="back-link" type="button" onClick={onBack}>Back to Home</button>
          <p className="predict-badge">Stage 2 | Lab-based screening</p>
        </div>

        <div className="predict-header">
          <p className="section-kicker">Stage 2</p>
          <h1>Upload Blood Report</h1>
          <p>Upload a report or paste report text to extract LH and FSH, then predict PCOS risk from lab values.</p>
        </div>

        <div className="stage2-grid">
          <section className="stage2-panel">
            <label className="field">
              <span>Upload report file</span>
              <input type="file" accept=".txt,.csv,.pdf,.png,.jpg,.jpeg,.bmp,.tif,.tiff" onChange={(event) => setReportFile(event.target.files?.[0] || null)} />
            </label>

            <label className="field">
              <span>Or paste report text</span>
              <textarea
                className="report-textarea"
                value={reportText}
                onChange={(event) => setReportText(event.target.value)}
                placeholder="Example: LH: 6.5 mIU/mL, FSH: 7.1 mIU/mL"
              />
            </label>

            <div className="predict-actions">
              <button className="primary-button" type="button" onClick={handleExtract} disabled={extracting}>
                {extracting ? "Extracting..." : "Upload Report and Predict"}
              </button>
            </div>
          </section>

          <section className="stage2-panel">
            <div className="form-grid stage2-values-grid">
              <label className="field">
                <span>LH Value</span>
                <input type="number" step="any" value={lh} onChange={(event) => setLh(event.target.value)} placeholder="Enter LH value" />
              </label>
              <label className="field">
                <span>FSH Value</span>
                <input type="number" step="any" value={fsh} onChange={(event) => setFsh(event.target.value)} placeholder="Enter FSH value" />
              </label>
            </div>

            <div className="predict-actions">
              <button className="secondary-button" type="button" onClick={handlePredict} disabled={loading || !lh || !fsh}>
                {loading ? "Predicting..." : "Predict From LH and FSH"}
              </button>
            </div>
          </section>
        </div>

        <div className="result-card">
          {error ? <p className="error-text">{error}</p> : null}
          {result ? (
            <>
              <p className="section-kicker">Lab Result</p>
              <h2>{result.risk_label}</h2>
              <p className="probability">Probability of PCOS: {(result.probability * 100).toFixed(2)}%</p>
              <p className="class-line">LH: {result.lh} | FSH: {result.fsh}</p>
            </>
          ) : (
            <p className="placeholder">Upload a report, paste report text, or enter LH and FSH values manually to view the lab-based result.</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [currentPage, setCurrentPage] = useState("home");
  const [stage1FormData, setStage1FormData] = useState(initialStage1Form);
  const [stage1Result, setStage1Result] = useState(null);
  const [stage1Error, setStage1Error] = useState("");
  const [stage1Loading, setStage1Loading] = useState(false);

  if (currentPage === "home") {
    return <HomePage onOpenStage1={() => setCurrentPage("stage1")} onOpenStage2={() => setCurrentPage("stage2")} />;
  }

  if (currentPage === "stage2") {
    return <Stage2Page onBack={() => setCurrentPage("home")} />;
  }

  return (
    <Stage1Page
      formData={stage1FormData}
      setFormData={setStage1FormData}
      result={stage1Result}
      setResult={setStage1Result}
      error={stage1Error}
      setError={setStage1Error}
      loading={stage1Loading}
      setLoading={setStage1Loading}
      onBack={() => setCurrentPage("home")}
    />
  );
}




