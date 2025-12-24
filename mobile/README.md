# JARVIS Mobile PWA

Progressive Web App for JARVIS AI Assistant.

## Features

- 📱 Mobile-optimized interface
- 🎤 Voice commands with real-time transcription
- 🏠 IoT device control
- 💬 Real-time responses via WebSocket
- 🔔 Push notifications (ntfy.sh)
- 📴 Offline support with service worker
- 🔐 JWT authentication

## Quick Start

### Prerequisites

- Node.js 18+
- JARVIS backend running on port 8000

### Installation

```bash
cd mobile
npm install
```

### Development

```bash
npm run dev
```

Opens at http://localhost:3000

### Production Build

```bash
npm run build
```

Creates optimized build in `dist/` folder.

## Project Structure

```
mobile/
├── public/
│   ├── favicon.svg
│   └── icons/          # PWA icons
├── src/
│   ├── components/     # Reusable UI components
│   │   ├── AppShell.jsx
│   │   ├── Header.jsx
│   │   └── BottomNav.jsx
│   ├── pages/          # Screen components
│   │   ├── Login.jsx
│   │   ├── Home.jsx
│   │   ├── Voice.jsx
│   │   ├── Devices.jsx
│   │   ├── Settings.jsx
│   │   └── History.jsx
│   ├── contexts/       # React contexts
│   │   ├── AuthContext.jsx
│   │   └── ToastContext.jsx
│   ├── services/       # API communication
│   │   ├── api.js
│   │   └── websocket.js
│   ├── hooks/          # Custom React hooks
│   ├── utils/          # Helper functions
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── package.json
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

## Screens

### Home
- Greeting based on time of day
- Quick action buttons
- Recent commands
- System status

### Voice
- Large voice button for recording
- Real-time audio visualization
- Conversation history
- Text input fallback

### Devices
- IoT device list with status
- Device controls (on/off, brightness, lock/unlock)
- Real-time state updates

### Settings
- Account management
- Voice preferences
- Notification settings
- Cache management
- Device management

### History
- Searchable command history
- Re-run previous commands
- Pagination

## PWA Installation

### iOS
1. Open in Safari
2. Tap Share button
3. Select "Add to Home Screen"

### Android
1. Open in Chrome
2. Tap menu (⋮)
3. Select "Add to Home Screen"

## API Endpoints Used

- `POST /api/v1/auth/login` - Authentication
- `POST /api/v1/command` - Send commands
- `GET /api/v1/devices` - List IoT devices
- `POST /api/v1/voice/transcribe` - Speech-to-text
- `WS /api/v1/ws` - Real-time communication

## Configuration

The app connects to the JARVIS API at the same host. In development, Vite proxies `/api` requests to `localhost:8000`.

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **React Router** - Navigation
- **TanStack Query** - Data fetching
- **Lucide React** - Icons
- **Workbox** - Service worker

## Default Credentials

- Username: `admin`
- Password: `jarvis`

Change password after first login!

---

*JARVIS Mobile v1.0.0 - Phase 6*
