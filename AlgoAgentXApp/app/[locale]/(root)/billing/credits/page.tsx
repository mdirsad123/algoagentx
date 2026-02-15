"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  CreditCard,
  Wallet,
  Plus,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Calendar,
  Clock,
  DollarSign,
  AlertCircle,
  CheckCircle,
  XCircle
} from "lucide-react";
import axiosInstance from "@/lib/axios";
import AppShell from "@/components/layout/AppShell";
import RazorpayScript from "@/components/shared/RazorpayScript";

interface CreditBalance {
  user_id: string;
  current_balance: number;
  last_updated: string;
}

interface CreditTransaction {
  id: string;
  user_id: string;
  transaction_type: 'debit' | 'credit' | 'refund';
  amount: number;
  description: string | null;
  backtest_id: string | null;
  job_id: string | null;
  balance_after: number;
  created_at: string;
}

interface CreateOrderResponse {
  order_id: string;
  amount: number;
  currency: string;
  razorpay_key_id: string;
}

interface VerifyPaymentResponse {
  success: boolean;
  payment_id: string;
  credits_granted: number;
  message: string;
}

interface TopUpPack {
  credits: number;
  price: number;
  label: string;
  popular?: boolean;
}

const TOP_UP_PACKS: TopUpPack[] = [
  { credits: 5, price: 500, label: "₹5", popular: false },
  { credits: 10, price: 1000, label: "₹10", popular: false },
  { credits: 20, price: 2000, label: "₹20", popular: false },
  { credits: 50, price: 5000, label: "₹50", popular: true },
  { credits: 100, price: 10000, label: "₹100", popular: false }
];

