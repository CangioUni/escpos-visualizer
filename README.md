# ESC/POS Visualizer

A lightweight web-based ESC/POS receipt visualizer for quickly testing and debugging applications that use `python-escpos` or raw ESC/POS commands.

> **Status:** This project was vibe-coded and works acceptably for its intended purpose, but no future updates are guaranteed.

## Features

- Visualize ESC/POS receipt output in a web interface
- Useful for debugging apps built with `python-escpos`
- Can also be used with general/raw ESC/POS commands
- Fast feedback loop without wasting receipt paper
- Supports the main text formatting functions commonly used in receipts
- Helpful for testing receipt layout and impagination before using a physical printer

## How to Run

### Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### PM2 configuration

Use the following PM2 app configuration:

```javascript
{
  name: 'escpos-visualizer',
  cwd: '/home/python/escpos-visualizer/',
  script: 'app.py',
  watch: true,
  interpreter: '/home/python/escpos-visualizer/.venv/bin/python',
  interpreter_args: '-u'
}
```

## Limitations

- The rendered output is **not guaranteed** to match a real physical printer 1:1
- Focused on practical debugging rather than perfect hardware-accurate emulation
- Support is centered on core text formatting behavior

## Use Cases

- Debug receipt generation during development
- Preview bills/receipts in the browser
- Test layout changes without printing on paper
- Validate basic ESC/POS formatting commands quickly

## Disclaimer

This tool is intended as a practical and fast debugging aid. It is especially useful when you want to avoid consuming bill/receipt rolls for routine tests, but it should not be treated as an exact simulator of a real ESC/POS printer.
