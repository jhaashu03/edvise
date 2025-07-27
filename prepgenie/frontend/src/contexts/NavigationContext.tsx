import React, { createContext, useContext, ReactNode } from 'react';

interface NavigationContextType {
  navCollapsed: boolean;
}

const NavigationContext = createContext<NavigationContextType | undefined>(undefined);

export const useNavigation = () => {
  const context = useContext(NavigationContext);
  if (context === undefined) {
    throw new Error('useNavigation must be used within a NavigationProvider');
  }
  return context;
};

interface NavigationProviderProps {
  children: ReactNode;
  navCollapsed: boolean;
}

export const NavigationProvider: React.FC<NavigationProviderProps> = ({
  children,
  navCollapsed,
}) => {
  return (
    <NavigationContext.Provider value={{ navCollapsed }}>
      {children}
    </NavigationContext.Provider>
  );
};