export default function CreditsWalletPage() {
  const [balance, setBalance] = useState<CreditBalance | null>(null);
  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPack, setSelectedPack] = useState<TopUpPack | null>(null);
  const [customAmount, setCustomAmount] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      setLoading(true);
      await Promise.all([
        fetchBalance(),
        fetchTransactions()
      ]);
    } catch (err: any) {
      console.error('Error fetching data:', err);
      setError('Failed to load wallet data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const fetchBalance = async () => {
    try {
      const response = await axiosInstance.get('/api/v1/credits/balance');
      setBalance(response.data);
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error('Error fetching balance:', err);
    }
  };

  const fetchTransactions = async () => {
    try {
      const response = await axiosInstance.get('/api/v1/credits/transactions?limit=50');
      setTransactions(response.data);
    } catch (err: any) {
      console.error('Error fetching transactions:', err);
    }
  };

  const handleTopUp = async (creditsToBuy: number) => {
    try {
      setIsProcessing(true);
      setError(null);

      // Check if user is authenticated
      const token = localStorage.getItem('access_token');
      if (!token) {
        router.push('/auth/login');
        return;
      }

      // Create order
      const orderResponse = await axiosInstance.post('/api/v1/payments/razorpay/create-order', {
        credits_to_buy: creditsToBuy
      });

      const orderData: CreateOrderResponse = orderResponse.data;

      // Open Razorpay checkout
      const options = {
        key: orderData.razorpay_key_id,
        amount: orderData.amount,
        currency: orderData.currency,
        name: 'AlgoAgentX',
        description: `${creditsToBuy} Credits Top-up`,
        image: '/algoagentx_icon.jpeg',
        order_id: orderData.order_id,
        handler: async function (response: any) {
          try {
            // Verify payment
            const verifyResponse = await axiosInstance.post('/api/v1/payments/razorpay/verify', {
              order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature
            });

            const verifyData: VerifyPaymentResponse = verifyResponse.data;

            if (verifyData.success) {
              // Refresh balance and transactions
              await fetchInitialData();
              
              // Show success message
              alert(`Success! ${verifyData.credits_granted} credits added to your wallet.`);
            } else {
              throw new Error(verifyData.message || 'Payment verification failed');
            }
          } catch (err: any) {
            console.error('Error verifying payment:', err);
            alert('Payment verification failed. Please contact support if you were charged.');
          }
        },
        prefill: {
          name: '', // Will be filled by Razorpay
          email: '', // Will be filled by Razorpay
          contact: '' // Will be filled by Razorpay
        },
        notes: {
          credits_to_buy: creditsToBuy
        },
        theme: {
          color: '#2563eb'
        }
      };

      const rzp = new (window as any).Razorpay(options);
      rzp.open();
    } catch (err: any) {
      console.error('Error creating order:', err);
      setError('Failed to create payment order. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCustomTopUp = () => {
    const amount = parseInt(customAmount);
    if (!amount || amount <= 0) {
      setError('Please enter a valid amount');
      return;
    }
    handleTopUp(amount);
  };

  const formatCurrency = (amount: number) => {
    return `₹${(amount / 100).toFixed(2)}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getTransactionIcon = (type: string) => {
    switch (type) {
      case 'credit':
        return <TrendingUp className="h-4 w-4 text-green-500" />;
      case 'debit':
        return <TrendingDown className="h-4 w-4 text-red-500" />;
      case 'refund':
        return <RefreshCw className="h-4 w-4 text-blue-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getTransactionDescription = (transaction: CreditTransaction) => {
    if (transaction.description) {
      return transaction.description;
    }
    
    if (transaction.transaction_type === 'debit') {
      if (transaction.backtest_id) {
        return `Backtest execution`;
      } else if (transaction.job_id) {
        return `Job execution`;
      }
      return 'Credit deduction';
    }
    
    if (transaction.transaction_type === 'credit') {
      return 'Credit top-up';
    }
    
    if (transaction.transaction_type === 'refund') {
      return 'Credit refund';
    }
    
    return 'Transaction';
  };

  if (loading && !balance) {
    return (
      <AppShell pageTitle="Credits Wallet">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading wallet...</span>
        </div>
      </AppShell>
    );
  }

  return (
    <RazorpayScript>
      <AppShell pageTitle="Credits Wallet">
        <div className="space-y-6">
          {/* Header Section */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Current Balance Card */}
            <Card className="lg:col-span-2 hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 border-blue-500/30">
              <CardHeader className="bg-gradient-to-br from-blue-900/50 to-blue-800/50 border-b border-blue-500/30">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-white text-2xl">Current Balance</CardTitle>
                    <CardDescription className="text-blue-200">
                      Your AlgoAgentX credits
                    </CardDescription>
                  </div>
                  <Wallet className="h-12 w-12 text-blue-300" />
                </div>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="flex items-end justify-between">
                  <div>
                    <div className="text-4xl font-bold text-white">
                      {balance ? balance.current_balance.toLocaleString() : '0'}
                    </div>
                    <div className="text-gray-400 text-sm mt-1">
                      Credits available
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-gray-400">Last updated</div>
                    <div className="text-white font-medium">
                      {lastUpdated ? lastUpdated.toLocaleTimeString() : 'Never'}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={fetchBalance}
                      className="mt-2 border-blue-500/50 text-blue-200 hover:bg-blue-900/20"
                    >
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Refresh
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions Card */}
            <Card className="hover:shadow-xl hover:shadow-green-500/10 transition-all duration-300 border-green-500/30">
              <CardHeader className="bg-gradient-to-br from-green-900/50 to-green-800/50 border-b border-green-500/30">
                <CardTitle className="text-white">Quick Actions</CardTitle>
                <CardDescription className="text-green-200">
                  Top up your credits
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6 space-y-4">
                <div className="space-y-2">
                  <Label className="text-gray-300">Select Top-up Pack</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {TOP_UP_PACKS.map((pack) => (
                      <Button
                        key={pack.credits}
                        variant={selectedPack?.credits === pack.credits ? "default" : "outline"}
                        onClick={() => setSelectedPack(pack)}
                        className={`h-12 ${
                          selectedPack?.credits === pack.credits 
                            ? 'bg-green-600 hover:bg-green-700' 
                            : 'border-green-500/50 text-green-200 hover:bg-green-900/20'
                        }`}
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        {pack.label}
                      </Button>
                    ))}
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="custom-amount" className="text-gray-300">
                    Custom Amount (Credits)
                  </Label>
                  <div className="flex space-x-2">
                    <Input
                      id="custom-amount"
                      type="number"
                      placeholder="Enter custom amount"
                      value={customAmount}
                      onChange={(e) => setCustomAmount(e.target.value)}
                      className="bg-gray-900 border-gray-700 text-white"
                    />
                    <Button
                      onClick={handleCustomTopUp}
                      disabled={isProcessing || !customAmount}
                      className="bg-purple-600 hover:bg-purple-700"
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Top Up
                    </Button>
                  </div>
                </div>

                {selectedPack && (
                  <div className="flex justify-between items-center p-3 bg-gray-900/50 rounded-lg border border-gray-700">
                    <span className="text-gray-300">Selected: {selectedPack.credits} credits</span>
                    <span className="text-green-400 font-bold">{formatCurrency(selectedPack.price)}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Top-up Section */}
          <Card className="border-gray-800">
            <CardHeader>
              <CardTitle className="text-white">Top Up Credits</CardTitle>
              <CardDescription className="text-gray-400">
                Choose a pack or enter custom amount to add credits to your wallet
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                {TOP_UP_PACKS.map((pack) => (
                  <div
                    key={pack.credits}
                    className={`p-4 border-2 rounded-lg cursor-pointer transition-all duration-200 hover:shadow-lg ${
                      selectedPack?.credits === pack.credits
                        ? 'border-green-500 bg-green-900/20'
                        : 'border-gray-700 hover:border-gray-600'
                    }`}
                    onClick={() => setSelectedPack(pack)}
                  >
                    {pack.popular && (
                      <span className="inline-block mb-2 px-2 py-1 bg-green-600 text-white text-xs rounded">Popular</span>
                    )}
                    <div className="text-2xl font-bold text-white">{pack.credits} Credits</div>
                    <div className="text-green-400 font-bold text-lg mt-1">{formatCurrency(pack.price)}</div>
                    <div className="text-gray-400 text-sm mt-1">One-time purchase</div>
                  </div>
                ))}
              </div>
              
              <div className="mt-6 flex justify-center">
                <Button
                  onClick={() => selectedPack ? handleTopUp(selectedPack.credits) : null}
                  disabled={isProcessing || !selectedPack}
                  className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 py-3 text-lg"
                >
                  <CreditCard className="h-5 w-5 mr-3" />
                  {isProcessing ? 'Processing...' : `Top Up ${selectedPack ? selectedPack.credits : ''} Credits`}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Transaction History */}
          <Card className="border-gray-800">
            <CardHeader>
              <CardTitle className="text-white">Transaction History</CardTitle>
              <CardDescription className="text-gray-400">
                Recent credit transactions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {transactions.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">
                    No transactions yet. Top up your credits to get started!
                  </div>
                ) : (
                  transactions.map((transaction) => (
                    <div
                      key={transaction.id}
                      className="flex items-center justify-between p-4 bg-gray-900/50 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors"
                    >
                      <div className="flex items-center space-x-4">
                        {getTransactionIcon(transaction.transaction_type)}
                        <div>
                          <div className="font-medium text-white">
                            {getTransactionDescription(transaction)}
                          </div>
                          <div className="text-sm text-gray-400 flex items-center space-x-4">
                            <span className="flex items-center">
                              <Calendar className="h-3 w-3 mr-1" />
                              {formatDate(transaction.created_at)}
                            </span>
                            {transaction.transaction_type === 'debit' && (
                              <span className="text-red-400">-{transaction.amount}</span>
                            )}
                            {transaction.transaction_type === 'credit' && (
                              <span className="text-green-400">+{transaction.amount}</span>
                            )}
                            {transaction.transaction_type === 'refund' && (
                              <span className="text-blue-400">Refund +{transaction.amount}</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`font-bold ${
                          transaction.transaction_type === 'debit' ? 'text-red-400' :
                          transaction.transaction_type === 'credit' ? 'text-green-400' :
                          'text-blue-400'
                        }`}>
                          {transaction.transaction_type === 'debit' ? '-' : '+'}{transaction.amount}
                        </div>
                        <div className="text-sm text-gray-400">Balance: {transaction.balance_after}</div>
                      </div>
                    </div>
                  ))
                )}
              </div>
              
              <div className="mt-4 text-center">
                <Button
                  variant="outline"
                  onClick={fetchTransactions}
                  className="border-gray-600 text-gray-300 hover:bg-gray-800"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh History
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Error Display */}
          {error && (
            <div className="fixed bottom-4 right-4 bg-red-900/90 border border-red-500 text-red-100 p-4 rounded-lg shadow-lg">
              <div className="flex items-center space-x-2">
                <AlertCircle className="h-5 w-5" />
                <span>{error}</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setError(null)}
                className="ml-auto mt-2 text-red-300 hover:text-white"
              >
                Dismiss
              </Button>
            </div>
          )}
        </div>
      </AppShell>
    </RazorpayScript>
  );
}