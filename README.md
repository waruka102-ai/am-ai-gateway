# 🛡️ AM AI Gateway (Multi-Layer Guardrail Engine)

An enterprise-grade Security Gateway designed to protect LLM Applications against Prompt Injections, Data Exfiltration, XSS attacks, and unauthorized system access.

![Status](https://img.shields.io/badge/Deploy_Status-Live_100%25-brightgreen)
![Platform](https://img.shields.io/badge/Platform-Render-purple)
![Architecture](https://img.shields.io/badge/Security-5--Layer_Guardrail-blue)

---

## 🏗️ System Architecture & Layer Breakdown

This gateway implements a **5-Layer Security Pipeline** before passing requests to the core LLM:

[ User Input ]
      │
      ▼
┌─────────────────────────────────────────┐
│ Layer 1: Basic Sanitization & Filtering │ ──▶ (Filters raw bad data)
└─────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────┐
│ Layer 2: Threat & Injection Detection   │ ──▶ (Blocks XSS, SQLi, Jailbreaks)
└─────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────┐
│ Layer 3: Dynamic Risk & Strike System   │ ──▶ (Tracks malicious behavior score)
└─────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────┐
│ Layer 4: Dynamic Output Mapping         │ ──▶ (Context-aware redirection)
└─────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────┐
│ Layer 5: Safe LLM Execution / Gateway   │ ──▶ (Final Output Generation)
└─────────────────────────────────────────┘

---

## 🔥 Key Features

- **Dynamic Context Redirection (Layer 4):** Automatically redirects potential security threats to safe topics (e.g., product inquiries) instead of returning hardcoded error messages.
- **Strike System Integration:** Maintains threat score counters (`strikes: 1`, `strikes: 2`) per context session to mitigate repetitive exploit attempts.
- **Render Cloud Ready:** Fully automated deployment architecture integrated with continuous testing suites via Google Colab.

---

## 🧪 Test Case Results

Recent execution logs (100% Pass Rate):

| Test Case | Payload Type | HTTP Status | Response Outcome | Strike Count |
| :--- | :--- | :--- | :--- | :--- |
| **Test 1** | Normal Request | `200 OK` | `SUCCESS` (Default Response) | `strikes: 0` |
| **Test 2** | XSS / Injection Attack | `200 OK` | `SUCCESS` (Redirected to Safe Topic) | `strikes: 1` |
| **Test 3** | Prompt Injection Attack | `200 OK` | `SUCCESS` (Redirected to Safe Topic) | `strikes: 2` |

---

## 🛠️ Tech Stack & Deployment

- **Backend:** Python / Django / FastAPI
- **Cloud Infrastructure:** Render Web Services
- **Validation Engine:** Google Colab Automated Testing
