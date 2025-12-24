# JARVIS Communication System

This document describes the communication features in JARVIS, including contacts management, WhatsApp automation, and keyboard shortcut activation.

## Features

### 1. Contacts Management

Store and manage contacts for communication features.

**Voice Commands:**
```
"Add contact John phone 9876543210"
"Add contact Papa phone +1 555-123-4567"
"Delete contact John"
"List my contacts"
"What's Papa's number?"
```

**Features:**
- SQLite database storage
- Nickname support for voice recognition (e.g., "Papa", "Mom")
- Country code handling (default: +1 for US)
- Category organization (family, friend, work)
- Favorite contacts
- CSV and vCard import

### 2. WhatsApp Automation

Send WhatsApp messages and make calls via WhatsApp Web.

**Voice Commands:**
```
"Send WhatsApp message to Papa saying I'll be late"
"WhatsApp Mom that I reached safely"
"Message John on WhatsApp hello"
"Call Papa on WhatsApp"
"Video call Mom on WhatsApp"
```

**How it works:**
1. JARVIS resolves the contact name to a phone number
2. Opens WhatsApp Web with the message pre-filled
3. User clicks send (or auto-send if enabled)

**Note:** You must be logged into WhatsApp Web in your browser for this to work.

### 3. Keyboard Shortcut Activation (Win+J)

Activate JARVIS instantly with a keyboard shortcut.

**Default Shortcuts:**
- **Windows:** `Win+J`
- **macOS:** `Cmd+J`
- **Linux:** `Ctrl+Alt+J`

**How it works:**
1. Press the hotkey combination
2. JARVIS plays activation sound
3. JARVIS enters conversation mode and says "Yes?"
4. Speak your command

## Configuration

Add to `config/settings.yaml`:

```yaml
communication:
  # Contacts Management
  contacts:
    enabled: true
    db_path: "data/contacts.db"
    default_country_code: "+1"  # US = +1, India = +91
  
  # WhatsApp Automation
  whatsapp:
    enabled: true
    auto_send: false  # If true, auto-click send (requires Playwright)
    use_web_whatsapp: true
    confirm_before_send: true  # Ask before sending
  
  # Keyboard Shortcut
  hotkey:
    enabled: true
    key_combination: "win+j"
    play_sound: true
```

## Usage Examples

### Adding Contacts

```
You: "Add contact Papa phone 9876543210"
JARVIS: "Added Papa to contacts"

You: "Add contact Mom phone +91 9876543211"
JARVIS: "Added Mom to contacts"
```

### Sending WhatsApp Messages

```
You: "Send WhatsApp message to Papa saying I'll be late"
JARVIS: "I'll send 'I'll be late' to Papa on WhatsApp. Should I send it?"
You: "Yes"
JARVIS: "Opening WhatsApp to send message to Papa. Please click send."
```

### Making WhatsApp Calls

```
You: "Call Mom on WhatsApp"
JARVIS: "Opening WhatsApp chat with Mom. Click the voice call button to start the call."

You: "Video call Papa on WhatsApp"
JARVIS: "Opening WhatsApp chat with Papa. Click the video call button to start the call."
```

### Using Keyboard Shortcut

```
[Press Win+J]
JARVIS: *activation sound* "Yes?"
You: "What's the weather?"
JARVIS: "The weather in..."
```

## Importing Contacts

### From CSV

Export contacts from Google Contacts or other services as CSV, then:

```python
from src.communication import ContactsManager

manager = ContactsManager("data/contacts.db")
imported, skipped, msg = manager.import_contacts("contacts.csv")
print(msg)  # "Imported 50 contacts successfully"
```

Expected CSV columns: `Name`, `Phone`, `Email`, `Nickname`, `Category`

### From vCard

```python
manager.import_contacts("contacts.vcf")
```

## API Reference

### ContactsManager

```python
from src.communication import ContactsManager

manager = ContactsManager(
    db_path="data/contacts.db",
    default_country_code="+1"
)

# Add contact
success, msg = manager.add_contact(
    name="John Doe",
    phone="5551234567",
    email="john@example.com",
    nickname="John",
    category="friend"
)

# Get phone number
phone, msg = manager.get_phone_number("John")

# Search contacts
contacts = manager.search_contacts("John")

# List all contacts
contacts = manager.list_contacts()

# Delete contact
success, msg = manager.delete_contact("John")
```

### WhatsAppService

```python
from src.communication import ContactsManager, WhatsAppService

contacts = ContactsManager("data/contacts.db")
whatsapp = WhatsAppService(contacts)

# Send message
result = whatsapp.send_message("Papa", "I'll be late")
print(result.message)  # "Opening WhatsApp..."

# Make call
result = whatsapp.make_call("Mom", video=False)

# Video call
result = whatsapp.make_call("Papa", video=True)
```

### HotkeyListener

```python
from src.communication import HotkeyListener

def on_activate():
    print("JARVIS activated!")

listener = HotkeyListener(
    hotkey="win+j",
    callback=on_activate
)

listener.start()
# ... listener runs in background
listener.stop()
```

## Troubleshooting

### WhatsApp not opening
- Make sure you're logged into WhatsApp Web in your default browser
- Check that the phone number has the correct country code

### Hotkey not working
- On Windows, run JARVIS as administrator for global hotkey access
- Check if another application is using the same hotkey
- Try a different key combination in settings

### Contact not found
- Check the exact spelling of the name or nickname
- Use `list my contacts` to see all saved contacts
- Try adding the contact again

## Dependencies

- `keyboard>=0.13.5` - For global hotkey detection (optional)
- Standard library: `sqlite3`, `webbrowser`, `urllib`

Install keyboard library:
```bash
pip install keyboard
```

## Security Notes

- Contacts are stored locally in SQLite database
- Phone numbers are stored with country codes
- WhatsApp messages are sent via browser (no API access to your WhatsApp)
- Confirmation is required before sending messages (configurable)
