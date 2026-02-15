"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  CheckCircle, 
  XCircle, 
  CreditCard,
  Zap,
  Shield,
  Users,
  TrendingUp,
  Calendar,
  Sparkles,
  Star,
  Crown
} from "lucide-react";
import axiosInstance from "@/lib/axios";
import AppShell from "@/components/layout/AppShell";
import RazorpayScript from "@/components/shared/RazorpayScript";

interface PlanFeature {
  name: string;
  free: boolean | string;
  pro: boolean | string;
  premium: boolean | string;
  ultimate: boolean | string;
}

interface Plan {
  code: string;
  billing_period: string;
  price_inr: number;
  included_credits: number;
  features: Record<string, any>;
  is_active: boolean;
}

interface PlanData {
  monthly: Plan[];
  yearly: Plan[];
}

export default function PricingPage() {
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('monthly');
  const [plans, setPlans] = useState<PlanData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const response = await axiosInstance.get('/api/v1/billing/plans');
      
      // Transform the API response to our expected format
      const allPlans = response.data;
      const monthlyPlans = allPlans.filter((plan: Plan) => plan.billing_period === 'MONTHLY');
      const yearlyPlans = allPlans.filter((plan: Plan) => plan.billing_period === 'YEARLY');
      
      setPlans({
        monthly: monthlyPlans,
        yearly: yearlyPlans
      });
    } catch (err: any) {
      console.error('Error fetching plans:', err);
      setError('Failed to load pricing plans. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = async (planCode: string, billingPeriod: string) => {
    try {
      // Check if user is authenticated
      const token = localStorage.getItem('access_token');
      if (!token) {
        router.push('/auth/login');
        return;
      }

      // Create subscription
      const response = await axiosInstance.post('/api/v1/subscriptions/razorpay/create', {
        plan_code: planCode,
        billing_period: billingPeriod
      });

      if (response.data && response.data.subscription_id) {
        // Open Razorpay checkout
        const options = {
          key: response.data.key_id,
          subscription_id: response.data.subscription_id,
          name: 'AlgoAgentX',
          description: `${planCode} Plan - ${billingPeriod}`,
          image: '/algoagentx_icon.jpeg',
          handler: function (response: any) {
            // Success callback
            console.log('Payment successful:', response);
            router.push('/profile');
          },
          prefill: {
            name: '', // Will be filled by Razorpay
            email: '', // Will be filled by Razorpay
            contact: '' // Will be filled by Razorpay
          },
          notes: {
            plan_code: planCode,
            billing_period: billingPeriod
          },
          theme: {
            color: '#2563eb'
          }
        };

        const rzp = new (window as any).Razorpay(options);
        rzp.open();
      }
    } catch (err: any) {
      console.error('Error creating subscription:', err);
      setError('Failed to create subscription. Please try again.');
    }
  };

  const getPlanByCode = (code: string) => {
    if (!plans) return null;
    const currentPlans = billingPeriod === 'monthly' ? plans.monthly : plans.yearly;
    return currentPlans.find(plan => plan.code === code);
  };

  const formatPrice = (price: number) => {
    if (price === 0) return 'Free';
    return `₹${price.toLocaleString()}`;
  };

  const formatCredits = (credits: number) => {
    if (credits === 0) return 'No credits';
    if (credits >= 1000) {
      return `${(credits / 1000).toFixed(1)}K credits`;
    }
    return `${credits} credits`;
  };

  const getFeatureValue = (feature: any, planCode: string) => {
    const plan = getPlanByCode(planCode);
    if (!plan || !plan.features) return false;
    
    // Get the value for this plan from the feature object
    const planKey = planCode.toLowerCase();
    return feature[planKey] || feature.value || feature[planCode] || false;
  };

  const renderFeatureValue = (value: any) => {
    if (typeof value === 'boolean') {
      return value ? (
        <CheckCircle className="h-5 w-5 text-green-500" />
      ) : (
        <XCircle className="h-5 w-5 text-red-500" />
      );
    }
    if (typeof value === 'string' && value.includes('Unlimited')) {
      return <span className="text-green-500 font-medium">{value}</span>;
    }
    if (typeof value === 'number') {
      return <span className="font-medium">{value.toLocaleString()}</span>;
    }
    return <span className="text-gray-600">{value}</span>;
  };

  const features = [
    {
      name: 'Included Credits',
      free: true,
      pro: true,
      premium: true,
      ultimate: true
    },
    {
      name: 'Daily Backtests',
      free: '5',
      pro: '20',
      premium: '50',
      ultimate: 'Unlimited'
    },
    {
      name: 'Daily AI Screener Runs',
      free: '3',
      pro: '10',
      premium: '25',
      ultimate: 'Unlimited'
    },
    {
      name: 'Max Date Range',
      free: '30 days',
      pro: '90 days',
      premium: '1 year',
      ultimate: 'Unlimited'
    },
    {
      name: 'Export Results',
      free: false,
      pro: true,
      premium: true,
      ultimate: true
    },
    {
      name: 'Advanced Strategies',
      free: false,
      pro: true,
      premium: true,
      ultimate: true
    },
    {
      name: 'AI Screener Access',
      free: false,
      pro: true,
      premium: true,
      ultimate: true
    },
    {
      name: 'Priority Support',
      free: false,
      pro: false,
      premium: true,
      ultimate: true
    },
    {
      name: 'Dedicated Account Manager',
      free: false,
      pro: false,
      premium: false,
      ultimate: true
    }
  ];

  if (loading) {
    return (
      <AppShell pageTitle="Pricing">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading pricing plans...</span>
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell pageTitle="Pricing">
        <div className="text-center py-8">
          <div className="text-red-500 mb-4">{error}</div>
          <Button onClick={fetchPlans}>Try Again</Button>
        </div>
      </AppShell>
    );
  }

  return (
    <RazorpayScript>
      <AppShell pageTitle="Pricing">
        <div className="space-y-8">
        {/* Header Section */}
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Choose Your Plan</h1>
          <p className="text-gray-600 text-lg mb-8">
            Start with our free plan or upgrade to unlock premium features and unlimited trading potential
          </p>
          
          {/* Billing Toggle */}
          <div className="flex items-center justify-center space-x-4 mb-8">
            <Button
              variant={billingPeriod === 'monthly' ? 'default' : 'outline'}
              onClick={() => setBillingPeriod('monthly')}
              className="text-gray-700 border-gray-300 hover:bg-gray-50"
            >
              Monthly
            </Button>
            <Button
              variant={billingPeriod === 'yearly' ? 'default' : 'outline'}
              onClick={() => setBillingPeriod('yearly')}
              className="text-gray-700 border-gray-300 hover:bg-gray-50"
            >
              Yearly <span className="text-green-600 ml-2">(Save 20%)</span>
            </Button>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Free Plan */}
          <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-gray-200">
            <CardHeader className="bg-gradient-to-br from-gray-50 to-gray-100 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-gray-900 text-2xl">Free</CardTitle>
                  <CardDescription className="text-gray-600">Get started</CardDescription>
                </div>
                <Badge variant="secondary" className="bg-gray-200 text-gray-700">Basic</Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="text-4xl font-bold text-gray-900 mb-2">
                {formatPrice(0)}
              </div>
              <p className="text-gray-600 text-sm mb-6">No credit card required</p>
              
              <div className="space-y-3 mb-6">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Trial Period</span>
                  <span className="text-green-600 font-medium">7 days</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Included Credits</span>
                  <span className="text-gray-900 font-medium">{formatCredits(100)}</span>
                </div>
              </div>

              <Button 
                className="w-full bg-gray-600 hover:bg-gray-700 text-white mb-4"
                onClick={() => handleSubscribe('FREE', billingPeriod.toUpperCase())}
              >
                <Sparkles className="h-4 w-4 mr-2" />
                Start Free Trial
              </Button>
              
              <Button 
                variant="outline" 
                className="w-full border-gray-300 text-gray-700 hover:bg-gray-50"
                onClick={() => router.push('/dashboard')}
              >
                Continue with Credits
              </Button>
            </CardContent>
          </Card>

          {/* Pro Plan */}
          <Card className="hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-blue-200 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-purple-500"></div>
            <CardHeader className="bg-gradient-to-br from-blue-50 to-purple-50 border-b border-blue-200">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-gray-900 text-2xl">Pro</CardTitle>
                  <CardDescription className="text-blue-700">For serious traders</CardDescription>
                </div>
                <Badge className="bg-blue-600 text-white">Popular</Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="text-4xl font-bold text-gray-900 mb-2">
                {formatPrice(2999)}
              </div>
              <p className="text-gray-600 text-sm mb-6">per month</p>
              
              <div className="space-y-3 mb-6">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Included Credits</span>
                  <span className="text-gray-900 font-medium">{formatCredits(5000)}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Best Value</span>
                  <span className="text-green-600 font-medium">Save 20%</span>
                </div>
              </div>

              <Button 
                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white mb-4"
                onClick={() => handleSubscribe('PRO', billingPeriod.toUpperCase())}
              >
                <CreditCard className="h-4 w-4 mr-2" />
                Buy {billingPeriod === 'monthly' ? 'Monthly' : 'Yearly'}
              </Button>
              
              <Button 
                variant="outline" 
                className="w-full border-blue-200 text-blue-700 hover:bg-blue-50"
                onClick={() => router.push('/dashboard')}
              >
                Continue with Credits
              </Button>
            </CardContent>
          </Card>

          {/* Premium Plan */}
          <Card className="hover:shadow-xl hover:shadow-green-500/10 transition-all duration-300 border-green-200 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-green-500 to-emerald-500"></div>
            <CardHeader className="bg-gradient-to-br from-green-50 to-emerald-50 border-b border-green-200">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-gray-900 text-2xl">Premium</CardTitle>
                  <CardDescription className="text-green-700">For professionals</CardDescription>
                </div>
                <Badge className="bg-green-600 text-white">Advanced</Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="text-4xl font-bold text-gray-900 mb-2">
                {formatPrice(7999)}
              </div>
              <p className="text-gray-600 text-sm mb-6">per month</p>
              
              <div className="space-y-3 mb-6">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Included Credits</span>
                  <span className="text-gray-900 font-medium">{formatCredits(15000)}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Priority Support</span>
                  <span className="text-green-600 font-medium">Included</span>
                </div>
              </div>

              <Button 
                className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white mb-4"
                onClick={() => handleSubscribe('PREMIUM', billingPeriod.toUpperCase())}
              >
                <Shield className="h-4 w-4 mr-2" />
                Buy {billingPeriod === 'monthly' ? 'Monthly' : 'Yearly'}
              </Button>
              
              <Button 
                variant="outline" 
                className="w-full border-green-200 text-green-700 hover:bg-green-50"
                onClick={() => router.push('/dashboard')}
              >
                Continue with Credits
              </Button>
            </CardContent>
          </Card>

          {/* Ultimate Plan */}
          <Card className="hover:shadow-xl hover:shadow-purple-500/10 transition-all duration-300 border-purple-200 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 to-pink-500"></div>
            <CardHeader className="bg-gradient-to-br from-purple-50 to-pink-50 border-b border-purple-200">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-gray-900 text-2xl">Ultimate</CardTitle>
                  <CardDescription className="text-purple-700">For institutions</CardDescription>
                </div>
                <Badge className="bg-purple-600 text-white">Enterprise</Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="text-4xl font-bold text-gray-900 mb-2">
                {formatPrice(19999)}
              </div>
              <p className="text-gray-600 text-sm mb-6">per month</p>
              
              <div className="space-y-3 mb-6">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Included Credits</span>
                  <span className="text-gray-900 font-medium">{formatCredits(50000)}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Dedicated Manager</span>
                  <span className="text-purple-600 font-medium">Included</span>
                </div>
              </div>

              <Button 
                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white mb-4"
                onClick={() => handleSubscribe('ULTIMATE', billingPeriod.toUpperCase())}
              >
                <Crown className="h-4 w-4 mr-2" />
                Buy {billingPeriod === 'monthly' ? 'Monthly' : 'Yearly'}
              </Button>
              
              <Button 
                variant="outline" 
                className="w-full border-purple-200 text-purple-700 hover:bg-purple-50"
                onClick={() => router.push('/dashboard')}
              >
                Continue with Credits
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Feature Comparison Table */}
        <Card className="border-gray-200">
          <CardHeader>
            <CardTitle className="text-gray-900">Feature Comparison</CardTitle>
            <CardDescription className="text-gray-600">
              Compare all features across our plans
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left text-gray-600 py-3 px-4">Features</th>
                    <th className="text-center text-gray-600 py-3 px-4">Free</th>
                    <th className="text-center text-gray-600 py-3 px-4">Pro</th>
                    <th className="text-center text-gray-600 py-3 px-4">Premium</th>
                    <th className="text-center text-gray-600 py-3 px-4">Ultimate</th>
                  </tr>
                </thead>
                <tbody>
                  {features.map((feature, index) => (
                    <tr key={index} className="border-b border-gray-100">
                      <td className="py-4 px-4 text-gray-900 font-medium">{feature.name}</td>
                      <td className="py-4 px-4 text-center">
                        {renderFeatureValue(getFeatureValue(feature, 'FREE'))}
                      </td>
                      <td className="py-4 px-4 text-center">
                        {renderFeatureValue(getFeatureValue(feature, 'PRO'))}
                      </td>
                      <td className="py-4 px-4 text-center">
                        {renderFeatureValue(getFeatureValue(feature, 'PREMIUM'))}
                      </td>
                      <td className="py-4 px-4 text-center">
                        {renderFeatureValue(getFeatureValue(feature, 'ULTIMATE'))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Credit-Only Section */}
        <Card className="border-gray-200 bg-gradient-to-r from-blue-50 to-purple-50">
          <CardHeader>
            <CardTitle className="text-gray-900 flex items-center">
              <CreditCard className="h-6 w-6 mr-2 text-gray-700" />
              Credit-Only Option
            </CardTitle>
            <CardDescription className="text-gray-600">
              Prefer to pay per usage? Buy credits and pay only for what you use.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-6 bg-white rounded-xl border border-gray-200">
                <div className="text-3xl font-bold text-blue-600 mb-2">₹100</div>
                <div className="text-gray-600 mb-4">100 Credits</div>
                <Button variant="outline" className="border-blue-200 text-blue-700 hover:bg-blue-50">
                  Buy Now
                </Button>
              </div>
              <div className="text-center p-6 bg-white rounded-xl border border-gray-200">
                <div className="text-3xl font-bold text-green-600 mb-2">₹500</div>
                <div className="text-gray-600 mb-4">600 Credits</div>
                <Button variant="outline" className="border-green-200 text-green-700 hover:bg-green-50">
                  Buy Now
                </Button>
              </div>
              <div className="text-center p-6 bg-white rounded-xl border border-gray-200">
                <div className="text-3xl font-bold text-purple-600 mb-2">₹2000</div>
                <div className="text-gray-600 mb-4">2500 Credits</div>
                <Button variant="outline" className="border-purple-200 text-purple-700 hover:bg-purple-50">
                  Buy Now
                </Button>
              </div>
            </div>
            <div className="mt-4 text-sm text-gray-600 text-center">
              Credits never expire and can be used for backtests, AI screener runs, and other premium features.
            </div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
    </RazorpayScript>
  );
}


