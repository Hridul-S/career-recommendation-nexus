
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import career_recomentationp as crp
import database as db
import uvicorn
from fastapi import Header, Depends

app = FastAPI(title="Career Pro API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model and encoders once at startup
print("Loading model and training...")
MODEL, LE_DICT, TARGET_LE, FEATURE_COLUMNS = crp.load_and_train()
print("Model loaded successfully.")

# Authentication Dependency
def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.split(" ")[1]
    user_id = db.get_user_id_by_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired")
    return user_id

class UserProfile(BaseModel):
    data: Dict[str, Any]

class LoginData(BaseModel):
    email: str
    password: str

@app.get("/")
def read_index():
    return FileResponse("index.html")

@app.get("/login")
def read_login():
    return FileResponse("login.html")

@app.get("/dashboard")
def read_dashboard():
    # In a real app, we would check for a session/token here
    return FileResponse("dashboard.html")

@app.post("/api/login")
def login(data: LoginData):
    user_id = db.verify_user(data.email, data.password)
    if user_id:
        token = db.create_session(user_id)
        return {"success": True, "token": token, "message": "Login successful"}
    raise HTTPException(status_code=401, detail="Invalid email or password")

@app.post("/api/signup")
def signup(data: LoginData):
    if db.create_user(data.email, data.password):
        return {"success": True, "message": "User created successfully"}
    raise HTTPException(status_code=400, detail="User already exists")

@app.get("/api/me")
def get_me(user_id: int = Depends(get_current_user)):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return {"email": row['email'] if row else "Unknown"}

@app.get("/api/metadata")
def get_metadata():
    """Returns the required fields and their options for the frontend to build the form."""
    metadata = {}
    skill_columns = ['Python', 'SQL', 'Java']
    
    for col in FEATURE_COLUMNS:
        if col in skill_columns:
            metadata[col] = {
                "type": "skill",
                "options": list(crp.SKILL_MAP.keys())
            }
        elif col in LE_DICT:
            # Capitalize each word for professional display
            raw_options = sorted(list(LE_DICT[col].classes_))
            formatted_options = [" ".join(word.capitalize() for word in opt.split()) for opt in raw_options]
            metadata[col] = {
                "type": "categorical",
                "options": formatted_options
            }
        else:
            metadata[col] = {
                "type": "numeric",
                "integer_only": True if col.lower() == 'age' else False
            }
    return metadata

@app.get("/api/history")
def get_history(user_id: int = Depends(get_current_user)):
    return db.get_history(user_id)

@app.get("/api/competencies")
def get_competencies(career: str = None, user_id: int = Depends(get_current_user)):
    latest_profile = db.get_profile(user_id)
    if not latest_profile:
        return {}
    
    profile_data = latest_profile.get('data', latest_profile)
    
    def get_val(key, default):
        val = profile_data.get(key, default)
        try:
            if isinstance(val, str) and val in crp.SKILL_MAP:
                return crp.SKILL_MAP[val]
            return float(val)
        except:
            return float(default)

    raw_gpa = get_val('GPA', 3.0)
    eff_gpa = raw_gpa if raw_gpa > 5 else raw_gpa * 2.5
    
    # Professional skill categories with metadata
    categories = {
        "Technical Mastery": {"icon": "💻", "desc": "Execution of complex technical stacks and architectural patterns."},
        "Analytical Intelligence": {"icon": "📊", "desc": "Data-driven decision making and statistical inference capability."},
        "System Fundamentals": {"icon": "⚙️", "desc": "Knowledge of core software engineering and database principles."},
        "Future Performance": {"icon": "🚀", "desc": "Predicted adaptability and growth potential in specialized roles."}
    }

    # Dynamic Adjustments based on Career
    if career:
        c_low = career.lower()
        if any(x in c_low for x in ["security", "hacker", "privacy", "forensic"]):
            categories["Technical Mastery"] = {"icon": "🛡️", "desc": "Specialized defense mechanisms and security protocols.", "name": "Defense Systems"}
            categories["Analytical Intelligence"] = {"icon": "🔍", "desc": "Threat detection, pattern recognition, and risk assessment.", "name": "Threat Intelligence"}
            categories["System Fundamentals"] = {"icon": "🔗", "desc": "Secure infrastructure and network architecture resilience.", "name": "System Security"}
            categories["Future Performance"] = {"icon": "⚡", "desc": "Ability to respond to novel cyber threats proactively.", "name": "Incident Readiness"}
        elif any(x in c_low for x in ["data", "research", "ai", "machine", "nlp", "vision", "quantum", "bioinfo"]):
            categories["Technical Mastery"] = {"icon": "🧠", "desc": "Implementation of advanced algorithms and model architectures.", "name": "Algorithmic Logic"}
            categories["Analytical Intelligence"] = {"icon": "📈", "desc": "Mathematical foundations and statistical data modeling.", "name": "Statistical Intelligence"}
            categories["System Fundamentals"] = {"icon": "📐", "desc": "Data pipeline engineering and model scaling.", "name": "Data Architecture"}
            categories["Future Performance"] = {"icon": "🤖", "desc": "Potential to innovate new machine learning paradigms.", "name": "Research Innovation"}
        elif any(x in c_low for x in ["graphics", "game", "vr", "development", "software", "web", "mobile", "app", "block", "system"]):
            categories["Technical Mastery"] = {"icon": "💻", "desc": "Architecture design and scalability in application development.", "name": "System Architecture"}
            categories["Analytical Intelligence"] = {"icon": "🧩", "desc": "Problem-solving and complex logic implementation.", "name": "Logic & Algorithms"}
            categories["System Fundamentals"] = {"icon": "⚙️", "desc": "Core foundation in frameworks and deployment.", "name": "Engineering Foundation"}
            categories["Future Performance"] = {"icon": "🚀", "desc": "Adaptability to new frameworks and technologies.", "name": "Tech Adaptability"}
        elif any(x in c_low for x in ["design", "ux", "seo", "geo"]):
            categories["Technical Mastery"] = {"icon": "🎨", "desc": "Mastery of visual hierarchy and structural design.", "name": "Design Mastery"}
            categories["Analytical Intelligence"] = {"icon": "👤", "desc": "Understanding user behaviors and testing methodologies.", "name": "User Empathy"}
            categories["System Fundamentals"] = {"icon": "📱", "desc": "Translating designs to functional interfaces.", "name": "Interactive Systems"}
            categories["Future Performance"] = {"icon": "🌟", "desc": "Trend forecasting and innovative interaction patterns.", "name": "Creative Vision"}
        elif any(x in c_low for x in ["cloud", "devops", "database", "admin"]):
            categories["Technical Mastery"] = {"icon": "☁️", "desc": "Designing scalable distributed architectures.", "name": "Cloud Infrastructure"}
            categories["Analytical Intelligence"] = {"icon": "📊", "desc": "Performance metrics tuning and capacity planning.", "name": "Performance Analytics"}
            categories["System Fundamentals"] = {"icon": "🔄", "desc": "Continuous integration and deployment pipelines.", "name": "Automation & CI/CD"}
            categories["Future Performance"] = {"icon": "🛡️", "desc": "Ensuring high availability and disaster recovery.", "name": "Reliability Engineering"}

    s1 = int(40 + (get_val('Python', 1) * 20))
    s2 = int(eff_gpa / 10.0 * 100)
    s3 = int(40 + (get_val('SQL', 1) * 20))
    s4 = int(40 + (get_val('Java', 1) * 20))

    scores = {
        "Technical Mastery": s1,
        "Analytical Intelligence": s2,
        "System Fundamentals": s3,
        "Future Performance": s4
    }

    def clamp(s):
        return max(5, min(100, int(s)))

    def get_label(s):
        if s >= 90: return "EXPERT"
        if s >= 75: return "ADVANCED"
        if s >= 60: return "INTERMEDIATE"
        return "NOVICE"

    return {
        categories[k].get("name", k): {
            "score": clamp(scores[k]),
            "label": get_label(clamp(scores[k])),
            "desc": categories[k]["desc"],
            "icon": categories[k]["icon"]
        } for k in categories
    }

@app.get("/api/roadmap/{career}")
def get_roadmap(career: str):
    # Professional tailored roadmaps for presentation
    roadmaps = {
        "Machine Learning Researcher": [
            "Phase 1: Advanced Probability & Statistical Inference",
            "Phase 2: Deep Generative Models & Transformers",
            "Phase 3: Research Methodology & Academic Writing",
            "Phase 4: Optimization for Machine Learning"
        ],
        "Data Scientist": [
            "Phase 1: Advanced Statistical Modeling",
            "Phase 2: Big Data Processing (Spark/Flink)",
            "Phase 3: Automated ML & Feature Engineering",
            "Phase 4: Executive Data Storytelling"
        ],
        "Software Engineer": [
            "Phase 1: High-Level System Design",
            "Phase 2: Distributed Systems & Scalability",
            "Phase 3: Advanced Patterns (Clean Arch/DDD)",
            "Phase 4: Performance Engineering & SRE"
        ],
        "Web Developer": [
            "Phase 1: Modern Component Architecture",
            "Phase 2: Next.js & Server-Side Optimization",
            "Phase 3: Advanced Web Security & Auth",
            "Phase 4: Real-time Data Sync (WebSockets)"
        ],
        "Information Security Analyst": [
            "Phase 1: Network Defense & Perimeter Security",
            "Phase 2: Threat Hunting & SIEM Mastery",
            "Phase 3: GRC (Governance, Risk, Compliance)",
            "Phase 4: Advanced SOC Operations"
        ],
        "Security Analyst": [
            "Phase 1: Vulnerability Assessment Logic",
            "Phase 2: Incident Detection & Response",
            "Phase 3: Digital Forensic Fundamentals",
            "Phase 4: Security Automation & Orchestration"
        ],
        "Machine Learning Engineer": [
            "Phase 1: Production-Grade ML Systems",
            "Phase 2: MLOps & Model Monitoring",
            "Phase 3: Scaling Models with Kubernetes",
            "Phase 4: Edge AI Implementation"
        ],
        "Database Administrator": [
            "Phase 1: Query Tuning & Schema Engineering",
            "Phase 2: High Availability & DR Planning",
            "Phase 3: NoSQL & Distributed Databases",
            "Phase 4: Database Security & Auditing"
        ],
        "Cloud Solutions Architect": [
            "Phase 1: Multi-Cloud Strategy Design",
            "Phase 2: Cost Optimization & FinOps",
            "Phase 3: Infrastructure as Code (Terraform)",
            "Phase 4: Disaster Recovery Architecting"
        ],
        "Mobile App Developer": [
            "Phase 1: Cross-Platform Performance Mastery",
            "Phase 2: Native API Integration",
            "Phase 3: Mobile Security & Offline Sync",
            "Phase 4: App Store Optimization & CI/CD"
        ],
        "Graphics Programmer": [
            "Phase 1: Low-Level Graphics APIs (Vulkan/DX12)",
            "Phase 2: Shader Development & GLSL/HLSL",
            "Phase 3: Real-time Rendering Heuristics",
            "Phase 4: GPU Performance Profiling"
        ],
        "NLP Research Scientist": [
            "Phase 1: Advanced Language Modeling",
            "Phase 2: LLM Fine-tuning & Alignment",
            "Phase 3: Multimodal NLP Architectures",
            "Phase 4: Efficiency in Large-scale NLP"
        ],
        "Game Developer": [
            "Phase 1: Physics Engine Integration",
            "Phase 2: Advanced AI in Games",
            "Phase 3: Multiplayer Networking Logic",
            "Phase 4: Monetization & Analytics Strategy"
        ],
        "Embedded Software Engineer": [
            "Phase 1: Real-time Operating Systems (RTOS)",
            "Phase 2: Low-level Driver Development",
            "Phase 3: Firmware Security & Protocols",
            "Phase 4: Hardware-Software Co-Design"
        ],
        "Data Analyst": [
            "Phase 1: Business Intelligence Visualization",
            "Phase 2: Statistical Inference for Product",
            "Phase 3: Data Warehouse Integration",
            "Phase 4: Advanced Predictive Analytics"
        ],
        "Robotics Engineer": [
            "Phase 1: Control Systems & Kinematics",
            "Phase 2: SLAM & Sensor Fusion",
            "Phase 3: Robot Operating System (ROS 2)",
            "Phase 4: Autonomous Navigation Logic"
        ],
        "Ethical Hacker": [
            "Phase 1: Penetration Testing Methodology",
            "Phase 2: Exploit Development & Research",
            "Phase 3: Web & Network Mastery",
            "Phase 4: Red Teaming & Adversary Emulation"
        ],
        "Computer Vision Engineer": [
            "Phase 1: Image Processing Fundamentals",
            "Phase 2: Object Detection & Segmentation",
            "Phase 3: 3D Vision & Pose Estimation",
            "Phase 4: CV on Embedded Devices"
        ],
        "DevOps Engineer": [
            "Phase 1: CI/CD Excellence & Automation",
            "Phase 2: Kubernetes Orchestration",
            "Phase 3: Service Mesh & Advanced Networking",
            "Phase 4: Observability & SRE Practice"
        ],
        "Bioinformatician": [
            "Phase 1: Computational Genomic Analysis",
            "Phase 2: Sequence Alignment Algorithms",
            "Phase 3: Structural Biology Modeling",
            "Phase 4: Biostatistics & Data Science"
        ],
        "IoT Developer": [
            "Phase 1: IoT Protocols & Communication",
            "Phase 2: Edge Computing & Analytics",
            "Phase 3: Device Security & Fleet Management",
            "Phase 4: End-to-End IoT Architecting"
        ],
        "NLP Engineer": [
            "Phase 1: Text Processing & NLTK/Spacy",
            "Phase 2: Sequential Modeling & LSTMs",
            "Phase 3: BERT & Transformer Integration",
            "Phase 4: Deploying NLP Microservices"
        ],
        "UX Designer": [
            "Phase 1: Visual Design Systems",
            "Phase 2: Interaction & Motion Design",
            "Phase 3: Advanced User Research Labs",
            "Phase 4: Design Leadership & Ops"
        ],
        "Healthcare IT Specialist": [
            "Phase 1: Health Data Standards (HL7/FHIR)",
            "Phase 2: Medical Imaging Systems (PACS)",
            "Phase 3: EHR Integration & Workflows",
            "Phase 4: Cybersecurity in Healthcare"
        ],
        "Quantum Computing Researcher": [
            "Phase 1: Quantum Mechanics for CS",
            "Phase 2: Quantum Algorithm Complexity",
            "Phase 3: Error Correction & Hardware",
            "Phase 4: Hybrid Quantum-Classical ML"
        ],
        "VR Developer": [
            "Phase 1: Spatial Computing Principles",
            "Phase 2: Haptic & Interaction Feedback",
            "Phase 3: 3D Environment Optimization",
            "Phase 4: Social VR & Multi-user Sync"
        ],
        "Blockchain Engineer": [
            "Phase 1: Distributed Ledger Architecture",
            "Phase 2: Smart Contract Dev (Solidity)",
            "Phase 3: Consensus Protocols & Cryptography",
            "Phase 4: DeFi & Web3 Integration Hubs"
        ],
        "SEO Specialist": [
            "Phase 1: Technical SEO & Site Architecture",
            "Phase 2: Content Strategy & Semantic Web",
            "Phase 3: Algorithm Tracking & Analytics",
            "Phase 4: International SEO & Localization"
        ],
        "Data Privacy Specialist": [
            "Phase 1: Privacy Law (GDPR/CCPA) Mastery",
            "Phase 2: Privacy-Enhancing Tech (PETs)",
            "Phase 3: Risk Assessment & DPIA Logic",
            "Phase 4: Secure Data De-identification"
        ],
        "Geospatial Analyst": [
            "Phase 1: GIS Software Proficiency",
            "Phase 2: Remote Sensing & Image Analysis",
            "Phase 3: Spatial Database Management",
            "Phase 4: Python for Geospatial Mapping"
        ],
        "Distributed Systems Engineer": [
            "Phase 1: Agreement & Consensus Algorithms",
            "Phase 2: Fault Tolerance & Availability",
            "Phase 3: Performance Tuning in Clusters",
            "Phase 4: Large-scale Messaging Systems"
        ],
        "Digital Forensics Specialist": [
            "Phase 1: Evidence Collection & Preservation",
            "Phase 2: File System & Memory Analysis",
            "Phase 3: Malware Analysis & Forensics",
            "Phase 4: Legal Reporting & Expert Testimony"
        ],
        "AI Researcher": [
            "Phase 1: AGI Research & Probabilistic Logic",
            "Phase 2: Ethics & Fairness in AI",
            "Phase 3: Symbolic vs Connectionist AI",
            "Phase 4: Neuromorphic Computing Dev"
        ]
    }
    
    # Fuzzy match or exact match
    match = roadmaps.get(career)
    if not match:
        for k, v in roadmaps.items():
            if k.lower() in career.lower() or career.lower() in k.lower():
                match = v
                break
    
    return match if match else [
        "Phase 1: Advanced Domain Specialization",
        "Phase 2: Strategic Leadership & Project Mastery",
        "Phase 3: Innovation & Emerging Tech Exploration",
        "Phase 4: Professional Network Expansion & Mentorship"
    ]

@app.get("/api/institution")
def get_institution():
    """Returns institutional metadata for professional presentation."""
    return {
        "name": "Center for Advanced Computing & Career Excellence",
        "department": "Department of Computer Science & Engineering",
        "program": "Undergraduate Career Pathway Initiative",
        "version": "2.4.0-PRO",
        "mentor_id": "HOD-CSE-P1"
    }

@app.post("/api/predict")
def predict(profile_obj: UserProfile, user_id: int = Depends(get_current_user)):
    # Use model_dump for Pydantic V2 compatibility
    profile = profile_obj.model_dump()
    
    try:
        # Pre-process inputs
        processed_data = {}
        skill_columns = ['Python', 'SQL', 'Java']
        
        for col in FEATURE_COLUMNS:
            # We look inside profile['data']
            val = profile['data'].get(col)
            if val is None:
                raise HTTPException(status_code=400, detail=f"Missing field: {col}")
            
            if col in skill_columns:
                matched_skill = next((k for k in crp.SKILL_MAP if k.lower() == str(val).lower().strip()), None)
                if not matched_skill:
                    raise HTTPException(status_code=400, detail=f"Invalid skill level for {col}: {val}")
                processed_data[col] = crp.SKILL_MAP[matched_skill]
            
            elif col in LE_DICT:
                le = LE_DICT[col]
                options = le.classes_
                choice = str(val).strip().lower()
                
                matched = next((o for o in options if o.lower() == choice), None)
                if not matched:
                    choice_no_space = choice.replace(" ", "")
                    matched = next((o for o in options if o.lower().replace(" ", "") == choice_no_space), None)
                if not matched and len(choice) > 1:
                    partials = [o for o in options if choice in o.lower()]
                    if len(partials) == 1:
                        matched = partials[0]
                
                if not matched:
                    raise HTTPException(status_code=400, detail=f"Invalid option for {col}: {val}")
                
                processed_data[col] = int(le.transform([matched])[0])
            else:
                try:
                    processed_data[col] = float(val)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid numeric value for {col}: {val}")

        # Get recommendations using a DataFrame to maintain feature names and avoid warnings
        import pandas as pd
        input_df = pd.DataFrame([processed_data], columns=FEATURE_COLUMNS)
        
        print("\n--- DEBUG PREDICT ENDPOINT ---")
        print(f"INCOMING RAW: {profile['data']}")
        print(f"PROCESSED FOR MODEL: {processed_data}")
        
        # --- EXPERT HEURISTICS LAYER ---
        # 1. Neutralize Gender (Set to most common value from LE if exists to keep model happy but neutral)
        if 'Gender' in FEATURE_COLUMNS and 'Gender' in LE_DICT:
            # We don't want gender to influence the score, so we use a neutral baseline for prediction
            input_df['Gender'] = LE_DICT['Gender'].transform([LE_DICT['Gender'].classes_[0]])[0]

        # 2. Extract raw values for heuristic boosting
        raw_age = processed_data.get('Age', 20)
        raw_gpa = processed_data.get('GPA', 3.0)
        strong_skills_count = sum(1 for col in skill_columns if processed_data.get(col) == 2) # 2 is 'Strong'

        # Get base prediction from model
        top_cat, top_cat_prob, top_careers, top_probs = crp.get_recommendations_df(
            input_df, MODEL, LE_DICT, TARGET_LE, FEATURE_COLUMNS,
            raw_domain=profile['data'].get('Interested Domain')
        )
        print(f"MODEL RAW TOP CAREERS: {top_careers} (Probs: {top_probs})")
        print("------------------------------\n")

        # 3. Apply Professional Heuristics to the probability scores
        # Base multiplier logic
        score_modifier = 1.0
        
        # GPA Boost: Higher GPA = Higher Match (Max +20% boost for 10.0)
        # Normalize GPA to 0-10 scale if it's 0-4
        eff_gpa = raw_gpa if raw_gpa > 5 else raw_gpa * 2.5
        gpa_boost = (eff_gpa / 10.0) * 0.25
        score_modifier += gpa_boost

        # Skill Boost: +15% for each 'Strong' skill (Significant visibility)
        skill_boost = strong_skills_count * 0.15
        score_modifier += skill_boost

        # Age Penalty: Neutral < 40, Decay after 40
        age_penalty = 0
        if raw_age >= 40:
            age_penalty = min(0.4, (raw_age - 40) * 0.03) # Up to 40% penalty for significantly higher age
        
        # Apply modifier and penalty
        def adjust_score(s):
            new_score = (s * score_modifier) - age_penalty
            return max(0.05, min(0.99, new_score)) # Keep within [5%, 99%] range

        final_cat_prob = adjust_score(top_cat_prob)
        final_career_probs = [adjust_score(p) for p in top_probs]

        result = {
            "primary_field": top_cat,
            "field_description": crp.CATEGORY_DESCRIPTIONS.get(top_cat, "Specialized field requiring advanced technical skills."),
            "field_confidence": float(final_cat_prob),
            "recommendations": [
                {"role": career, "match": float(prob)}
                for career, prob in zip(top_careers, final_career_probs)
            ]
        }
        
        # Save to database (Use expert-refined scores)
        db.save_simulation(user_id, str(top_careers[0]), f"{int(final_career_probs[0]*100)}%", result)
        # Save processed numeric profile for dashboard snapshot
        db.save_profile(user_id, processed_data)

        return result
    except HTTPException as he:
        # Re-raise HTTP exceptions (like 400s) directly
        raise he
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
