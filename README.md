# 💰 Personal Finance Advisor

> **Stop double-counting. Know your real spending.**

An intelligent financial reconciliation system that unifies data from bank statements and expense-sharing apps to show your true financial picture.

---

## 🎯 The Problem

When you split expenses with friends:
- Your **bank** says ₹50,000 spent
- You **actually consumed** ₹32,000
- Friends **owe you** ₹18,000

Standard trackers count everything twice. This system fixes that.

---

## ✨ How It Works

1. **Upload** bank statement + expense tracker CSVs
2. **Smart matching** links transactions using date, amount & text similarity
3. **Get insights** on true spending, cash flow, and money owed to you

---

## 🛠️ Tech Stack

- **Backend:** Python, Kafka, PostgreSQL, Docker
- **Processing:** 4-pass matching algorithm with text similarity
- **Planned:** FastAPI, React dashboard, RAG chatbot (Llama 3)

---

## 🚀 Quick Start
```bash
# Start infrastructure
python start_infra.py

# Run analysis (separate terminal)
python run_analysis.py
```

---

## 📊 Current Features

✅ Multi-source data ingestion  
✅ Intelligent transaction matching  
✅ Settlement & transfer detection  
✅ Month-based session management  
🚧 Analytics dashboard (in progress)  
🚧 REST API (planned)  

---

## 🎓 Built With

Event-driven architecture • ETL pipelines • Data reconciliation algorithms • Clean code practices

---

**MIT License** • Built by [Your Name]
