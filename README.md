# 🤖 Coworker AI v2.1

**Your intelligent document organization assistant.**
Turn a chaotic folder of receipts, invoices, and contracts into a structured archive with a single command.

## ✨ Features

- **Interactive Setup**: Simple wizard to configure how you want your files organized.
- **Smart Organization**: Automatically sorts files by Date and Category.
- **AI-Powered**: Uses Google Gemini to read PDFs and Images (Scan/Receipts).
- **Safe by Default**: Files are moved to `Organized/`, but originals are backed up in `.coworker/trash/`.
- **Quality Control**: "Review" folder + CSV report for low-confidence or ambiguous documents.
- **Master Report**: Generates a clean Excel report (`master.xlsx`).
- **Telemetry**: Tracks costs (tokens) and processing time.

## 🚀 Quick Start

### 1. Install

Install globally with `pipx` (recommended) or `pip`:

```bash
pipx install .
```

### 2. Configure API Key

Get your key from [Google AI Studio](https://aistudio.google.com/).

```bash
export GEMINI_API_KEY="your_api_key_here"
```

### 3. Quick Run (Zero Setup)

Just cd into any folder with receipts and run:

```bash
cd my_receipts_folder
coworker run
```

Coworker will:

- Auto-initialize (hidden `.coworker` folder).
- **Move** files into `Organized/` (Safe Move).
- Place ambiguous files in `Review/`.
- Generate `master.xlsx` and `Review/review.csv`.

**Mistake?** Run `coworker undo` to restore files.

### 4. Advanced Setup (Optional)

If you want a dedicated workspace with an `Inbox/` folder:

```bash
# Create the workspace
coworker init my_money

# Run the setup wizard
cd my_money
coworker setup

# Drop files in Inbox/ and run
coworker run
```

### 5. Run!

1.  Put your **Messy Files** inside the `Inbox/` folder (or current folder for ad-hoc).
2.  Run the magic command:
    ```bash
    coworker run
    ```
3.  Enjoy the results:
    - `Organized/`: Clean, renamed files.
    - `Review/`: Files that need your attention.
    - `master.xlsx`: Your financial summary.

## 📂 Structure

Ad-hoc workspace (default):

```text
my_folder/
├── Organized/       <-- CLEAN RESULTS (YYYY-MM/Category/...)
├── Review/          <-- CHECK THESE
│   └── review.csv   <-- REASONS (CSV)
└── master.xlsx      <-- EXCEL REPORT
```

_(System files like backups, config, cache, and logs are hidden in `.coworker/`)_

## 🛠 Command Reference

| Command                | Usage Scenario      | Description                                                                 |
| :--------------------- | :------------------ | :-------------------------------------------------------------------------- |
| **`coworker run`**     | **Daily Use**       | **The main command.** Runs in current folder. **MOVES** files by default.   |
| `coworker undo`        | **Recovery**        | **Restores files** from the last run to their original locations.           |
| `coworker run --safe`  | **Testing**         | Runs in copy mode (keeps originals in place).                               |
| `coworker run --dev`   | **Debug**           | Includes technical columns (tokens, hash) and system stats in Excel.        |
| `coworker init <path>` | **New Project**     | Creates a dedicated workspace structure with an explicit `Inbox/`.          |
| `coworker setup`       | **Configuration**   | Runs the interactive wizard to customize categories and folder preferences. |
| `coworker status`      | **Monitoring**      | View total files processed, tokens used, and estimated costs.               |
| `coworker doctor`      | **Troubleshooting** | Checks if your API key is set and dependencies are healthy.                 |

## ❓ FAQ

**Q: What if the AI makes a mistake?**
A: Files with low confidence (< 70%) or missing dates/amounts are automatically moved to `Review/` folder. Check `Review/review.csv` for reasons. You can rename them and move them to `Organized/` manually.

**Q: Is it safe?**
A: Yes. `coworker run` defaults to a **safe move**: originals are backed up in `.coworker/trash/` before moving. You can restore them instantly with `coworker undo`.

**Q: How do I change settings?**
A: Run `coworker setup` again, or edit `.coworker/config.yml` directly.
