import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";
import axiosInstance from "@/lib/axios";
import Cookies from "js-cookie";

interface User {
  id: string;
  email: string;
  role: string;
  displayName?: string;
  fullname?: string;
  username?: string;
}

interface UserContextType {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  fetchUser: () => Promise<void>;
  clearUser: () => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const useUser = () => {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};

interface UserProviderProps {
  children: ReactNode;
}

export const UserProvider: React.FC<UserProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchUser = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Check if we have cached user data in localStorage
      const cachedUser = localStorage.getItem('currentUser');
      if (cachedUser) {
        try {
          const parsedUser = JSON.parse(cachedUser);
          setUser(parsedUser);
        } catch (e) {
          // Invalid cached data, remove it
          localStorage.removeItem('currentUser');
        }
      }

      // Fetch fresh user data from API
      const response = await axiosInstance.get("/api/v1/users/me");
      const userData: User = response.data;
      
      // Enhance user data with full name from cookies if available
      const fullname = Cookies.get("loggedinuserfullname");
      const username = Cookies.get("loggedinusername");
      
      const enhancedUser = {
        ...userData,
        displayName: fullname || username || userData.email,
        fullname: fullname,
        username: username
      };
      
      setUser(enhancedUser);
      
      // Cache enhanced user data in localStorage for faster loading
      localStorage.setItem('currentUser', JSON.stringify(enhancedUser));
      
    } catch (err) {
      setError('Failed to fetch user information');
      console.error('Error fetching user:', err);
      
      // If API fails, try to get user info from cookies as fallback
      const email = Cookies.get("loggedinuseremail");
      const role = Cookies.get("loggedinuserrole") || "User";
      const userId = Cookies.get("loggedinuserid");
      const fullname = Cookies.get("loggedinuserfullname");
      const username = Cookies.get("loggedinusername");
      
      if (email && userId) {
        const fallbackUser = {
          id: userId,
          email: email,
          role: role,
          displayName: fullname || username || email,
          fullname: fullname,
          username: username
        };
        setUser(fallbackUser);
        localStorage.setItem('currentUser', JSON.stringify(fallbackUser));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const clearUser = () => {
    setUser(null);
    localStorage.removeItem('currentUser');
  };

  // Initial fetch
  useEffect(() => {
    fetchUser();
  }, []);

  const value: UserContextType = {
    user,
    isLoading,
    error,
    fetchUser,
    clearUser,
  };

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
};