import { createContext, useContext, ReactNode } from 'react';

// Stubbing ThemeContext to always return dark mode for backward compatibility with Dashboard pages
const ThemeContext = createContext({
  isDark: true,
  toggleTheme: () => {}
});

export function ThemeProvider({ children }: { children: ReactNode }) {
  return (
    <ThemeContext.Provider value={{ isDark: true, toggleTheme: () => {} }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
