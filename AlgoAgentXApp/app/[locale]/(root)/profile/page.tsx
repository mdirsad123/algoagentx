"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { User, Mail, Shield, Settings, Bell, CreditCard, Activity, TrendingUp } from "lucide-react";
import AppShell from "@/components/layout/AppShell";

interface UserProfile {
  name: string;
  email: string;
  role: string;
  joinDate: string;
  lastLogin: string;
  subscription: string;
  notifications: boolean;
  twoFactor: boolean;
  apiKeys: number;
  totalTrades: number;
  totalProfit: number;
  winRate: number;
}

export default function ProfilePage() {
  const [user, setUser] = useState<UserProfile>({
    name: "John Doe",
    email: "john.doe@algoagentx.com",
    role: "Admin",
    joinDate: "2024-01-15",
    lastLogin: "2024-12-05 14:30:00",
    subscription: "Premium",
    notifications: true,
    twoFactor: true,
    apiKeys: 3,
    totalTrades: 1234,
    totalProfit: 45200.50,
    winRate: 67.1
  });

  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    name: user.name,
    email: user.email
  });

  const handleEdit = () => {
    setIsEditing(true);
    setFormData({
      name: user.name,
      email: user.email
    });
  };

  const handleSave = () => {
    setUser({
      ...user,
      name: formData.name,
      email: formData.email
    });
    setIsEditing(false);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setFormData({
      name: user.name,
      email: user.email
    });
  };

  return (
    <AppShell pageTitle="Profile">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Profile Settings</h1>
            <p className="text-gray-600 mt-2">Manage your account and preferences</p>
          </div>
          <div className="hidden md:flex items-center space-x-4">
            <Badge variant="default" className="text-sm font-medium bg-gradient-to-r from-blue-600 to-purple-600 text-white">
              {user.subscription} Plan
            </Badge>
            <Badge variant="outline" className="text-sm text-gray-600 border-gray-300">
              {user.role}
            </Badge>
          </div>
        </div>

        {/* Main Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Profile Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Profile Card */}
            <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
              <CardHeader>
                <CardTitle className="text-gray-900">Personal Information</CardTitle>
                <CardDescription className="text-gray-600">
                  Update your account details and preferences
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center space-x-6">
                  <div className="w-20 h-20 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full flex items-center justify-center">
                    <User className="w-10 h-10 text-white" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">{user.name}</h2>
                    <p className="text-gray-600">{user.email}</p>
                    <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                      <span>Member since {user.joinDate}</span>
                      <span>•</span>
                      <span>Last login: {user.lastLogin}</span>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="name" className="text-gray-700">Full Name</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) => setFormData({...formData, name: e.target.value})}
                      disabled={!isEditing}
                      className="bg-white border-gray-200 text-gray-900 placeholder-gray-400"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-gray-700">Email Address</Label>
                    <Input
                      id="email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({...formData, email: e.target.value})}
                      disabled={!isEditing}
                      className="bg-white border-gray-200 text-gray-900 placeholder-gray-400"
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  {isEditing ? (
                    <>
                      <Button onClick={handleSave} className="bg-green-600 hover:bg-green-700 text-white">
                        Save Changes
                      </Button>
                      <Button variant="outline" onClick={handleCancel} className="border-gray-300 text-gray-700 hover:bg-gray-50">
                        Cancel
                      </Button>
                    </>
                  ) : (
                    <Button onClick={handleEdit} className="bg-blue-600 hover:bg-blue-700 text-white">
                      Edit Profile
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Account Stats */}
            <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
              <CardHeader>
                <CardTitle className="text-gray-900">Account Statistics</CardTitle>
                <CardDescription className="text-gray-600">
                  Your trading performance and activity
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl border border-gray-200">
                    <div className="flex items-center justify-center w-12 h-12 bg-blue-500 rounded-full mx-auto mb-3">
                      <Activity className="w-6 h-6 text-white" />
                    </div>
                    <div className="text-2xl font-bold text-gray-900">{user.totalTrades.toLocaleString()}</div>
                    <div className="text-sm text-gray-600">Total Trades</div>
                  </div>
                  <div className="text-center p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl border border-gray-200">
                    <div className="flex items-center justify-center w-12 h-12 bg-green-500 rounded-full mx-auto mb-3">
                      <TrendingUp className="w-6 h-6 text-white" />
                    </div>
                    <div className="text-2xl font-bold text-gray-900">${user.totalProfit.toLocaleString()}</div>
                    <div className="text-sm text-gray-600">Total Profit</div>
                  </div>
                  <div className="text-center p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl border border-gray-200">
                    <div className="flex items-center justify-center w-12 h-12 bg-purple-500 rounded-full mx-auto mb-3">
                      <TrendingUp className="w-6 h-6 text-white" />
                    </div>
                    <div className="text-2xl font-bold text-gray-900">{user.winRate}%</div>
                    <div className="text-sm text-gray-600">Win Rate</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Settings */}
          <div className="space-y-6">
            {/* Security Settings */}
            <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
              <CardHeader>
                <CardTitle className="text-gray-900">Security</CardTitle>
                <CardDescription className="text-gray-600">
                  Manage your account security settings
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl border border-gray-200">
                  <div className="flex items-center space-x-3">
                    <Shield className="w-5 h-5 text-blue-600" />
                    <div>
                      <div className="font-medium text-gray-900">Two-Factor Authentication</div>
                      <div className="text-sm text-gray-600">Add an extra layer of security</div>
                    </div>
                  </div>
                  <Badge variant={user.twoFactor ? "default" : "secondary"} className="bg-green-100 text-green-800 border-green-200">
                    {user.twoFactor ? "Enabled" : "Disabled"}
                  </Badge>
                </div>

                <div className="flex items-center justify-between p-4 bg-gradient-to-r from-yellow-50 to-orange-50 rounded-xl border border-gray-200">
                  <div className="flex items-center space-x-3">
                    <Bell className="w-5 h-5 text-yellow-600" />
                    <div>
                      <div className="font-medium text-gray-900">Email Notifications</div>
                      <div className="text-sm text-gray-600">Receive important updates</div>
                    </div>
                  </div>
                  <Badge variant={user.notifications ? "default" : "secondary"} className="bg-green-100 text-green-800 border-green-200">
                    {user.notifications ? "Enabled" : "Disabled"}
                  </Badge>
                </div>

                <div className="flex items-center justify-between p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl border border-gray-200">
                  <div className="flex items-center space-x-3">
                    <CreditCard className="w-5 h-5 text-green-600" />
                    <div>
                      <div className="font-medium text-gray-900">API Keys</div>
                      <div className="text-sm text-gray-600">Active API connections</div>
                    </div>
                  </div>
                  <Badge variant="outline" className="border-gray-300 text-gray-700">
                    {user.apiKeys} keys
                  </Badge>
                </div>

                <div className="space-y-3">
                  <Button variant="outline" className="w-full border-gray-300 text-gray-700 hover:bg-gray-50">
                    <Settings className="w-4 h-4 mr-2 text-gray-600" />
                    Change Password
                  </Button>
                  <Button variant="outline" className="w-full border-gray-300 text-gray-700 hover:bg-gray-50">
                    <Shield className="w-4 h-4 mr-2 text-gray-600" />
                    Manage API Keys
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Subscription Info */}
            <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
              <CardHeader>
                <CardTitle className="text-gray-900">Subscription</CardTitle>
                <CardDescription className="text-gray-600">
                  Your current plan and billing
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-gray-900">{user.subscription} Plan</div>
                    <div className="text-sm text-gray-600">Premium features included</div>
                  </div>
                  <Badge variant="default" className="bg-green-100 text-green-800 border-green-200">
                    Active
                  </Badge>
                </div>

                <div className="space-y-2 text-sm text-gray-600">
                  <div className="flex justify-between">
                    <span>Next billing date:</span>
                    <span className="text-gray-900">Jan 15, 2025</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Monthly limit:</span>
                    <span className="text-gray-900">Unlimited</span>
                  </div>
                  <div className="flex justify-between">
                    <span>API calls:</span>
                    <span className="text-gray-900">12,345 / ∞</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <Button variant="outline" className="w-full border-gray-300 text-gray-700 hover:bg-gray-50">
                    View Billing History
                  </Button>
                  <Button variant="outline" className="w-full border-gray-300 text-gray-700 hover:bg-gray-50">
                    Upgrade Plan
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
              <CardHeader>
                <CardTitle className="text-gray-900">Quick Actions</CardTitle>
                <CardDescription className="text-gray-600">
                  Common account tasks
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button variant="outline" className="w-full justify-start border-gray-300 text-gray-700 hover:bg-gray-50">
                  <Settings className="w-4 h-4 mr-3 text-gray-600" />
                  Account Settings
                </Button>
                <Button variant="outline" className="w-full justify-start border-gray-300 text-gray-700 hover:bg-gray-50">
                  <Bell className="w-4 h-4 mr-3 text-gray-600" />
                  Notification Preferences
                </Button>
                <Button variant="outline" className="w-full justify-start border-gray-300 text-gray-700 hover:bg-gray-50">
                  <Shield className="w-4 h-4 mr-3 text-gray-600" />
                  Security Settings
                </Button>
                <Button variant="outline" className="w-full justify-start border-gray-300 text-gray-700 hover:bg-gray-50">
                  <Activity className="w-4 h-4 mr-3 text-gray-600" />
                  Activity Log
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </AppShell>
  );
}


