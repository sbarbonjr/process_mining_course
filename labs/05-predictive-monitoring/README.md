# Lab 05: Predictive Process Monitoring

Build pre-completion prefixes, use a temporal holdout, compare against a
base-rate model, and evaluate discrimination, calibration, and balanced
accuracy without future-information leakage.

Run:

```bash
python3 labs/05-predictive-monitoring/predictive_monitoring_lab.py
```

The implementation uses scikit-learn directly. A SkPM extension can replace the
manual prefix and encoding steps while preserving the same evaluation design.
