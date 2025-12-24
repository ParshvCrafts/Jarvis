# JARVIS Contact Management Guide

This guide explains how to add and manage contacts in JARVIS so you can easily send WhatsApp messages, make calls, and communicate with your family and friends.

## Quick Start

The easiest way to add contacts is with voice commands:

```
"Add contact Daddy phone +91 9825779760"
"Add contact Mummy phone +1 9515995017"
"Add contact Jeel phone +1 9515908231"
```

## Adding Contacts

### Method 1: Voice Commands (Easiest)

Just speak naturally to JARVIS:

```
"Add contact Daddy phone +91 9825779760"
"Add contact Mummy phone +1 9515995017 email niketaparshv@gmail.com"
"Add contact Jeel phone +1 9515908231"
```

**With nicknames:**
```
"Add contact Dr. Manish Patel nickname Daddy phone +91 9825779760"
```

**With categories:**
```
"Add contact Daddy phone +91 9825779760 category family"
```

### Method 2: Text Commands

Same commands work when typed in JARVIS text mode:

```bash
python run.py --text
```

Then type:
```
Add contact Daddy phone +91 9825779760
```

### Method 3: Command Line (Quick Add)

Add a single contact from the command line:

```bash
python run.py --add-contact "Daddy" "+91 9825779760"
python run.py --add-contact "Mummy" "+1 9515995017" --email "niketaparshv@gmail.com"
```

### Method 4: Interactive Setup

Launch the interactive contact setup wizard:

```bash
python run.py --add-contacts
```

This guides you through adding multiple contacts:

```
=== JARVIS Contact Setup ===

Contact 1:
  Name: Daddy
  Phone: +91 9825779760
  Email (optional): drmanish.patel@yahoo.com
  Category (family/friend/work): family
  Favorite? (y/n): y
  
  ✅ Added Daddy to contacts!

Type 'done' when finished.
```

### Method 5: Import from CSV

1. Create a CSV file with your contacts (see template below)
2. Place it in the JARVIS directory
3. Say: **"Import contacts from contacts.csv"**

**CSV Format:**
```csv
name,nickname,phone,email,category,favorite
Daddy,,+91 9825779760,drmanish.patel@yahoo.com,family,true
Mummy,,+1 9515995017,niketaparshv@gmail.com,family,true
Jeel,Sister,+1 9515908231,,family,true
```

A template file is available at `data/contacts_template.csv`.

### Method 6: Import from vCard

Export contacts from your phone as a .vcf file, then:

```
"Import contacts from my_contacts.vcf"
```

## Managing Contacts

### View Contacts

```
"List my contacts"
"Show my contacts"
"How many contacts do I have?"
```

### Get Contact Info

```
"What's Daddy's number?"
"What's Mummy's email?"
```

### Update Contacts

```
"Update Daddy's phone to +91 9825779761"
"Add email drmanish.patel@yahoo.com to Daddy"
```

### Delete Contacts

```
"Delete contact John"
"Remove contact John"
```

## Favorites

Mark your most important contacts as favorites for quick access:

### Add to Favorites
```
"Add Daddy to favorites"
"Add Mummy to favorites"
```

### Remove from Favorites
```
"Remove John from favorites"
```

### View Favorites
```
"Show my favorite contacts"
"Who are my favorites?"
```

## Recent Contacts

JARVIS tracks who you've contacted recently:

```
"Show my recent contacts"
"Who did I recently contact?"
```

## Smart Matching

JARVIS understands relationship names! If you have a contact named "Daddy", you can also say:

- "Call **Dad**" → Matches "Daddy"
- "Message **Papa**" → Matches "Daddy"  
- "WhatsApp **Father**" → Matches "Daddy"

Same for Mom/Mummy/Mother/Mama, etc.

## Phone Number Format

### Country Codes

Always include the country code for best results:

- **India:** +91 9825779760
- **USA:** +1 9515995017

### Default Country Code

If you don't include a country code, JARVIS uses the default from settings.

**To change the default:**

Edit `config/settings.yaml`:
```yaml
communication:
  contacts:
    default_country_code: "+91"  # Change to your country
```

## Example: Setting Up Family Contacts

Here's a complete example of setting up family contacts:

```bash
# Start JARVIS in text mode
python run.py --text
```

```
You: Add contact Daddy phone +91 9825779760 email drmanish.patel@yahoo.com
JARVIS: Added Daddy to contacts.

You: Add contact Mummy phone +1 9515995017 email niketaparshv@gmail.com
JARVIS: Added Mummy to contacts.

You: Add contact Jeel phone +1 9515908231
JARVIS: Added Jeel to contacts.

You: Add Daddy to favorites
JARVIS: Daddy added to favorites.

You: Add Mummy to favorites
JARVIS: Mummy added to favorites.

You: Add Jeel to favorites
JARVIS: Jeel added to favorites.

You: List my contacts
JARVIS: You have 3 contacts: Daddy, Mummy, Jeel

You: Show my favorite contacts
JARVIS: Your favorite contacts are: Daddy, Mummy, Jeel
```

## Using Contacts

Once contacts are added, use them naturally:

```
"Send WhatsApp to Daddy saying I'll be home soon"
"Call Mummy on WhatsApp"
"What's Jeel's number?"
"Message my sister"  (if Jeel has nickname "Sister")
```

## Troubleshooting

### "Contact not found"

- Check spelling: "List my contacts" to see exact names
- JARVIS will suggest similar names: "Did you mean Daddy?"

### Phone number issues

- Always include country code (+91, +1, etc.)
- Remove spaces and dashes: +919825779760

### Import not working

- Check CSV format matches the template
- Ensure file path is correct
- Check for special characters in names

## Data Location

Contacts are stored in: `data/contacts.db`

This is a SQLite database that persists across sessions.

---

**Need help?** Just ask JARVIS: "How do I add a contact?"
