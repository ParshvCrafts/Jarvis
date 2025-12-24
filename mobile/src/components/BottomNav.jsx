import { NavLink } from 'react-router-dom'
import { Home, Mic, Cpu, Settings } from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { path: '/', icon: Home, label: 'Home' },
  { path: '/voice', icon: Mic, label: 'Voice' },
  { path: '/devices', icon: Cpu, label: 'Devices' },
  { path: '/settings', icon: Settings, label: 'Settings' },
]

export default function BottomNav() {
  return (
    <nav className="safe-bottom bg-jarvis-card border-t border-jarvis-border">
      <div className="flex items-center justify-around h-16">
        {navItems.map(({ path, icon: Icon, label }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) => clsx(
              'flex flex-col items-center justify-center w-16 h-full gap-1',
              'transition-colors touch-manipulation',
              isActive 
                ? 'text-jarvis-primary' 
                : 'text-jarvis-muted hover:text-jarvis-text'
            )}
          >
            {({ isActive }) => (
              <>
                <div className={clsx(
                  'p-1.5 rounded-lg transition-colors',
                  isActive && 'bg-jarvis-primary/10'
                )}>
                  <Icon className="w-5 h-5" />
                </div>
                <span className="text-[10px] font-medium">{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
