# 🤖 Form Filler Bot

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-4.27-43B02A?style=for-the-badge&logo=selenium&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram_Bot-21.6-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Coolify](https://img.shields.io/badge/Coolify-Deployed-7C3AED?style=for-the-badge)

**Automated form submission bot for Bihar DBT Agri Service portal**
*Send an Excel file → Bot validates, fills, and reports back — fully headless*

</div>

---

## ✨ Features

- 📁 **Telegram-first UX** — send `.xlsx` file directly in chat, no GUI needed
- ✅ **Smart Validation** — checks all 10 required columns before touching the browser
- 🧹 **HTML Sanitization** — auto-strips `<span>` and other tags copied from web
- 🔐 **Credential Extraction** — reads `RegistrationNo` + `Password` from the Excel itself
- 📈 **Live Progress Updates** — real-time pings every 5 rows while filling
- 🛡️ **Robust Error Handling** — retries on stale elements, per-row error isolation
- 🏁 **Full Completion Report** — success count + per-row error details sent back
- 🐳 **Docker + Coolify Ready** — one-click deploy on Oracle Cloud

---

## 📋 Required Excel Columns

Your `.xlsx` file **must** contain all of these columns:

| Column | Description |
|---|---|
| `ProductName` | Name of the pesticide product |
| `ProductCIBCode` | CIB registration code |
| `ProductRegDate` | Product registration date |
| `InsecticideRegistrationValidUpto` | Validity date |
| `ManufacturerName` | Manufacturer / importer name |
| `PrincipalCerificateNo` | Principal certificate number |
| `PrincipleCertificateIssueDate` | Certificate issue date |
| `PrincipleCertificateValidUpto` | Certificate validity date |
| `RegistrationNo` | Portal login ID |
| `Password` | Portal login password |

> 💡 Credentials only need to be present in the **first row** — they're reused for all rows.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Chrome installed (for local testing)
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/bihar-form-filler-bot
cd bihar-form-filler-bot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your bot token
export TELEGRAM_BOT_TOKEN="your_token_here"

# 4. Run the bot
python bot.py
