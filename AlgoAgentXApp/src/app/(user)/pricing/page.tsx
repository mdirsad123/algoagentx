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
          image: '/images/algoagentx_icon.jpeg',
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
            color: '#8b5cf6'
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
        <XCircle className="h-5 w-5 text-red-500/50" />
      );
    }
    if (typeof value === 'string' && value.includes('Unlimited')) {
      return <span className="text-green-400 font-medium">{value}</span>;
    }
    if (typeof value === 'number') {
      return <span className="font-medium text-white">{value.toLocaleString()}</span>;
    }
    return <span className="text-gray-400">{value}</span>;
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
      <div className="min-h-screen bg-gradient-to-br from-[#1a0f2e] via-[#2a1458] to-[#0f172a] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
          <span className="text-gray-400">Loading pricing plans...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#1a0f2e] via-[#2a1458] to-[#0f172a] flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-400 mb-4">{error}</div>
          <Button onClick={fetchPlans} className="bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600">
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <RazorpayScript>
      <div className="min-h-screen bg-gradient-to-br from-[#1a0f2e] via-[#2a1458] to-[#0f172a]">
        <div className="space-y-8 p-6">
        {/* Header Section */}
        <div className="text-center">
          <h1 className="text-4xl font-bold text-white mb-4">Choose Your Plan</h1>
          <p className="text-gray-400 text-lg mb-8">
            Start with our free plan or upgrade to unlock premium features and unlimited trading potential
          </p>
          
          {/* Billing Toggle */}
          <div className="flex items-center justify-center space-x-4 mb-8">
            <Button
              variant={billingPeriod === 'monthly' ? 'default' : 'outline'}
              onClick={() => setBillingPeriod('monthly')}
              className={`px-6 ${
                billingPeriod === 'monthly' 
                  ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white' 
                  : 'border-white/20 text-gray-300 hover:bg-white/10 hover:border-white/40'
              }`}
            >
              Monthly
            </Button>
            <Button
              variant={billingPeriod === 'yearly' ? 'default' : 'outline'}
              onClick={() => setBillingPeriod('yearly')}
              className={`px-6 ${
                billingPeriod === 'yearly' 
                  ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white' 
                  : 'border-white/20 text-gray-300 hover:bg-white/10 hover:border-white/40'
              }`}
            >
              Yearly <span className="text-green-400 ml-2">(Save 20%)</span>
            </Button>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Free Plan */}
          <Card className="hover:shadow-xl hover:shadow-purple-500/10 transition-all duration-300 border-white/10 bg-white/5 backdrop-blur-lg rounded-2xl">
            <CardHeader className="bg-gradient-to-br from-white/10 to-white/5 border-b border-white/10">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-white text-2xl">Free</CardTitle>
                  <CardDescription className="text-gray-400">Get started</CardDescription>
                </div>
                <Badge variant="secondary" className="bg-white/10 text-gray-300">Basic</Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="text-4xl font-bold text-white mb-2">
                {formatPrice(0)}
              </div>
              <p className="text-gray-400 text-sm mb-6">No credit card required</p>
              
              <div className="space-y-3 mb-6">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Trial Period</span>
                  <span className="text-green-400 font-medium">7 days</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Included Credits</span>
                  <span className="text-white font-medium">{formatCredits(100)}</span>
                </div>
              </div>

              <Button 
                className="w-full bg-gray-600/50 hover:bg-gray-600 text-white mb-4 border-white/20"
                onClick={() => handleSubscribe('FREE', billingPeriod.toUpperCase())}
              >
                <Sparkles className="h-4 w-4 mr-2" />
                Start Free Trial
              </Button>
              
              <Button 
                variant="outline" 
                className="w-full border-white/20 text-gray-300 hover:bg-white/10 hover:border-white/40"
                onClick={() => router.push('/dashboard')}
              >
                Continue with Credits
              </Button>
            </CardContent>
          </Card>

          {/* Pro Plan */}
          <Card className="hover:shadow-xl hover:shadow-blue-500/20 transition-all duration-300 border-blue-500/30 relative overflow-hidden bg-white/5 backdrop-blur-lg rounded-2xl">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-purple-500"></div>
            <CardHeader className="bg-gradient-to-br from-blue-900/30 to-purple-900/30 border-b border-blue-500/20">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-white text-2xl">Pro</CardTitle>
                  <CardDescription className="text-blue-300">For serious traders</CardDescription>
                </div>
                <Badge className="bg-blue-500 text-white">Popular</Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="text-4xl font-bold text-white mb-2">
                {formatPrice(2999)}
              </div>
              <p className="text-gray-400 text-sm mb-6">per month</p>
              
              <div className="space-y-3 mb-6">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Included Credits</span>
                  <span className="text-white font-medium">{formatCredits(5000)}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Best Value</span>
                  <span className="text-green-400 font-medium">Save 20%</span>
                </div>
              </div>

              <Button 
                className="w-full bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white mb-4 shadow-lg"
                onClick={() => handleSubscribe('PRO', billingPeriod.toUpperCase())}
              >
                <CreditCard className="h-4 w-4 mr-2" />
                Buy {billingPeriod === 'monthly' ? 'Monthly' : 'Yearly'}
              </Button>
              
              <Button 
                variant="outline" 
                className="w-full border-blue-500/30 text-blue-300 hover:bg-blue-900/30 hover:border-blue-500/50"
                onClick={() => router.push('/dashboard')}
              >
                Continue with Credits
              </Button>
            </CardContent>
          </Card>

          {/* Premium Plan */}
          <Card className="hover:shadow-xl hover:shadow-green-500/20 transition-all duration-300 border-green-500/30 relative overflow-hidden bg-white/5 backdrop-blur-lg rounded-2xl">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-green-500 to-emerald-500"></div>
            <CardHeader className="bg-gradient-to-br from-green-900/30 to-emerald-900/30 border-b border-green-500/20">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-white text-2xl">Premium</CardTitle>
                  <CardDescription className="text-green-300">For professionals</CardDescription>
                </div>
                <Badge className="bg-green-500 text-white">Advanced</Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="text-4xl font-bold text-white mb-2">
                {formatPrice(7999)}
              </div>
              <p className="text-gray-400 text-sm mb-6">per month</p>
              
              <div className="space-y-3 mb-6">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Included Credits</span>
                  <span className="text-white font-medium">{formatCredits(15000)}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Priority Support</span>
                  <span className="text-green-400 font-medium">Included</span>
                </div>
              </div>

              <Button 
                className="w-full bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 text-white mb-4 shadow-lg"
                onClick={() => handleSubscribe('PREMIUM', billingPeriod.toUpperCase())}
              >
                <Shield className="h-4 w-4 mr-2" />
                Buy {billingPeriod === 'monthly' ? 'Monthly' : 'Yearly'}
              </Button>
              
              <Button 
                variant="outline" 
                className="w-full border-green-500/30 text-green-300 hover:bg-green-900/30 hover:border-green-500/50"
                onClick={() => router.push('/dashboard')}
              >
                Continue with Credits
              </Button>
            </CardContent>
          </Card>

          {/* Ultimate Plan */}
          <Card className="hover:shadow-xl hover:shadow-purple-500/20 transition-all duration-300 border-purple-500/30 relative overflow-hidden bg-white/5 backdrop-blur-lg rounded-2xl">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 to-pink-500"></div>
            <CardHeader className="bg-gradient-to-br from-purple-900/30 to-pink-900/30 border-b border-purple-500/20">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-white text-2xl">Ultimate</CardTitle>
                  <CardDescription className="text-purple-300">For institutions</CardDescription>
                </div>
                <Badge className="bg-purple-500 text-white">Enterprise</Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="text-4xl font-bold text-white mb-2">
                {formatPrice(19999)}
              </div>
              <p className="text-gray-400 text-sm mb-6">per month</p>
              
              <div className="space-y-3 mb-6">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Included Credits</span>
                  <span className="text-white font-medium">{formatCredits(50000)}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Dedicated Manager</span>
                  <span className="text-purple-400 font-medium">Included</span>
                </div>
              </div>

              <Button 
                className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white mb-4 shadow-lg"
                onClick={() => handleSubscribe('ULTIMATE', billingPeriod.toUpperCase())}
              >
                <Crown className="h-4 w-4 mr-2" />
                Buy {billingPeriod === 'monthly' ? 'Monthly' : 'Yearly'}
              </Button>
              
              <Button 
                variant="outline" 
                className="w-full border-purple-500/30 text-purple-300 hover:bg-purple-900/30 hover:border-purple-500/50"
                onClick={() => router.push('/dashboard')}
              >
                Continue with Credits
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Feature Comparison Table */}
        <Card className="border-white/10 bg-white/5 backdrop-blur-lg rounded-2xl">
          <CardHeader>
            <CardTitle className="text-white">Feature Comparison</CardTitle>
            <CardDescription className="text-gray-400">
              Compare all features across our plans
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left text-gray-400 py-3 px-4">Features</th>
                    <th className="text-center text-gray-400 py-3 px-4">Free</th>
                    <th className="text-center text-gray-400 py-3 px-4">Pro</th>
                    <th className="text-center text-gray-400 py-3 px-4">Premium</th>
                    <th className="text-center text-gray-400 py-3 px-4">Ultimate</th>
                  </tr>
                </thead>
                <tbody>
                  {features.map((feature, index) => (
                    <tr key={index} className="border-b border-white/5">
                      <td className="py-4 px-4 text-white font-medium">{feature.name}</td>
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
        <Card className="border-white/10 bg-gradient-to-r from-blue-900/30 to-purple-900/30 backdrop-blur-lg rounded-2xl">
          <CardHeader>
            <CardTitle className="text-white flex items-center">
              <CreditCard className="h-6 w-6 mr-2 text-purple-400" />
              Credit-Only Option
            </CardTitle>
            <CardDescription className="text-gray-400">
              Prefer to pay per usage? Buy credits and pay only for what you use.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-6 bg-white/5 rounded-xl border border-white/10 hover:border-purple-500/30 transition-all duration-300">
                <div className="text-3xl font-bold text-blue-400 mb-2">₹100</div>
                <div className="text-gray-400 mb-4">100 Credits</div>
                <Button variant="outline" className="border-blue-500/30 text-blue-300 hover:bg-blue-900/30 hover:border-blue-500/50">
                  Buy Now
                </Button>
              </div>
              <div className="text-center p-6 bg-white/5 rounded-xl border border-white/10 hover:border-green-500/30 transition-all duration-300">
                <div className="text-3xl font-bold text-green-400 mb-2">₹500</div>
                <div className="text-gray-400 mb-4">600 Credits</div>
                <Button variant="outline" className="border-green-500/30 text-green-300 hover:bg-green-900/30 hover:border-green-500/50">
                  Buy Now
                </Button>
              </div>
              <div className="text-center p-6 bg-white/5 rounded-xl border border-white/10 hover:border-purple-500/30 transition-all duration-300">
                <div className="text-3xl font-bold text-purple-400 mb-2">₹2000</div>
                <div className="text-gray-400 mb-4">2500 Credits</div>
                <Button variant="outline" className="border-purple-500/30 text-purple-300 hover:bg-purple-900/30 hover:border-purple-500/50">
                  Buy Now
                </Button>
              </div>
            </div>
            <div className="mt-4 text-sm text-gray-400 text-center">
              Credits never expire and can be used for backtests, AI screener runs, and other premium features.
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </RazorpayScript>
  );
}