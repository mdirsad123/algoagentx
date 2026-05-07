"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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
  AlertCircle,
} from "lucide-react";
import axiosInstance from "@/lib/axios";
import RazorpayScript from "@/components/shared/RazorpayScript";
import { toast } from "sonner";

interface CreditBalance {
  user_id: string;
  balance?: number;
  current_balance: number;
  last_updated: string;
}

interface CreditTransaction {
  id: string;
  user_id: string;
  type?: 'debit' | 'credit' | 'refund';
  transaction_type: 'debit' | 'credit' | 'refund';
  amount: number;
  reason?: string | null;
  description: string | null;
  backtest_id: string | null;
  job_id: string | null;
  balance_after: number;
  created_at: string;
}

interface TopUpPack {
  code: string;
  title: string;
  credits: number;
  bonus_credits?: number;
  total_credits?: number;
  price_usd: number;
  amount_usd?: number;
  description?: string | null;
  is_popular?: boolean;
  popular?: boolean;
  label?: string;
}

interface RazorpayConfigResponse {
  configured: boolean;
  key_id: string;
  packs: TopUpPack[];
  allow_custom_topup: boolean;
  min_custom_credits: number;
  max_custom_credits: number;
}

interface CreateOrderResponse {
  order_id: string;
  billing_order_id: string;
  amount: number;
  amount_inr: number;
  currency: string;
  key_id?: string;
  razorpay_key_id: string;
  status?: string;
}

interface VerifyPaymentResponse {
  success: boolean;
  payment_id: string;
  order_id: string;
  billing_order_id?: string;
  credits_granted: number;
  balance?: number;
  idempotent?: boolean;
  status?: string;
  message: string;
}

const unwrapApiData = (payload: any) => payload?.success ? payload.data : payload;

const DEFAULT_TOP_UP_PACKS: TopUpPack[] = [];

const getErrorMessage = (error: any): string =>
  error?.response?.data?.detail || error?.message || "Something went wrong";

