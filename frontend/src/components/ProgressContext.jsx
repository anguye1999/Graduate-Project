import React, { createContext, useState, useContext } from 'react';

const ProgressContext = createContext();

export const ProgressProvider = ({ children }) => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  
  const refreshProgress = () => {
    setRefreshTrigger(prev => prev + 1);
  };
  
  return (
    <ProgressContext.Provider value={{ refreshTrigger, refreshProgress }}>
      {children}
    </ProgressContext.Provider>
  );
};

export const useProgress = () => useContext(ProgressContext);