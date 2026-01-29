# 🤖 Coworker AI v2.0

**Your intelligent document organization assistant.**
Turn a chaotic folder of receipts, invoices, and contracts into a structured archive with a single command.

## ✨ Features

- **Interactive Setup**: Simple wizard to configure how you want your files organized.
- **Smart Organization**: Automatically sorts files by Date and Category.
- **AI-Powered**: Uses Google Gemini to read PDFs and Images (Scan/Receipts).
- **Quality Control**: "Review" folder for low-confidence or ambiguous documents.
- **Master Report**: Generates a detailed Excel report with monthly breakdowns.
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
- Organize files into `Organized/`, `Review/`.
- **Warning**: By default, it **MOVES** files. To keep originals, use `--safe`.
- Generate `master.xlsx` in the current folder.

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

1.  Put your **Messy Files** inside the `Inbox/` folder.
2.  Run the magic command:
    ```bash
    coworker run
    ```
3.  Enjoy the results:
    - `Organized/`: Clean, renamed files.
    - `Review/`: Files that need your attention.
    - `Exports/master.xlsx`: Your financial summary.

## 📂 Structure

What you see in your workspace:

```text
my_workspace/
├── Inbox/           <-- DROP FILES HERE
├── Organized/       <-- CLEAN RESULTS (YYYY-MM/Category/...)
├── Review/          <-- CHECK THESE (Low confidence)
└── Exports/         <-- EXCEL REPORTS
```

_(System files like config, cache, and logs are hidden in `.coworker/`)_

## 🛠 Command Reference

| Command                | Usage Scenario      | Description                                                                 |
| :--------------------- | :------------------ | :-------------------------------------------------------------------------- |
| **`coworker run`**     | **Daily Use**       | **The main command.** Runs in current folder. **MOVES** files by default.   |
| `coworker run --safe`  | **Testing**         | Same as above, but **copies** files instead of moving them.                 |
| `coworker init <path>` | **New Project**     | Creates a dedicated workspace structure with an explicit `Inbox/`.          |
| `coworker setup`       | **Configuration**   | Runs the interactive wizard to customize categories and folder preferences. |
| `coworker status`      | **Monitoring**      | View total files processed, tokens used, and estimated costs.               |
| `coworker doctor`      | **Troubleshooting** | Checks if your API key is set and dependencies are healthy.                 |

## ❓ FAQ

**Q: What if the AI makes a mistake?**
A: Files with low confidence (< 70%) or missing dates/amounts are automatically moved to `Review/` folder. You can rename them and move them to `Organized/` manually.

**Q: Is it safe?**
A: Your files are processed using your own Google Gemini API key. We compute a SHA256 hash locally to cache results, so we never re-send the same file twice to save you money/tokens.

**Q: How do I change settings?**
A: Run `coworker setup` again, or edit `.coworker/config.yml` directly.