export default function CreditsWalletPage() {
  const [balance, setBalance] = useState<CreditBalance | null>(null);
  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [packs, setPacks] = useState<TopUpPack[]>(DEFAULT_TOP_UP_PACKS);
  const [selectedPackCode, setSelectedPackCode] = useState<string>("");
  const [customAmount, setCustomAmount] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [configured, setConfigured] = useState(false);
  const [allowCustomTopup, setAllowCustomTopup] = useState(false);
  const [minCustomCredits, setMinCustomCredits] = useState(1);
  const [maxCustomCredits, setMaxCustomCredits] = useState(100000);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const router = useRouter();

  const selectedPack = useMemo(
    () => packs.find((pack) => pack.code === selectedPackCode) || null,
    [packs, selectedPackCode],
  );

  const fetchPaymentConfig = useCallback(async () => {
    const [configResponse, packsResponse] = await Promise.all([
      axiosInstance.get('/api/v1/payments/razorpay/config'),
      axiosInstance.get('/api/v1/billing/credit-packs'),
    ]);
    const config: RazorpayConfigResponse = unwrapApiData(configResponse.data);
    const activePacks = unwrapApiData(packsResponse.data) as TopUpPack[];
    setConfigured(!!config?.configured);
    setAllowCustomTopup(false);
    setMinCustomCredits(Number(config?.min_custom_credits || 1));
    setMaxCustomCredits(Number(config?.max_custom_credits || 100000));

    if (Array.isArray(activePacks) && activePacks.length > 0) {
      const normalized = activePacks.map((pack) => ({
        ...pack,
        total_credits: Number(pack.total_credits ?? (Number(pack.credits || 0) + Number(pack.bonus_credits || 0))),
        price_usd: Number(pack.price_usd ?? pack.amount_usd ?? 0),
        amount_usd: Number(pack.price_usd ?? pack.amount_usd ?? 0),
        popular: Boolean(pack.popular ?? pack.is_popular),
        label: formatUsdPackLabel(pack),
      }));
      setPacks(normalized);
      const preferredPack = normalized.find((pack) => pack.popular || pack.is_popular) || normalized[0];
      setSelectedPackCode(preferredPack.code);
    } else {
      setPacks([]);
      setSelectedPackCode('');
    }
  }, []);

  const fetchBalance = useCallback(async () => {
    try {
      const response = await axiosInstance.get('/api/v1/credits/balance');
      const data = unwrapApiData(response.data) as CreditBalance;
      setBalance({
        ...data,
        current_balance: Number(data?.current_balance ?? data?.balance ?? 0),
      });
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error('Error fetching balance:', err);
    }
  }, []);

  const fetchTransactions = useCallback(async () => {
    try {
      const response = await axiosInstance.get('/api/v1/credits/transactions?limit=50');
      const data = unwrapApiData(response.data);
      const normalized = (Array.isArray(data) ? data : []).map((txn: any) => ({
        ...txn,
        transaction_type: String(txn?.transaction_type || txn?.type || '').toLowerCase(),
        description: txn?.description || txn?.reason || null,
      })) as CreditTransaction[];
      setTransactions(normalized);
    } catch (err: any) {
      console.error('Error fetching transactions:', err);
    }
  }, []);

  const fetchInitialData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      await Promise.all([
        fetchBalance(),
        fetchTransactions(),
        fetchPaymentConfig(),
      ]);
    } catch (err: any) {
      console.error('Error fetching data:', err);
      setError('Failed to load wallet data. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [fetchBalance, fetchTransactions, fetchPaymentConfig]);

  useEffect(() => {
    void fetchInitialData();
  }, [fetchInitialData]);

  const markPaymentFailure = useCallback(async (orderId: string, reason?: string, code?: string) => {
    try {
      await axiosInstance.post('/api/v1/payments/razorpay/failure', {
        order_id: orderId,
        reason,
        code,
      });
    } catch {
      // best-effort
    }
  }, []);

  const openRazorpayCheckout = useCallback(
    (orderData: CreateOrderResponse, creditsToBuy: number): Promise<void> =>
      new Promise((resolve, reject) => {
        const Razorpay = (window as any)?.Razorpay;
        if (!Razorpay) {
          reject(new Error('Razorpay SDK not loaded. Please refresh and try again.'));
          return;
        }

        const options = {
          key: orderData.razorpay_key_id || orderData.key_id,
          amount: orderData.amount,
          currency: orderData.currency,
          name: 'AlgoAgentX',
          description: `${creditsToBuy} Credits Top-up`,
          image: '/images/algoagentx_icon.jpeg',
          order_id: orderData.order_id,
          notes: {
            credits_to_buy: String(creditsToBuy),
            billing_order_id: orderData.billing_order_id,
          },
          theme: { color: '#7c3aed' },
          handler: async (response: any) => {
            try {
              const verifyResponse = await axiosInstance.post('/api/v1/payments/razorpay/verify', {
                order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              });

              const verifyData: VerifyPaymentResponse = unwrapApiData(verifyResponse.data);
              if (!verifyData?.success) {
                throw new Error(verifyData?.message || 'Payment verification failed');
              }

              toast.success(
                verifyData.idempotent
                  ? 'Payment already verified. Wallet is up to date.'
                  : `Success! ${verifyData.credits_granted} credits added to your wallet.`,
              );
              await Promise.all([fetchBalance(), fetchTransactions()]);
              resolve();
            } catch (err: any) {
              const message = getErrorMessage(err);
              toast.error(message || 'Payment verification failed. Please contact support if charged.');
              reject(err);
            }
          },
          modal: {
            ondismiss: async () => {
              await markPaymentFailure(orderData.order_id, 'checkout_closed_by_user');
              reject(new Error('checkout_cancelled'));
            },
          },
        };

        const rzp = new Razorpay(options);
        rzp.on('payment.failed', async (failure: any) => {
          await markPaymentFailure(
            orderData.order_id,
            failure?.error?.description || 'payment_failed',
            failure?.error?.code,
          );
          reject(new Error(failure?.error?.description || 'Payment failed'));
        });

        rzp.open();
      }),
    [fetchBalance, fetchTransactions, markPaymentFailure],
  );

  const handleTopUp = async (creditsToBuy: number, packCode?: string) => {
    setError(null);

    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/auth/login');
      return;
    }

    if (!creditsToBuy || creditsToBuy <= 0) {
      setError('Please choose a valid credit amount.');
      return;
    }

    if (!packCode) {
      setError('Please choose a configured credit pack.');
      return;
    }
    router.push(`/billing/checkout?type=credits&pack=${encodeURIComponent(packCode)}`);
  };

  const handleCustomTopUp = () => {
    const amount = parseInt(customAmount, 10);
    if (!amount || amount <= 0) {
      setError('Please enter a valid amount');
      return;
    }

    if (!allowCustomTopup) {
      setError('Custom credit top-up is disabled. Please choose a configured pack.');
      return;
    }

    if (amount < minCustomCredits || amount > maxCustomCredits) {
      setError(`Custom credits must be between ${minCustomCredits} and ${maxCustomCredits}.`);
      return;
    }

    handleTopUp(amount);
  };

  const getPackUsdAmount = (pack: TopUpPack | null | undefined): number => {
    if (!pack) return 0;
    return Number(pack.price_usd ?? pack.amount_usd ?? 0);
  };

  const formatCurrency = (amountUsd: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: amountUsd % 1 === 0 ? 0 : 2,
    }).format(amountUsd || 0);

  const formatUsdPackLabel = (pack: TopUpPack): string => formatCurrency(getPackUsdAmount(pack));

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

  const handleRefreshAll = async () => {
    await fetchInitialData();
  };

  if (loading && !balance) {
    return (
      <>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
          <span className="ml-2 text-purple-100/60">Loading wallet...</span>
        </div>
      </>
    );
  }

  return (
    <RazorpayScript>
      <>
        <div className="space-y-6">
        {/* Header Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Current Balance Card */}
          <Card className="lg:col-span-2 hover:shadow-xl hover:shadow-purple-500/20 transition-all duration-300 border-white/20 bg-gradient-to-br from-white/10 to-purple-500/10 backdrop-blur-lg rounded-2xl">
            <CardHeader className="bg-gradient-to-br from-white/10 to-white/5 border-b border-white/20">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-white text-2xl">Current Balance</CardTitle>
                  <CardDescription className="text-purple-100/60">
                    Your AlgoAgentX credits
                  </CardDescription>
                </div>
                <Wallet className="h-12 w-12 text-purple-300" />
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="flex items-end justify-between">
                <div>
                  <div className="text-4xl font-bold text-white">
                    {balance ? balance.current_balance.toLocaleString() : '0'}
                  </div>
                  <div className="text-purple-100/60 text-sm mt-1">
                    Credits available
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-purple-100/60">Last updated</div>
                  <div className="text-white font-medium">
                    {lastUpdated ? lastUpdated.toLocaleTimeString() : 'Never'}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={fetchBalance}
                    className="mt-2 border-white/20 text-purple-100 hover:bg-white/10 hover:border-purple-400/50"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions Card */}
          <Card className="hover:shadow-xl hover:shadow-green-500/20 transition-all duration-300 border-green-500/30 bg-gradient-to-br from-white/10 to-green-500/10 backdrop-blur-lg rounded-2xl">
            <CardHeader className="bg-gradient-to-br from-green-900/30 to-emerald-900/30 border-b border-green-500/30">
              <CardTitle className="text-white">Quick Actions</CardTitle>
              <CardDescription className="text-green-300">
                Top up your credits
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <div className="space-y-2">
                <Label className="text-purple-100/60">Select Top-up Pack</Label>
                <div className="grid grid-cols-2 gap-2">
                  {packs.map((pack) => (
                    <Button
                      key={pack.code}
                      variant={selectedPack?.code === pack.code ? "default" : "outline"}
                      onClick={() => setSelectedPackCode(pack.code)}
                      className={`h-12 ${
                        selectedPack?.code === pack.code 
                          ? 'bg-gradient-to-r from-green-500 to-emerald-500 shadow-lg' 
                          : 'border-white/20 text-purple-100 hover:bg-white/10 hover:border-purple-400/50'
                      }`}
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      {formatUsdPackLabel(pack)}
                    </Button>
                  ))}
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="custom-amount" className="text-purple-100/60">
                  Custom Amount (Credits)
                </Label>
                <div className="flex space-x-2">
                  <Input
                    id="custom-amount"
                    type="number"
                    placeholder="Enter custom amount"
                    value={customAmount}
                    onChange={(e) => setCustomAmount(e.target.value)}
                    className="bg-white/10 border-white/20 text-white placeholder:text-purple-100/50 focus:border-purple-400 focus:ring-2 focus:ring-purple-400/30"
                    disabled={!allowCustomTopup || isProcessing}
                  />
                  <Button
                    onClick={handleCustomTopUp}
                    disabled={isProcessing || !customAmount || !allowCustomTopup}
                    className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white border-0"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Top Up
                  </Button>
                </div>
                <p className="text-xs text-purple-100/60">
                  {allowCustomTopup
                    ? `Allowed range: ${minCustomCredits} - ${maxCustomCredits} credits`
                    : 'Custom top-up disabled. Please select a pack.'}
                </p>
              </div>

              {selectedPack && (
                <div className="flex justify-between items-center p-3 bg-gradient-to-br from-white/10 to-purple-500/10 rounded-lg border border-white/20">
                  <span className="text-purple-100/60">Selected: {selectedPack.title || `${selectedPack.total_credits || selectedPack.credits} credits`}</span>
                  <span className="text-green-400 font-bold">{formatCurrency(getPackUsdAmount(selectedPack))}</span>
                </div>
              )}
              {!configured && (
                <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-200">
                  Razorpay routing is configured on the checkout page. You can preview billing before payment.
                </div>
              )}
            </CardContent>
          </Card>
        </div>

          {/* Top-up Section */}
          <Card className="border-white/20 bg-gradient-to-br from-white/10 to-purple-500/10 backdrop-blur-lg rounded-2xl">
            <CardHeader>
              <CardTitle className="text-white">Top Up Credits</CardTitle>
              <CardDescription className="text-purple-100/60">
                Choose an admin-managed pack to add credits to your wallet
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                {packs.map((pack) => (
                  <div
                    key={pack.code}
                    className={`p-4 border-2 rounded-lg cursor-pointer transition-all duration-200 hover:shadow-lg ${
                      selectedPack?.code === pack.code
                        ? 'border-purple-400 bg-purple-500/10'
                        : 'border-white/20 hover:border-purple-400/50'
                    }`}
                    onClick={() => setSelectedPackCode(pack.code)}
                  >
                    {(pack.popular || pack.is_popular) && (
                      <span className="inline-block mb-2 px-2 py-1 bg-gradient-to-r from-purple-500 to-pink-500 text-white text-xs rounded shadow-lg">Popular</span>
                    )}
                    <div className="text-2xl font-bold text-white">{pack.title || `${pack.total_credits || pack.credits} Credits`}</div>
                    <div className="mt-1 text-sm text-purple-100/70">{Number(pack.credits || 0).toLocaleString()} base{Number(pack.bonus_credits || 0) > 0 ? ` + ${Number(pack.bonus_credits || 0).toLocaleString()} bonus` : ''}</div>
                    <div className="text-purple-400 font-bold text-lg mt-1">{formatCurrency(getPackUsdAmount(pack))}</div>
                    <div className="text-purple-100/60 text-sm mt-1">{pack.description || 'One-time purchase'}</div>
                  </div>
                ))}
              </div>
              
              <div className="mt-6 flex justify-center space-x-4">
                <Button
                  onClick={() => selectedPack ? handleTopUp(selectedPack.total_credits || selectedPack.credits, selectedPack.code) : null}
                  disabled={isProcessing || !selectedPack}
                  className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white px-8 py-3 text-lg shadow-lg shadow-purple-500/30"
                >
                  <CreditCard className="h-5 w-5 mr-3" />
                  {isProcessing ? 'Processing...' : `Top Up ${selectedPack ? (selectedPack.total_credits || selectedPack.credits) : ''} Credits`}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Transaction History */}
          <Card className="border-white/20 bg-gradient-to-br from-white/10 to-purple-500/10 backdrop-blur-lg rounded-2xl">
            <CardHeader>
              <CardTitle className="text-white">Transaction History</CardTitle>
              <CardDescription className="text-purple-100/60">
                Recent credit transactions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {transactions.length === 0 ? (
                  <div className="text-center py-8 text-purple-100/60">
                    No transactions yet. Top up your credits to get started!
                  </div>
                ) : (
                  transactions.map((transaction) => (
                    <div
                      key={transaction.id}
                      className="flex items-center justify-between p-4 bg-gradient-to-br from-white/10 to-purple-500/10 rounded-lg border border-white/20 hover:border-purple-400/50 transition-all duration-200 hover:shadow-lg hover:shadow-purple-500/20"
                    >
                      <div className="flex items-center space-x-4">
                        {getTransactionIcon(transaction.transaction_type)}
                        <div>
                          <div className="font-medium text-white">
                            {getTransactionDescription(transaction)}
                          </div>
                          <div className="text-sm text-purple-100/60 flex items-center space-x-4">
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
                        <div className="text-sm text-purple-100/60">Balance: {transaction.balance_after}</div>
                      </div>
                    </div>
                  ))
                )}
              </div>
              
              <div className="mt-4 text-center">
                <Button
                  variant="outline"
                  onClick={handleRefreshAll}
                  className="border-white/20 text-purple-100 hover:bg-white/10 hover:border-purple-400/50"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh Data
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Error Display */}
          {error && (
            <div className="fixed bottom-4 right-4 bg-red-900/90 border border-red-500 text-red-100 p-4 rounded-lg shadow-lg backdrop-blur-lg">
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
      </>
    </RazorpayScript>
  );
}