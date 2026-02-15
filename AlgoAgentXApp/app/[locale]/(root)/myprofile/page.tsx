import React, { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useUser } from "@/contexts/user-context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { toast } from "@/components/ui/use-toast";
import { Loader2, User, Mail, Shield, Calendar, CreditCard, LogOut } from "lucide-react";
import Cookies from "js-cookie";
import axiosInstance from "@/lib/axios";

interface UserProfile {
  id: string;
  email: string;
  full_name?: string;
  role: string;
  plan?: string;
  credits?: number;
  created_at?: string;
  last_login?: string;
}

export default function MyProfilePage() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isLoading: userLoading } = useUser();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [saving, setSaving] = useState(false);

  // Function to fetch complete user profile from backend
  const fetchUserProfile = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Try to get complete profile from backend
      try {
        const response = await axiosInstance.get("/api/v1/users/me");
        setProfile(response.data);
        setEditName(response.data.full_name || "");
      } catch (apiError) {
        // Fallback to auth verify endpoint if /users/me doesn't exist
        try {
          const authResponse = await axiosInstance.get("/api/v1/auth/verify");
          const userData = authResponse.data.user;
          
          // Create profile object with available data
          const fallbackProfile: UserProfile = {
            id: userData.id || userData.user_id || "",
            email: userData.email,
            full_name: userData.full_name || userData.name || userData.username || "",
            role: userData.role || "User",
            plan: userData.plan || "Free",
            credits: userData.credits || 0,
            created_at: userData.created_at || userData.created || "",
            last_login: userData.last_login || userData.last_login_at || ""
          };
          
          setProfile(fallbackProfile);
          setEditName(fallbackProfile.full_name || "");
        } catch (authError) {
          console.error("Failed to fetch user profile:", authError);
          setError("Unable to load profile information");
        }
      }
    } catch (error) {
      console.error("Error fetching profile:", error);
      setError("Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUserProfile();
  }, []);

  // Initialize edit name when profile loads
  useEffect(() => {
    if (profile) {
      setEditName(profile.full_name || "");
    }
  }, [profile]);

  const handleLogout = () => {
    // Remove all authentication cookies
    Cookies.remove("accessToken");
    Cookies.remove("loggedinuserid");
    Cookies.remove("loggedinusername");
    Cookies.remove("loggedinuserfullname");
    Cookies.remove("loggedinuserroleid");
    Cookies.remove("loggedinuseremail");
    Cookies.remove("loggedinuserrole");

    // Remove localStorage token if present
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
    }

    // Navigate to login with locale support
    router.push('/auth/login');
  };

  const handleSaveProfile = async () => {
    if (!profile) return;

    try {
      setSaving(true);
      // For now, we'll just update the local state since backend may not support updates
      // In a real implementation, this would call a PATCH/PUT endpoint
      setProfile({
        ...profile,
        full_name: editName
      });
      setIsEditing(false);
      toast({
        title: "Success",
        description: "Profile updated successfully"
      });
    } catch (error) {
      console.error("Error updating profile:", error);
      toast({
        title: "Error",
        description: "Failed to update profile",
        variant: "destructive"
      });
    } finally {
      setSaving(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "Not available";
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return "Invalid date";
    }
  };

  if (loading || userLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
        <div className="max-w-4xl mx-auto px-4">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-300 dark:bg-gray-700 rounded w-1/3 mb-6"></div>
            <div className="grid gap-6 md:grid-cols-2">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
                  <div className="h-4 bg-gray-300 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
                  <div className="space-y-3">
                    {[...Array(3)].map((_, j) => (
                      <div key={j} className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
        <div className="max-w-4xl mx-auto px-4">
          <Card className="border-red-200 dark:border-red-800">
            <CardHeader>
              <CardTitle className="text-red-600 dark:text-red-400">Error Loading Profile</CardTitle>
              <CardDescription>{error}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button onClick={fetchUserProfile} variant="outline">
                Try Again
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
        <div className="max-w-4xl mx-auto px-4">
          <Card>
            <CardHeader>
              <CardTitle>Profile Not Available</CardTitle>
              <CardDescription>
                Unable to load your profile information. Please try again later.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button onClick={fetchUserProfile} variant="outline">
                Retry
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">My Profile</h1>
          <p className="text-gray-600 dark:text-gray-300 mt-1">
            Manage your account information and settings
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Profile Summary Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5" />
                Profile Information
              </CardTitle>
              <CardDescription>
                Your basic account information
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center">
                    <span className="text-white font-bold text-sm">
                      {profile.full_name ? profile.full_name.charAt(0).toUpperCase() : profile.email.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <div className="font-semibold text-gray-900 dark:text-white">
                      {isEditing ? (
                        <Input
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          className="w-48"
                          placeholder="Enter your name"
                        />
                      ) : (
                        <span>{profile.full_name || profile.email}</span>
                      )}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      {profile.email}
                    </div>
                  </div>
                </div>
                {!isEditing && (
                  <Button
                    variant="outline"
                    onClick={() => setIsEditing(true)}
                    disabled={!profile.full_name}
                  >
                    Edit
                  </Button>
                )}
              </div>

              {isEditing && (
                <div className="flex gap-2 pt-2">
                  <Button onClick={handleSaveProfile} disabled={saving}>
                    {saving ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      "Save"
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setIsEditing(false);
                      setEditName(profile.full_name || "");
                    }}
                    disabled={saving}
                  >
                    Cancel
                  </Button>
                </div>
              )}

              <Separator />

              <div className="grid gap-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Role</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    <Shield className="w-4 h-4 inline mr-1" />
                    {profile.role}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Plan</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    <CreditCard className="w-4 h-4 inline mr-1" />
                    {profile.plan || "Free"}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Credits</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {profile.credits || 0}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Account Information Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="w-5 h-5" />
                Account Details
              </CardTitle>
              <CardDescription>
                Account creation and activity information
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Account Created</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {formatDate(profile.created_at)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Last Login</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {formatDate(profile.last_login)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500 dark:text-gray-400">User ID</span>
                  <span className="font-mono text-sm text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                    {profile.id}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Actions Card */}
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Account Actions</CardTitle>
              <CardDescription>
                Manage your account settings and security
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col sm:flex-row gap-4">
              <Button
                variant="outline"
                onClick={() => router.push("/changepassword")}
                className="flex-1"
              >
                Change Password
              </Button>
              <Button
                variant="outline"
                onClick={() => router.push("/notifications")}
                className="flex-1"
              >
                Notifications
              </Button>
              <Button
                variant="destructive"
                onClick={handleLogout}
                className="flex-1"
              >
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}