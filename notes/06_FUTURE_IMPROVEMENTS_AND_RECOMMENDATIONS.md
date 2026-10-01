# Future Improvements & Architectural Recommendations

This document outlines key technical and operational recommendations to further enhance the **JUMO Laser Trimming Support System** for production scale.

---

## 1. Real-Time Data & Concept Drift Monitoring (Evidently AI)

### Problem
Manufacturing conditions evolve over time due to seasonal humidity changes, machine degradation, target cathode aging, and raw material lot variations. Static ML models risk accuracy decay if unmonitored.

### Recommendation
Integrate **Evidently AI** or **Azure ML Data Drift Monitoring**:
- **Input Feature Drift**: Track statistical distributions (using Wasserstein distance or Kolmogorov-Smirnov tests) of incoming parameters such as `tcr_sputter`, `film_thickness`, and `air_humidity`.
- **Target Drift**: Compare predicted $NC$ distributions against post-selection physical resistance results.
- **Automated Alerts**: Configure Webhook alerts (e.g., Teams/Slack) when distribution drift exceeds defined thresholds ($\alpha = 0.05$).

---

## 2. Automated Continuous Retraining Pipeline (MLOps)

### Problem
Manual model retraining in `app/mlops.py` requires developer intervention whenever new production batches arrive.

### Recommendation
Establish an automated CI/CD retraining workflow:
- **Scheduled Trigger**: Run automated weekly or bi-weekly retraining jobs when new selection data is appended to Supabase.
- **Automated Evaluation Gate**: Retrained candidate models must outperform the active production model's RMSE on a holdout test set before auto-registering in MLflow.
- **Canary / Blue-Green Deployment**: Serve candidate models via Azure Container Apps revisions with traffic splitting (e.g. 10% canary traffic).

---

## 3. Integrated SHAP Explainability Dashboard (XAI)

### Problem
Operators and quality control engineers require transparent justifications for AI recommendations before overriding manual laser settings.

### Recommendation
Integrate **SHAP (SHapley Additive exPlanations)** visualization directly into the React UI:
- **Waterfall Feature Attribution**: Display top contributing factors for each prediction (e.g., *"+0.012 NC adjustment due to 15.0 nm film thickness", "-0.005 NC adjustment due to high humidity"*).
- **Compliance Artifacts**: Automatically log SHAP values in the database for auditability under EU AI Act Article 13 transparency guidelines.

---

## 4. Managed Enterprise Database & Infrastructure Scalability

### Problem
The current SQLite setup (`nc_prediction.db`) is ideal for lightweight container deployment but lacks multi-region replication and concurrent write locking needed for high-throughput factory lines.

### Recommendation
- **Database Migration**: Migrate to managed **Supabase PostgreSQL** or **Azure Database for PostgreSQL Flexible Server**.
- **Connection Pooling**: Use **PgBouncer** to handle high-frequency concurrent prediction queries across multiple laser table stations.
- **Backup & Disaster Recovery**: Enable Point-In-Time Recovery (PITR) and automated daily snapshots.

---

## 5. Security, RBAC & Multi-Tenant Authentication

### Problem
The API currently accepts unauthenticated requests for testing convenience.

### Recommendation
Implement enterprise security controls:
- **OAuth2 / JWT Authentication**: Secure FastAPI endpoints using JSON Web Tokens.
- **Role-Based Access Control (RBAC)**:
  - **Operator Role**: Can calculate predictions and view default configurations.
  - **Process Engineer Role**: Can view MLflow experiment runs, trigger model retraining, and adjust default fallback parameters.
  - **Auditor Role**: Read-only access to historical prediction logs and compliance traceability records.

---

## 6. Advanced Model Ensembling & Deep Learning

### Problem
XGBoost achieves state-of-the-art tabular performance (RMSE 0.0202), but composite model architectures could further improve rare sensor group handling.

### Recommendation
- **Ensemble Stacking**: Combine **XGBoost**, **LightGBM**, and **CatBoost** using a Ridge regression meta-learner.
- **Physics-Informed Neural Networks (PINN)**: Embed platinum resistance temperature equations ($R(T) = R_0(1 + A T + B T^2)$) as inductive bias constraints in a PyTorch network to improve generalization on rare sensor geometries (e.g. `PCF` Pt1000).
