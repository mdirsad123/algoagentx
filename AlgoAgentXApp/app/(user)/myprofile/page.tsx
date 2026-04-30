"use client";

import React, { useState, useEffect } from "react";
import { User, Mail, Calendar, Shield, LogOut, Edit2, Save, X } from "lucide-react";
import { useUser } from "@/contexts/user-context";
import axiosInstance from "@/lib/axios";
import { toast } from "sonner";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";

interface UserProfile {
  id: string;
  email: string;
  role: string;
  full_name?: string;
  name?: string;
  username?: string;
  plan?: string;
  credits?: number;
  created_at: string;
  last_login?: string;
}

export default function MyProfilePage() {
  const { user, isLoading: userLoading } = useUser();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState("");
  const [saving, setSaving] = useState(false);
  const router = useRouter();

  // Fetch user profile data
  const fetchProfile = async () => {
    try {
      setLoading(true);
      // Try to get from /users/me first, fallback to /auth/verify
      let response;
      try {
        response = await axiosInstance.get("/api/v1/users/me");
        setProfile(response.data);
      } catch (error: any) {
        if (error.response?.status === 404) {
          // Fallback to auth verify endpoint
          response = await axiosInstance.get("/api/v1/auth/verify");
          const userData = response.data.user;
          setProfile({
            id: userData.id,
            email: userData.email,
            role: userData.role || "User",
            full_name: userData.full_name || userData.name || userData.username,
            created_at: userData.created_at || new Date().toISOString(),
            plan: userData.plan || "Free",
            credits: userData.credits || 0,
          });
        } else {
          throw error;
        }
      }
      
      if (profile?.full_name || profile?.name) {
        setEditedName(profile.full_name || profile.name || "");
      }
    } catch (error) {
      console.error("Failed to fetch profile:", error);
      toast.error("Failed to load profile data");
      // Fallback to cookie data
      const cookieEmail = Cookies.get("loggedinuseremail");
      const cookieName = Cookies.get("loggedinuserfullname") || Cookies.get("loggedinusername");
      const cookieRole = Cookies.get("loggedinuserrole");
      
      if (cookieEmail) {
        setProfile({
          id: "unknown",
          email: cookieEmail,
          role: cookieRole || "User",
          full_name: cookieName,
          created_at: new Date().toISOString(),
          plan: "Free",
          credits: 0,
        });
        setEditedName(cookieName || "");
      }
    } finally {
      setLoading(false);
    }
  };

  // Save profile changes
  const handleSaveProfile = async () => {
    if (!profile) return;
    
    try {
      setSaving(true);
      await axiosInstance.patch("/api/v1/users/me", {
        full_name: editedName.trim() || null
      });
      
      setProfile({
        ...profile,
        full_name: editedName.trim() || undefined
      });
      
      setIsEditing(false);
      toast.success("Profile updated successfully");
    } catch (error) {
      console.error("Failed to update profile:", error);
      toast.error("Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  // Logout function
  const handleLogout = () => {
    // Remove all authentication data
    Cookies.remove("accessToken");
    Cookies.remove("loggedinuserid");
    Cookies.remove("loggedinusername");
    Cookies.remove("loggedinuserfullname");
    Cookies.remove("loggedinuserroleid");
    Cookies.remove("loggedinuseremail");
    Cookies.remove("loggedinuserrole");

    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
    }

    toast.success("Logged out successfully");
    router.push('/auth/login');
  };

  useEffect(() => {
    if (!userLoading) {
      fetchProfile();
    }
  }, [userLoading]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <div className="text-gray-500">Failed to load profile data</div>
        <button 
          onClick={fetchProfile}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  const displayName = profile.full_name || profile.name || profile.username || profile.email;
  const avatarLetter = displayName.charAt(0).toUpperCase();

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">My Profile</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Manage your account settings and preferences</p>
        </div>

        {/* Profile Content */}
        <div className="p-6">
          <div className="flex items-start gap-6">
            
            {/* Avatar */}
            <div className="flex-shrink-0">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center">
                <span className="text-white font-bold text-2xl">{avatarLetter}</span>
              </div>
            </div>

            {/* Profile Info */}
            <div className="flex-1 space-y-6">
              
              {/* Basic Info */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* Name Field */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <User className="w-4 h-4 inline mr-2" />
                    Full Name
                  </label>
                  {isEditing ? (
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={editedName}
                        onChange={(e) => setEditedName(e.target.value)}
                        className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="Enter your full name"
                      />
                      <button
                        onClick={handleSaveProfile}
                        disabled={saving}
                        className="px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                      >
                        {saving ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Save className="w-4 h-4" />}
                      </button>
                      <button
                        onClick={() => {
                          setIsEditing(false);
                          setEditedName(profile.full_name || profile.name || "");
                        }}
                        className="px-3 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white flex-1">
                        {displayName}
                      </span>
                      <button
                        onClick={() => setIsEditing(true)}
                        className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>

                {/* Email */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <Mail className="w-4 h-4 inline mr-2" />
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={profile.email}
                    disabled
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-gray-500 dark:text-gray-400 cursor-not-allowed"
                  />
                </div>

                {/* Role */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <Shield className="w-4 h-4 inline mr-2" />
                    Role
                  </label>
                  <input
                    type="text"
                    value={profile.role}
                    disabled
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-gray-500 dark:text-gray-400 cursor-not-allowed"
                  />
                </div>

                {/* Plan */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Plan
                  </label>
                  <div className="flex items-center gap-2">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      profile.plan === "Pro" ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400" :
                      profile.plan === "Trial" ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400" :
                      "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
                    }`}>
                      {profile.plan || "Free"}
                    </span>
                    {profile.credits !== undefined && (
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {profile.credits} credits
                      </span>
                    )}
                  </div>
                </div>

              </div>

              {/* Account Details */}
              <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Account Information</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      <Calendar className="w-4 h-4 inline mr-2" />
                      Member Since
                    </label>
                    <span className="text-gray-900 dark:text-white">
                      {new Date(profile.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  {profile.last_login && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Last Login
                      </label>
                      <span className="text-gray-900 dark:text-white">
                        {new Date(profile.last_login).toLocaleDateString()}
                      </span>
                    </div>
                  )}

                </div>
              </div>

              {/* Actions */}
              <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
                <div className="flex gap-4">
                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    Logout
                  </button>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>
  );
}